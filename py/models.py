import re
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

HORARIOS = [f'{hora:02}:00' for hora in (8, 9, 10, 11, 13, 14, 15, 16, 17)]
FOTOS = ['helena', 'andre', 'teresa', 'marina', 'perfil']


def campo(dados, chave, limite, minimo=1):
    valor = dados.get(chave, '')
    if not isinstance(valor, str) or not minimo <= len(valor.strip()) <= limite:
        raise ValueError(f'Confira o campo {chave}.')
    return valor.strip()


def email_valido(dados):
    email = campo(dados, 'email', 150).lower()
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        raise ValueError('Informe um e-mail válido.')
    return email


def numero(valor):
    if not str(valor).isascii() or not str(valor).isdigit() or len(str(valor)) > 9:
        raise ValueError('Selecione uma opção válida.')
    return int(valor)


class Usuario:
    def __init__(self, dados):
        self.nome = campo(dados, 'nome', 90, 2)
        self.email = email_valido(dados)

    def gerar_hash(self, senha):
        if not isinstance(senha, str) or not 8 <= len(senha) <= 128:
            raise ValueError('Use uma senha entre 8 e 128 caracteres.')
        return generate_password_hash(senha)


class Paciente(Usuario):
    def __init__(self, dados):
        super().__init__(dados)
        self.telefone = campo(dados, 'telefone', 20, 0)
        if self.telefone and not re.fullmatch(r'[0-9()+ -]{8,20}', self.telefone):
            raise ValueError('Confira o telefone, incluindo o DDD.')


class Medico:
    def __init__(self, dados):
        self.nome = campo(dados, 'nome', 90, 2)
        self.especialidade_id = numero(dados.get('especialidade_id'))
        self.foto = dados.get('foto', 'perfil')
        if self.foto not in FOTOS:
            raise ValueError('Escolha uma foto da lista.')


class Especialidade:
    def __init__(self, dados):
        self.nome = campo(dados, 'nome', 70, 2)
        self.descricao = campo(dados, 'descricao', 350)
        self.area = dados.get('area')
        if self.area not in ('Geral', 'Especializada'):
            raise ValueError('Selecione a área de atendimento.')


class Consulta:
    def __init__(self, dados):
        self.medico_id = numero(dados.get('medico_id'))
        self.data = campo(dados, 'data', 10)
        self.hora = campo(dados, 'hora', 5)
        if self.hora not in self.horarios(self.data):
            raise ValueError('Escolha um horário futuro em dia útil, nos próximos 90 dias.')

    @staticmethod
    def horarios(data):
        try:
            dia = datetime.strptime(data, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            raise ValueError('Informe uma data válida.')
        agora = datetime.now()
        if dia.isoformat() != data or dia.weekday() >= 5 or dia > agora.date() + timedelta(days=90):
            return []
        return [h for h in HORARIOS if f'{data} {h}' > agora.strftime('%Y-%m-%d %H:%M')]


class Contato:
    def __init__(self, dados):
        self.nome = campo(dados, 'nome', 90, 2)
        self.email = email_valido(dados)
        self.mensagem = campo(dados, 'mensagem', 1500, 5)
