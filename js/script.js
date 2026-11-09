"use strict";

const $ = (seletor) => document.querySelector(seletor);
const pagina = document.body.dataset.pagina;
const parametros = new URLSearchParams(location.search);
const raiz = new URL("../", document.currentScript.src).pathname;
const demonstracao = location.hostname.endsWith(".github.io");
const catalogo = {
  "especialidades": [
    {
      "area": "Geral",
      "descricao": "Um primeiro encontro para conversar sobre sua saúde e planejar o acompanhamento.",
      "id": 1,
      "nome": "Clínica geral",
      "profissionais": 1
    },
    {
      "area": "Especializada",
      "descricao": "Consultas voltadas ao coração e ao acompanhamento da saúde cardiovascular.",
      "id": 2,
      "nome": "Cardiologia",
      "profissionais": 1
    },
    {
      "area": "Especializada",
      "descricao": "Atenção à saúde da pele, dos cabelos e das unhas em diferentes fases da vida.",
      "id": 3,
      "nome": "Dermatologia",
      "profissionais": 1
    },
    {
      "area": "Especializada",
      "descricao": "Acompanhamento individual para envelhecer com autonomia e qualidade de vida.",
      "id": 4,
      "nome": "Geriatria",
      "profissionais": 1
    }
  ],
  "medicos": [
    {
      "especialidade": "Clínica geral",
      "especialidade_id": 1,
      "foto": "helena",
      "id": 1,
      "nome": "Dra. Helena Prado"
    },
    {
      "especialidade": "Cardiologia",
      "especialidade_id": 2,
      "foto": "andre",
      "id": 2,
      "nome": "Dr. André Luz"
    },
    {
      "especialidade": "Dermatologia",
      "especialidade_id": 3,
      "foto": "marina",
      "id": 3,
      "nome": "Dra. Marina Reis"
    },
    {
      "especialidade": "Geriatria",
      "especialidade_id": 4,
      "foto": "teresa",
      "id": 4,
      "nome": "Dra. Teresa Vale"
    }
  ]
};
let usuario;
let token;
let medicos = [];
let especialidades = [];
let resumo;

