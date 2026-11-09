PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    senha_hash TEXT NOT NULL,
    papel TEXT NOT NULL CHECK (papel IN ('paciente','admin'))
);
CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    telefone TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS especialidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL COLLATE NOCASE UNIQUE,
    descricao TEXT NOT NULL,
    area TEXT NOT NULL CHECK (area IN ('Geral','Especializada'))
);
CREATE TABLE IF NOT EXISTS medicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL COLLATE NOCASE UNIQUE,
    especialidade_id INTEGER NOT NULL REFERENCES especialidades(id),
    foto TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS consultas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
    medico_id INTEGER NOT NULL REFERENCES medicos(id),
    data TEXT NOT NULL,
    hora TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Agendada' CHECK(status IN ('Agendada','Cancelada','Realizada'))
);
CREATE UNIQUE INDEX IF NOT EXISTS horario_do_medico
ON consultas(medico_id, data, hora) WHERE status = 'Agendada';
CREATE UNIQUE INDEX IF NOT EXISTS horario_do_paciente
ON consultas(paciente_id, data, hora) WHERE status = 'Agendada';
CREATE TABLE IF NOT EXISTS contatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT NOT NULL,
    mensagem TEXT NOT NULL, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
