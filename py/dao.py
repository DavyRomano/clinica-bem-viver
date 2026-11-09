from datetime import date, timedelta

from models import Paciente, Usuario


class Banco:
    def __init__(self, conexao):
        self.db = conexao

    def lista(self, sql, valores=()):
        return [dict(linha) for linha in self.db.execute(sql, valores)]

    def alterar(self, sql, valores):
        cursor = self.db.execute(sql, valores)
        if not cursor.rowcount:
            raise LookupError('Registro não encontrado ou já alterado.')


class UsuarioDAO(Banco):
    def por_id(self, codigo):
        return self.db.execute("""SELECT u.id,u.nome,u.email,u.papel,p.id AS paciente_id,p.telefone
                                FROM usuarios u LEFT JOIN pacientes p ON p.usuario_id=u.id WHERE u.id=?""",
                                (codigo,)).fetchone()

    def buscar(self, email):
        return self.db.execute('SELECT * FROM usuarios WHERE email=?', (email,)).fetchone()

    def cadastrar(self, pessoa, senha, papel='paciente'):
        return self.db.execute('INSERT INTO usuarios(nome,email,senha_hash,papel) VALUES(?,?,?,?)',
                               (pessoa.nome, pessoa.email, pessoa.gerar_hash(senha), papel)).lastrowid


class PacienteDAO(Banco):
    def criar(self, paciente, senha):
        usuario = UsuarioDAO(self.db).cadastrar(paciente, senha)
        return self.db.execute('INSERT INTO pacientes(usuario_id,telefone) VALUES(?,?)',
                               (usuario, paciente.telefone)).lastrowid

    def listar(self):
        return self.lista('SELECT p.id,u.nome,u.email,p.telefone FROM pacientes p JOIN usuarios u ON u.id=p.usuario_id ORDER BY u.nome')

    def editar(self, codigo, pessoa):
        self.alterar('UPDATE usuarios SET nome=?, email=? WHERE id=(SELECT usuario_id FROM pacientes WHERE id=?)',
                     (pessoa.nome, pessoa.email, codigo))
        self.alterar('UPDATE pacientes SET telefone=? WHERE id=?', (pessoa.telefone, codigo))

    def excluir(self, codigo):
        self.alterar('DELETE FROM usuarios WHERE id=(SELECT usuario_id FROM pacientes WHERE id=?)', (codigo,))


class EspecialidadeDAO(Banco):
    def listar(self):
        return self.lista('SELECT e.*,COUNT(m.id) AS profissionais FROM especialidades e LEFT JOIN medicos m ON m.especialidade_id=e.id GROUP BY e.id ORDER BY e.id')

    def salvar(self, item, codigo=None):
        valores = (item.nome, item.descricao, item.area)
        if codigo is None:
            self.db.execute('INSERT INTO especialidades(nome,descricao,area) VALUES(?,?,?)', valores)
        else:
            self.alterar('UPDATE especialidades SET nome=?,descricao=?,area=? WHERE id=?', valores + (codigo,))

    def excluir(self, codigo):
        self.alterar('DELETE FROM especialidades WHERE id=?', (codigo,))


class MedicoDAO(Banco):
    def listar(self):
        return self.lista('SELECT m.*, e.nome AS especialidade FROM medicos m JOIN especialidades e ON m.especialidade_id=e.id ORDER BY m.id')

    def salvar(self, item, codigo=None):
        valores = (item.nome, item.especialidade_id, item.foto)
        if codigo is None:
            self.db.execute('INSERT INTO medicos(nome,especialidade_id,foto) VALUES(?,?,?)', valores)
        else:
            self.alterar('UPDATE medicos SET nome=?,especialidade_id=?,foto=? WHERE id=?', valores + (codigo,))

    def excluir(self, codigo):
        self.alterar('DELETE FROM medicos WHERE id=?', (codigo,))


