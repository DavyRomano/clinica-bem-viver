import secrets
import sqlite3
from pathlib import Path

from flask import Flask, abort, g, jsonify, request, send_from_directory, session
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash

from dao import ConsultaDAO, ContatoDAO, EspecialidadeDAO, MedicoDAO, PacienteDAO, UsuarioDAO, iniciar_banco
from models import Consulta, Contato, Especialidade, Medico, Paciente, email_valido, numero

RAIZ = Path(__file__).resolve().parents[1]
app = Flask(__name__, static_folder=None)
app.secret_key = secrets.token_bytes(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=16000)
app.config['BANCO'] = RAIZ / 'sql' / 'clinica.db'


def banco():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['BANCO'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db


@app.teardown_appcontext
def fechar(erro):
    if 'db' in g:
        g.db.close()


def iniciar():
    esquema = (RAIZ / 'sql/clinica.sql').read_text(encoding='utf-8')
    iniciar_banco(banco(), esquema)


def dados():
    valor = request.get_json(silent=True)
    if not isinstance(valor, dict):
        raise ValueError('Envie um formulário válido.')
    return valor


def paciente_atual():
    if not g.usuario:
        abort(401)
    if g.usuario['paciente_id'] is None:
        abort(403, 'Use uma conta de paciente para acessar esta área.')
    return g.usuario['paciente_id']


@app.before_request
def proteger():
    if not request.path.startswith('/api/'):
        return
    g.usuario = UsuarioDAO(banco()).por_id(session.get('usuario'))
    if request.path.startswith('/api/admin/'):
        if not g.usuario:
            abort(401)
        if g.usuario['papel'] != 'admin':
            abort(403)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        token = request.headers.get('X-CSRF-Token', '')
        if not token or not token.isascii() or not secrets.compare_digest(token, session.get('csrf', '')):
            abort(403, 'Atualize a página para renovar sua sessão.')


@app.after_request
def cabecalhos(resposta):
    resposta.headers['X-Content-Type-Options'] = 'nosniff'
    resposta.headers['X-Frame-Options'] = 'DENY'
    resposta.headers['Content-Security-Policy'] = "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    if request.path.startswith('/api/'):
        resposta.headers['Cache-Control'] = 'no-store'
    return resposta


@app.errorhandler(HTTPException)
def erro_http(erro):
    mensagem = {401: 'Entre para continuar.', 403: 'Acesso restrito.', 404: 'Registro não encontrado.'}
    texto = erro.description
    if texto == type(erro).description:
        texto = mensagem.get(erro.code, 'Solicitação inválida.')
    return jsonify(erro=texto), erro.code


@app.errorhandler(ValueError)
def erro_campo(erro):
    return jsonify(erro=str(erro)), 400


@app.errorhandler(LookupError)
def ausente(erro):
    return jsonify(erro=str(erro)), 404


@app.errorhandler(sqlite3.IntegrityError)
def conflito(erro):
    texto = str(erro)
    if 'consultas.' in texto:
        mensagem = 'Este horário já foi reservado para o médico ou paciente.'
    elif 'FOREIGN KEY' in texto:
        mensagem = 'Confira o vínculo selecionado. Cadastros em uso são preservados.'
    else:
        mensagem = 'Este e-mail ou nome já está cadastrado.'
    return jsonify(erro=mensagem), 409


@app.get('/')
def inicio():
    return send_from_directory(RAIZ, 'index.html')


@app.get('/<pasta>/<arquivo>')
def arquivo_publico(pasta, arquivo):
    if pasta not in ('pages', 'css', 'js', 'img'):
        abort(404)
    return send_from_directory(RAIZ / pasta, arquivo)


@app.get('/api/sessao')
def sessao():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_urlsafe(32)
    return jsonify(usuario=dict(g.usuario) if g.usuario else None, token=session['csrf'])


@app.post('/api/cadastro')
def cadastro():
    valor = dados()
    with banco():
        PacienteDAO(banco()).criar(Paciente(valor), valor.get('senha'))
    return jsonify(ok=True), 201


@app.post('/api/login')
def login():
    valor = dados()
    usuario = UsuarioDAO(banco()).buscar(email_valido(valor))
    senha = valor.get('senha')
    if not usuario or not isinstance(senha, str) or not check_password_hash(usuario['senha_hash'], senha):
        abort(401, 'E-mail ou senha incorretos.')
    session.clear()
    session['usuario'] = usuario['id']
    return jsonify(ok=True)


@app.post('/api/logout')
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get('/api/especialidades')
def especialidades():
    return jsonify(EspecialidadeDAO(banco()).listar())


@app.get('/api/medicos')
def medicos():
    return jsonify(MedicoDAO(banco()).listar())


@app.get('/api/admin/horarios')
@app.get('/api/horarios')
def horarios():
    data = request.args.get('data', '')
    medico = numero(request.args.get('medico_id'))
    paciente = numero(request.args.get('paciente_id')) if request.path.startswith('/api/admin/') else paciente_atual()
    ocupados = ConsultaDAO(banco()).ocupados(medico, data, paciente)
    return jsonify([h for h in Consulta.horarios(data) if h not in ocupados])


@app.route('/api/consultas', methods=['GET', 'POST'])
def consultas():
    paciente = paciente_atual()
    dao = ConsultaDAO(banco())
    if request.method in ('GET', 'HEAD'):
        return jsonify(dao.listar(paciente))
    with banco():
        dao.criar(paciente, Consulta(dados()))
    return jsonify(ok=True), 201


@app.post('/api/consultas/<int:codigo>/cancelar')
def cancelar(codigo):
    with banco():
        ConsultaDAO(banco()).mudar_status(codigo, 'Cancelada', paciente_atual())
    return jsonify(ok=True)


@app.put('/api/perfil')
def perfil():
    with banco():
        PacienteDAO(banco()).editar(paciente_atual(), Paciente(dados()))
    return jsonify(ok=True)


@app.post('/api/contatos')
def contato():
    with banco():
        ContatoDAO(banco()).criar(Contato(dados()))
    return jsonify(ok=True), 201


@app.get('/api/admin/resumo')
def painel():
    db = banco()
    return jsonify(pacientes=PacienteDAO(db).listar(), medicos=MedicoDAO(db).listar(),
                   especialidades=EspecialidadeDAO(db).listar(), consultas=ConsultaDAO(db).listar(),
                   estatisticas=ConsultaDAO(db).estatisticas(), contatos=ContatoDAO(db).listar())


@app.route('/api/admin/<grupo>', methods=['POST'])
@app.route('/api/admin/<grupo>/<int:codigo>', methods=['PUT', 'DELETE'])
def gerenciar(grupo, codigo=None):
    db = banco()
    with db:
        if grupo == 'consultas' and request.method != 'DELETE':
            valor = dados()
            if codigo is None:
                ConsultaDAO(db).criar(numero(valor.get('paciente_id')), Consulta(valor))
            elif valor.get('status') in ('Cancelada', 'Realizada'):
                ConsultaDAO(db).mudar_status(codigo, valor['status'])
            else:
                raise ValueError('Escolha um status válido.')
        elif grupo == 'pacientes':
            dao = PacienteDAO(db)
            if request.method == 'DELETE':
                dao.excluir(codigo)
            elif codigo is None:
                valor = dados()
                dao.criar(Paciente(valor), valor.get('senha'))
            else:
                dao.editar(codigo, Paciente(dados()))
        elif grupo in ('especialidades', 'medicos'):
            dao, classe = (EspecialidadeDAO(db), Especialidade) if grupo == 'especialidades' else (MedicoDAO(db), Medico)
            if request.method == 'DELETE':
                dao.excluir(codigo)
            else:
                dao.salvar(classe(dados()), codigo)
        else:
            abort(404)
    return jsonify(ok=True)


if __name__ == '__main__':
    with app.app_context():
        iniciar()
    app.run(host='127.0.0.1', port=5000)
