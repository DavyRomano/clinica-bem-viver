import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'py'))
from app import app, banco, iniciar


class Sistema(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        app.config.update(TESTING=True, BANCO=Path(pasta.name) / 'teste.db')
        with app.app_context():
            iniciar()
        self.admin = self.entrar('admin@bemviver.test', 'ClinicaAV2!')
        self.paciente = self.entrar('paciente@bemviver.test', 'PacienteAV2!')
        self.outro = app.test_client()
        conta = dict(nome='Outro Exemplo', email='outro@teste.test', senha='SomenteTeste')
        self.enviar(self.outro, 'cadastro', conta, esperado=201)
        self.outro = self.entrar(conta['email'], conta['senha'])
        dia = date.today() + timedelta(days=7)
        while dia.weekday() >= 5:
            dia += timedelta(days=1)
        self.reserva = dict(medico_id=1, data=dia.isoformat(), hora='09:00')

    def entrar(self, email, senha):
        cliente = app.test_client()
        self.enviar(cliente, 'login', dict(email=email, senha=senha))
        return cliente

    def enviar(self, cliente, rota, dados=None, metodo='POST', esperado=200):
        token = cliente.get('/api/sessao').json['token']
        resposta = cliente.open('/api/' + rota, method=metodo, json=dados, headers={'X-CSRF-Token': token})
        self.assertEqual(resposta.status_code, esperado, resposta.json)
        return resposta.json

    def test_permissoes(self):
        self.assertEqual(app.test_client().get('/api/admin/resumo').status_code, 401)
        self.assertEqual(self.paciente.get('/api/admin/resumo').status_code, 403)
        self.assertEqual(self.outro.get('/api/consultas?paciente_id=1').json, [])
        self.enviar(self.outro, 'consultas/1/cancelar', esperado=404)
        self.assertEqual(self.admin.post('/api/logout').status_code, 403)
        self.assertEqual(self.admin.get('/sql/clinica.db').status_code, 404)
        self.enviar(self.admin, 'logout')
        self.assertEqual(self.admin.get('/api/admin/resumo').status_code, 401)

    def test_disputa_e_cancelamento(self):
        clientes = [self.paciente, self.outro]
        tokens = [c.get('/api/sessao').json['token'] for c in clientes]

        def reservar(i):
            return clientes[i].post('/api/consultas', json=self.reserva, headers={'X-CSRF-Token': tokens[i]}).status_code

        with ThreadPoolExecutor(2) as executor:
            resultados = list(executor.map(reservar, [0, 1]))
        self.assertEqual(sorted(resultados), [201, 409])
        vencedor = clientes[resultados.index(201)]
        outro = clientes[resultados.index(409)]
        consulta = next(c for c in vencedor.get('/api/consultas').json if c['data'] == self.reserva['data'])
        rota = f"consultas/{consulta['id']}/cancelar"
        self.enviar(outro, rota, esperado=404)
        self.enviar(vencedor, 'consultas', dict(self.reserva, medico_id=2), esperado=409)
        self.enviar(vencedor, rota)
        self.enviar(outro, 'consultas', self.reserva, esperado=201)

    def test_cadastros_administrativos(self):
        for grupo, dados in [
            ('especialidades', dict(nome='Nova área', descricao='Atendimento fictício', area='Geral')),
            ('medicos', dict(nome='Profissional de teste', especialidade_id=1, foto='perfil')),
            ('pacientes', dict(nome='Nome de teste', email='nome@teste.test', senha='SomenteTeste'))]:
            rota = 'admin/' + grupo
            self.enviar(self.admin, rota, dados)
            registros = self.admin.get('/api/admin/resumo').json[grupo]
            codigo = next(r['id'] for r in registros if r['nome'] == dados['nome'])
            self.enviar(self.admin, f'{rota}/{codigo}', dict(dados, nome='Nome alterado'), 'PUT')
            self.enviar(self.admin, f'{rota}/{codigo}', metodo='DELETE')
        self.enviar(self.admin, 'admin/medicos/1', metodo='DELETE', esperado=409)
        self.enviar(self.admin, 'admin/especialidades/1', metodo='DELETE', esperado=409)
        self.enviar(self.admin, 'admin/pacientes/1', metodo='DELETE', esperado=409)

    def test_validacoes_e_banco(self):
        self.enviar(self.outro, 'consultas', dict(self.reserva, data='2000-01-01'), esperado=400)
        self.enviar(self.outro, 'consultas', dict(self.reserva, hora='02:00'), esperado=400)
        self.enviar(self.outro, 'cadastro', dict(nome='Outro', email='outro@teste.test', senha='SomenteTeste'), esperado=409)
        self.enviar(self.outro, 'contatos', dict(nome='Outro', email='outro@teste.test', mensagem='Tudo certo aqui.'), esperado=201)
        with app.app_context():
            iniciar()
            self.assertEqual(banco().execute('SELECT COUNT(*) FROM contatos').fetchone()[0], 1)
            self.assertEqual(banco().execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertNotEqual(banco().execute('SELECT senha_hash FROM usuarios LIMIT 1').fetchone()[0], 'ClinicaAV2!')


if __name__ == '__main__':
    unittest.main()