class ConsultaDAO(Banco):
    def listar(self, paciente=None):
        sql = """SELECT c.*,u.nome AS paciente,m.nome AS medico,e.nome AS especialidade
                 FROM consultas c JOIN pacientes p ON c.paciente_id=p.id
                 JOIN usuarios u ON p.usuario_id=u.id JOIN medicos m ON c.medico_id=m.id
                 JOIN especialidades e ON m.especialidade_id=e.id"""
        filtro = ' WHERE c.paciente_id=?' if paciente is not None else ''
        return self.lista(sql + filtro + ' ORDER BY c.data DESC,c.hora DESC', (paciente,) if filtro else ())

    def ocupados(self, medico, data, paciente):
        linhas = self.lista("""SELECT hora FROM consultas WHERE data=? AND status='Agendada'
                            AND (medico_id=? OR paciente_id=?)""", (data, medico, paciente))
        return {linha['hora'] for linha in linhas}

    def criar(self, paciente, consulta):
        self.db.execute('INSERT INTO consultas(paciente_id,medico_id,data,hora) VALUES(?,?,?,?)',
                        (paciente, consulta.medico_id, consulta.data, consulta.hora))

    def mudar_status(self, codigo, status, paciente=None):
        sql = "UPDATE consultas SET status=? WHERE id=? AND status='Agendada'"
        valores = [status, codigo]
        if paciente is not None:
            sql += ' AND paciente_id=?'
            valores.append(paciente)
        if status == 'Realizada':
            sql += " AND data || ' ' || hora <= strftime('%Y-%m-%d %H:%M','now','localtime')"
        self.alterar(sql, valores)

    def estatisticas(self):
        return self.lista('SELECT status,COUNT(*) AS total FROM consultas GROUP BY status')


class ContatoDAO(Banco):
    def criar(self, contato):
        self.db.execute('INSERT INTO contatos(nome,email,mensagem) VALUES(?,?,?)',
                        (contato.nome, contato.email, contato.mensagem))

    def listar(self):
        return self.lista('SELECT * FROM contatos ORDER BY id DESC')


def iniciar_banco(db, esquema):
    db.executescript(esquema)
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT id FROM usuarios LIMIT 1').fetchone():
            return
        areas = [
            ('Clínica geral', 'Um primeiro encontro para conversar sobre sua saúde e planejar o acompanhamento.', 'Geral'),
            ('Cardiologia', 'Consultas voltadas ao coração e ao acompanhamento da saúde cardiovascular.', 'Especializada'),
            ('Dermatologia', 'Atenção à saúde da pele, dos cabelos e das unhas em diferentes fases da vida.', 'Especializada'),
            ('Geriatria', 'Acompanhamento individual para envelhecer com autonomia e qualidade de vida.', 'Especializada')]
        db.executemany('INSERT INTO especialidades(nome,descricao,area) VALUES(?,?,?)', areas)
        db.executemany('INSERT INTO medicos(nome,especialidade_id,foto) VALUES(?,?,?)', [
            ('Dra. Helena Prado', 1, 'helena'), ('Dr. André Luz', 2, 'andre'),
            ('Dra. Marina Reis', 3, 'marina'), ('Dra. Teresa Vale', 4, 'teresa')])
        UsuarioDAO(db).cadastrar(Usuario(dict(nome='Administração', email='admin@bemviver.test')), 'ClinicaAV2!', 'admin')
        paciente = PacienteDAO(db).criar(Paciente(dict(nome='Alex Exemplo', email='paciente@bemviver.test')), 'PacienteAV2!')
        proximo = date.today() + timedelta(days=1)
        while proximo.weekday() >= 5:
            proximo += timedelta(days=1)
        db.executemany('INSERT INTO consultas(paciente_id,medico_id,data,hora,status) VALUES(?,?,?,?,?)', [
            (paciente, 1, proximo.isoformat(), '10:00', 'Agendada'),
            (paciente, 2, (proximo-timedelta(days=7)).isoformat(), '14:00', 'Realizada')])