function seguro(valor) {
  return String(valor ?? "").replace(
    /[&<>"']/g,
    (letra) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[letra],
  );
}

function icone(nome) {
  return (
    '<svg class="icon" aria-hidden="true"><use href="' + raiz + 'img/icones.svg#' +
    nome +
    '"></use></svg>'
  );
}

async function api(caminho, metodo = "GET", dados) {
  if (demonstracao) {
    if (caminho === "sessao") return {usuario: null, token: ""};
    if (Object.hasOwn(catalogo, caminho)) return catalogo[caminho];
    throw new Error("Este recurso precisa do servidor Flask da clínica.");
  }
  const resposta = await fetch("/api/" + caminho, {
    method: metodo,
    headers: {
      "X-CSRF-Token": token || "",
      "Content-Type": "application/json",
    },
    body: dados === undefined ? undefined : JSON.stringify(dados),
  });
  const resultado = await resposta.json();
  if (!resposta.ok)
    throw new Error(resultado.erro || "Falha ao acessar a clínica.");
  return resultado;
}

function aviso(elemento, texto, erro = false) {
  elemento.classList.toggle("erro", erro);
  elemento.textContent = texto;
}

function formulario(id, acao) {
  const form = document.getElementById(id);
  if (!form) return;
  form.onsubmit = async (evento) => {
    evento.preventDefault();
    const botao = evento.submitter || form.querySelector("button");
    const mensagem = form.querySelector(".feedback");
    botao.disabled = true;
    try {
      const texto = await acao(Object.fromEntries(new FormData(form)), form);
      if (texto) aviso(mensagem, texto);
    } catch (erro) {
      aviso(mensagem, erro.message, true);
    } finally {
      botao.disabled = false;
    }
  };
}

function opcoes(itens, primeiro = "Selecione") {
  return (
    '<option value="">' +
    primeiro +
    "</option>" +
    itens
      .map(
        (item) =>
          '<option value="' +
          seguro(item.id) +
          '">' +
          seguro(item.nome) +
          "</option>",
      )
      .join("")
  );
}

function vazio(texto) {
  return '<p class="notice">' + seguro(texto) + "</p>";
}

function mostrarEspecialidades() {
  const busca = $("[name=busca]")?.value.toLocaleLowerCase().trim() || "";
  const area = $("#area")?.value;
  const itens = especialidades.filter(
    (e) =>
      e.nome.toLocaleLowerCase().includes(busca) && (!area || e.area === area),
  );
  const simbolos = ["clinica", "coracao", "pele", "folha"];
  $("#especialidades").innerHTML =
    itens
      .map(
        (e) => `<article class="card">
    <span class="tile">${icone(simbolos[e.id - 1] || "clinica")}</span><h3>${seguro(e.nome)}</h3>
    <p>${seguro(e.descricao)}</p><a class="link" href="${raiz}pages/medicos.html?especialidade=${e.id}">Ver médicos ${icone("arrow")}</a></article>`,
      )
      .join("") || vazio("Nenhuma especialidade encontrada.");
}

function mostrarMedicos() {
  const busca = $("[name=busca]")?.value.toLocaleLowerCase().trim() || "";
  const filtro = $("#filtro-medico")?.value;
  const itens = medicos.filter(
    (m) =>
      m.nome.toLocaleLowerCase().includes(busca) &&
      (!filtro || m.especialidade_id === Number(filtro)),
  );
  $("#medicos").innerHTML =
    itens
      .map(
        (m) => `<article class="doc">
    <img loading="lazy" src="${raiz}img/${seguro(m.foto)}.${m.foto === "perfil" ? "svg" : "webp"}" alt="${seguro(m.nome)}">
    <div><p class="eyebrow">${seguro(m.especialidade)}</p><h3>${seguro(m.nome)}</h3>
    <p><a class="link" href="${raiz}pages/agendamento.html?medico=${m.id}">Ver agenda ${icone("arrow")}</a></p></div></article>`,
      )
      .join("") || vazio("Nenhum médico encontrado.");
}

function acesso(papel) {
  if (usuario?.papel === papel) return true;
  $(".protegido").hidden = true;
  const destino = encodeURIComponent(location.pathname + location.search);
  $("#acesso").innerHTML =
    vazio(
      usuario
        ? "Esta página requer uma conta de " + papel + "."
        : "Entre na sua conta para continuar.",
    ) +
    '<a class="btn" href="' + raiz + 'pages/cadastro.html?voltar=' +
    destino +
    '">Área do paciente</a>';
  return false;
}

function destinoLogin() {
  const voltar = parametros.get("voltar") || "";
  if (/^\/pages\/[a-z-]+\.html(\?[a-z]+=\d+)?$/.test(voltar)) return voltar;
  return (
    "/pages/" +
    (usuario.papel === "admin" ? "administracao" : "minhas-consultas") +
    ".html"
  );
}

function contas() {
  if (usuario) {
    $("#formularios").hidden = true;
    $("#logado").innerHTML =
      `<h2>Olá, ${seguro(usuario.nome)}.</h2><div class="actions">
      <a class="btn" href="${seguro(destinoLogin())}">Abrir minha área</a>
      <button class="sec" id="sair">Sair da conta</button></div>`;
    $("#sair").onclick = async () => {
      await api("logout", "POST");
      location.reload();
    };
  }
  formulario("login", async (dados) => {
    await api("login", "POST", dados);
    usuario = (await api("sessao")).usuario;
    location.assign(destinoLogin());
  });
  formulario("cadastro", async (dados, form) => {
    await api("cadastro", "POST", dados);
    form.reset();
    $("#login").elements.email.value = dados.email;
    return "Cadastro realizado. Entre com seu e-mail e senha.";
  });
}

function dataLocal(dia) {
  return [
    dia.getFullYear(),
    String(dia.getMonth() + 1).padStart(2, "0"),
    String(dia.getDate()).padStart(2, "0"),
  ].join("-");
}

function configurarHorarios(form, admin = false) {
  const { data, medico_id, hora, paciente_id } = form.elements;
  const hoje = new Date();
  data.min = dataLocal(hoje);
  hoje.setDate(hoje.getDate() + 90);
  data.max = dataLocal(hoje);
  let versao = 0;
  async function atualizar() {
    const atual = ++versao;
    hora.innerHTML = opcoes([], "Selecione médico e data");
    if (!data.value || !medico_id.value || (admin && !paciente_id.value))
      return;
    const filtros = new URLSearchParams({
      data: data.value,
      medico_id: medico_id.value,
    });
    if (admin) filtros.set("paciente_id", paciente_id.value);
    try {
      const lista = await api((admin ? "admin/" : "") + "horarios?" + filtros);
      if (atual !== versao) return;
      hora.innerHTML = opcoes(
        lista.map((h) => ({ id: h, nome: h })),
        lista.length ? "Escolha o horário" : "Sem horários nesta data",
      );
    } catch (erro) {
      if (atual === versao)
        aviso(form.querySelector(".feedback"), erro.message, true);
    }
  }
  data.onchange = atualizar;
  medico_id.onchange = atualizar;
  if (admin) paciente_id.onchange = atualizar;
  return atualizar;
}

function agendamento() {
  if (!acesso("paciente")) return;
  const form = $("#agendar");
  const { especialidade_id, medico_id } = form.elements;
  especialidade_id.innerHTML = opcoes(especialidades);
  const atualizar = configurarHorarios(form);
  especialidade_id.onchange = () => {
    medico_id.innerHTML = opcoes(
      medicos.filter(
        (m) => m.especialidade_id === Number(especialidade_id.value),
      ),
    );
    atualizar();
  };
  const escolhido = medicos.find(
    (m) => m.id === Number(parametros.get("medico")),
  );
  if (escolhido) especialidade_id.value = escolhido.especialidade_id;
  especialidade_id.onchange();
  if (escolhido) medico_id.value = escolhido.id;
  formulario("agendar", async (dados) => {
    try {
      await api("consultas", "POST", dados);
      location.assign("/pages/minhas-consultas.html");
    } catch (erro) {
      await atualizar();
      throw erro;
    }
  });
}

function linha(titulo, detalhe, acoes = "") {
  return `<article class="registro"><div><b>${seguro(titulo)}</b><small>${seguro(detalhe)}</small></div><div class="actions">${acoes}</div></article>`;
}

function dataBr(data) {
  return data.split("-").reverse().join("/");
}

function linhaConsulta(c, cancelar = false) {
  const acao = cancelar
    ? `<button class="sec" data-cancelar="${c.id}">Cancelar</button>`
    : "";
  return linha(
    dataBr(c.data) + " · " + c.hora,
    [c.medico, c.especialidade, c.status].join(" · "),
    acao,
  );
}

async function minhaArea() {
  if (!acesso("paciente")) return;
  const lista = await api("consultas");
  if (pagina === "perfil") {
    const form = $("#perfil");
    for (const chave of ["nome", "email", "telefone"])
      form.elements[chave].value = usuario[chave] || "";
    $("#recentes").innerHTML =
      lista
        .slice(0, 4)
        .map((c) => linhaConsulta(c))
        .join("") || vazio("Ainda não há consultas.");
    formulario("perfil", async (dados) => {
      await api("perfil", "PUT", dados);
      return "Dados atualizados.";
    });
    return;
  }
  const agenda = lista.filter((c) => c.status === "Agendada").reverse();
  $("#agenda").innerHTML =
    agenda.map((c) => linhaConsulta(c, true)).join("") ||
    vazio("Nenhuma consulta agendada.");
  $("#historico").innerHTML =
    lista
      .filter((c) => c.status !== "Agendada")
      .map((c) => linhaConsulta(c))
      .join("") || vazio("Nenhuma consulta no histórico.");
  $("#agenda").onclick = async (evento) => {
    const id = evento.target.closest("[data-cancelar]")?.dataset.cancelar;
    if (!id || !confirm("Cancelar esta consulta e liberar o horário?")) return;
    try {
      await api("consultas/" + id + "/cancelar", "POST");
      await minhaArea();
    } catch (erro) {
      alert(erro.message);
    }
  };
}

const rotulos = {
  consultas: "Consultas",
  pacientes: "Pacientes",
  medicos: "Médicos",
  especialidades: "Especialidades",
};
function botao(acao, id, texto) {
  return `<button class="sec" data-acao="${acao}" data-id="${id}">${texto}</button>`;
}

function registros() {
  const grupo = $("#grupo").value;
  $("#edicao").replaceChildren();
  $("#novo").hidden = grupo === "contatos";
  $("#registros").innerHTML =
    resumo[grupo]
      .map((r) => {
        if (grupo === "contatos")
          return linha(r.nome + " · " + r.email, r.mensagem);
        if (grupo === "consultas") {
          const podeConcluir =
            r.data + "T" + r.hora <=
            dataLocal(new Date()) + "T" + new Date().toTimeString().slice(0, 5);
          let botoes = "";
          if (r.status === "Agendada")
            botoes =
              botao("Cancelar", r.id, "Cancelar") +
              (podeConcluir ? botao("Concluir", r.id, "Concluir") : "");
          return linha(
            r.paciente + " · " + r.medico,
            dataBr(r.data) + " · " + r.hora + " · " + r.status,
            botoes,
          );
        }
        return linha(
          r.nome,
          r.especialidade || r.email || r.descricao,
          botao("Editar", r.id, "Editar") + botao("Excluir", r.id, "Excluir"),
        );
      })
      .join("") || vazio("Nenhum registro nesta seção.");
}

async function painel() {
  resumo = await api("admin/resumo");
  $("#indicadores").innerHTML = Object.entries(rotulos)
    .map(
      ([k, v]) =>
        `<article class="card"><h3>${resumo[k].length}</h3><p>${v}</p></article>`,
    )
    .join("");
  $("#grafico").innerHTML = ["Agendada", "Realizada", "Cancelada"]
    .map((status) => {
      const total =
        resumo.estatisticas.find((s) => s.status === status)?.total || 0;
      return `<label>${status}<progress value="${total}" max="${resumo.consultas.length || 1}"></progress><b>${total}</b></label>`;
    })
    .join("");
  $("#equipe-grafico").innerHTML =
    resumo.especialidades
      .map(
        (e) =>
          `<label>${seguro(e.nome)}<progress value="${e.profissionais}" max="${resumo.medicos.length || 1}"></progress><b>${e.profissionais}</b></label>`,
      )
      .join("") || vazio("Nenhuma especialidade cadastrada.");
  registros();
}

function entrada(titulo, nome, tipo = "text", extra = "required") {
  return `<label>${titulo}<input name="${nome}" type="${tipo}" ${extra}></label>`;
}

function escolha(titulo, nome, itens) {
  return `<label>${titulo}<select name="${nome}" required>${opcoes(itens)}</select></label>`;
}

function editor(id) {
  const grupo = $("#grupo").value;
  let campos = entrada("Nome", "nome");
  if (grupo === "especialidades")
    campos +=
      entrada("Descrição", "descricao") +
      escolha("Área", "area", [
        { id: "Geral", nome: "Geral" },
        { id: "Especializada", nome: "Especializada" },
      ]);
  if (grupo === "medicos") {
    campos += escolha(
      "Especialidade",
      "especialidade_id",
      resumo.especialidades,
    );
    const fotos = ["perfil", "helena", "andre", "marina", "teresa"];
    campos += escolha(
      "Retrato",
      "foto",
      fotos.map((f) => ({
        id: f,
        nome: f === "perfil" ? "Ilustração de perfil" : "Foto · " + f,
      })),
    );
  }
  if (grupo === "pacientes") {
    campos +=
      entrada("E-mail", "email", "email") +
      entrada("Telefone (opcional)", "telefone", "tel", 'maxlength="20"');
    if (!id)
      campos += entrada(
        "Senha inicial",
        "senha",
        "password",
        'required minlength="8" maxlength="128"',
      );
  }
  if (grupo === "consultas")
    campos =
      escolha("Paciente", "paciente_id", resumo.pacientes) +
      escolha("Médico", "medico_id", resumo.medicos) +
      entrada("Data", "data", "date") +
      escolha("Horário", "hora", []);
  $("#edicao").innerHTML =
    `<form class="panel" id="editor"><h2>${id ? "Editar" : "Novo registro"} · ${rotulos[grupo]}</h2>${campos}<div class="actions"><button class="btn">Salvar</button><button type="button" class="sec" id="fechar">Fechar</button></div><p role="status" class="feedback"></p></form>`;
  const form = $("#editor");
  if (grupo === "consultas") configurarHorarios(form, true);
  if (grupo === "medicos") form.elements.foto.value = "perfil";
  const registro = resumo[grupo].find((r) => r.id === id);
  if (registro)
    for (const campo of form.elements) {
      if (campo.name && registro[campo.name] !== undefined)
        campo.value = registro[campo.name];
    }
  $("#fechar").onclick = () => $("#edicao").replaceChildren();
  form.elements[0].focus();
  formulario("editor", async (dados) => {
    await api(
      "admin/" + grupo + (id ? "/" + id : ""),
      id ? "PUT" : "POST",
      dados,
    );
    await painel();
  });
}

async function administracao() {
  if (!acesso("admin")) return;
  await painel();
  $("#grupo").onchange = registros;
  $("#novo").onclick = () => editor(null);
  $("#registros").onclick = async (evento) => {
    const alvo = evento.target.closest("[data-acao]");
    if (!alvo) return;
    const { acao, id } = alvo.dataset;
    if (acao === "Editar") return editor(Number(id));
    if (!confirm(acao + " este registro?")) return;
    try {
      const caminho = "admin/" + $("#grupo").value + "/" + id;
      if (acao === "Excluir") await api(caminho, "DELETE");
      else
        await api(caminho, "PUT", {
          status: acao === "Cancelar" ? "Cancelada" : "Realizada",
        });
      await painel();
    } catch (erro) {
      alert(erro.message);
    }
  };
}

async function iniciar() {
  $("#menu").onclick = () =>
    $("#menu").setAttribute(
      "aria-expanded",
      $("#nav").classList.toggle("aberto"),
    );
  if (demonstracao && ["agendamento","minhas-consultas","cadastro","contato","administracao","perfil"].includes(pagina)) {
    const area = document.querySelector("main > .section");
    if (area) area.innerHTML = vazio("Esta área funciona na versão Flask da clínica. Na demonstração, explore as especialidades e a equipe médica.");
    return;
  }
  const sessao = await api("sessao");
  token = sessao.token;
  usuario = sessao.usuario;
  if (usuario) $("#conta-texto").textContent = "Minha conta";
  if (["inicio", "especialidades", "medicos", "agendamento"].includes(pagina)) {
    [especialidades, medicos] = await Promise.all([
      api("especialidades"),
      api("medicos"),
    ]);
  }
  if ($("#especialidades")) mostrarEspecialidades();
  if ($("#filtro-medico")) {
    $("#filtro-medico").innerHTML = opcoes(
      especialidades,
      "Todas as especialidades",
    );
    $("#filtro-medico").value = parametros.get("especialidade") || "";
    $("#filtro-medico").onchange = mostrarMedicos;
  }
  if ($("#medicos")) mostrarMedicos();
  if (pagina === "especialidades") {
    $("[name=busca]").oninput = mostrarEspecialidades;
    $("#area").onchange = mostrarEspecialidades;
  }
  if (pagina === "medicos") $("[name=busca]").oninput = mostrarMedicos;
  if (pagina === "cadastro") contas();
  if (pagina === "agendamento") agendamento();
  if (["perfil", "minhas-consultas"].includes(pagina)) await minhaArea();
  if (pagina === "administracao") await administracao();
  formulario("contato", async (dados, form) => {
    await api("contatos", "POST", dados);
    form.reset();
    return "Mensagem recebida pela recepção.";
  });
}

iniciar().catch((erro) => {
  const caixa = document.createElement("p");
  caixa.className = "wrap notice erro";
  caixa.textContent = erro.message;
  $("#principal").prepend(caixa);
});

