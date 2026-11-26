// Cliente HTTP do core-api, usado só pelo processo principal.
// A tela (renderer) nunca fala com a rede: ela pede por IPC e este módulo valida tudo de novo,
// porque o que chega do renderer é tratado como entrada não confiável.

const LIMITE_NOME = 200;
const LIMITE_CONTEUDO = 1_000_000;
const LIMITE_PERGUNTA = 500;
const LIMITE_ARQUIVO = 20 * 1024 * 1024;
const TEMPO_LIMITE_MS = 60_000;
const VISIBILIDADES = new Set(['publico', 'interno']);
const MODOS = new Set(['semantica', 'hibrida', 'palavras']);
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const HOSTS_LOCAIS = new Set(['localhost', '127.0.0.1', '[::1]']);

export const ENDERECOS_PADRAO = Object.freeze({
  coreApi: 'http://localhost:8000',
  mcp: 'http://localhost:8001',
  agente: 'http://localhost:8002',
});

export const SERVICOS = Object.freeze(['coreApi', 'mcp', 'agente']);

export class ErroBackend extends Error {
  /** @param {'fora_do_ar'|'nao_disponivel'|'recusado'|'invalido'|'erro'} tipo */
  constructor(tipo, mensagem) {
    super(mensagem);
    this.tipo = tipo;
  }
}

/**
 * Aceita só http(s), sem usuário/senha na URL. HTTP sem TLS só para a própria máquina:
 * os serviços ainda não têm autenticação e os documentos trafegariam abertos na rede.
 */
export function validarEndereco(valor) {
  if (typeof valor !== 'string' || valor.length > 300) {
    throw new ErroBackend('invalido', 'Endereço inválido.');
  }
  let url;
  try {
    url = new URL(valor.trim());
  } catch {
    throw new ErroBackend('invalido', 'Endereço inválido. Exemplo: http://localhost:8000');
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new ErroBackend('invalido', 'O endereço precisa começar com http:// ou https://.');
  }
  if (url.username || url.password) {
    throw new ErroBackend('invalido', 'Não coloque usuário ou senha no endereço.');
  }
  if (url.protocol === 'http:' && !HOSTS_LOCAIS.has(url.hostname)) {
    throw new ErroBackend(
      'invalido',
      'Sem https, só é aceito um servidor nesta máquina (localhost). Para outro computador, use https.',
    );
  }
  return url.origin;
}

function texto(valor, nome, maximo) {
  if (typeof valor !== 'string' || valor.length < 1 || valor.length > maximo) {
    throw new ErroBackend('invalido', `Campo "${nome}" ausente ou grande demais.`);
  }
  return valor;
}

function visibilidade(valor) {
  if (!VISIBILIDADES.has(valor)) throw new ErroBackend('invalido', 'Visibilidade inválida.');
  return valor;
}

function identificador(valor) {
  if (typeof valor !== 'string' || !UUID.test(valor)) {
    throw new ErroBackend('invalido', 'Identificador de documento inválido.');
  }
  return valor;
}

function inteiro(valor, minimo, maximo, padrao) {
  if (valor === undefined || valor === null) return padrao;
  if (!Number.isInteger(valor) || valor < minimo || valor > maximo) {
    throw new ErroBackend('invalido', 'Número fora do intervalo aceito.');
  }
  return valor;
}

/** @param {{coreApi: string, mcp: string, agente: string}} enderecos @param {typeof fetch} buscarNaRede */
export function criarBackend(enderecos, buscarNaRede = fetch) {
  async function pedir(base, caminho, opcoes = {}) {
    let resposta;
    try {
      resposta = await buscarNaRede(new URL(caminho, base), {
        ...opcoes,
        redirect: 'error', // um servidor não pode nos mandar para outro endereço
        signal: AbortSignal.timeout(opcoes.tempoLimite ?? TEMPO_LIMITE_MS),
        headers: { accept: 'application/json', ...opcoes.headers },
      });
    } catch {
      throw new ErroBackend('fora_do_ar', 'Não consegui falar com o servidor. Ele está no ar?');
    }
    let corpo = null;
    try {
      corpo = await resposta.json();
    } catch {
      corpo = null;
    }
    if (resposta.ok) return corpo;
    // Endpoint que ainda não existe no servidor (previsto para a próxima etapa). Um 404 de rota
    // inexistente vem do FastAPI com "Not Found"; um 404 nosso traz a frase do que não foi achado.
    const rotaAusente =
      resposta.status === 501 ||
      ([404, 405].includes(resposta.status) && ['Not Found', 'Method Not Allowed'].includes(corpo?.detail));
    if (rotaAusente && opcoes.planejado) {
      throw new ErroBackend('nao_disponivel', 'O servidor ainda não oferece esta função.');
    }
    const detalhe = corpo && typeof corpo.detail === 'string' ? corpo.detail.slice(0, 300) : null;
    if (resposta.status === 503) {
      throw new ErroBackend('fora_do_ar', detalhe ?? 'Serviço temporariamente indisponível.');
    }
    if (resposta.status >= 400 && resposta.status < 500) {
      throw new ErroBackend('recusado', detalhe ?? `O servidor recusou o pedido (HTTP ${resposta.status}).`);
    }
    throw new ErroBackend('erro', `O servidor falhou (HTTP ${resposta.status}).`);
  }

  const json = (corpo) => ({
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(corpo),
  });

  return {
    async saude() {
      const ver = async (base) => {
        try {
          await pedir(base, '/health', { tempoLimite: 4000 });
          return 'no_ar';
        } catch {
          return 'fora_do_ar';
        }
      };
      const [coreApi, mcp, agente] = await Promise.all(SERVICOS.map((nome) => ver(enderecos[nome])));
      return { coreApi, mcp, agente };
    },

    async listarDocumentos() {
      const dados = await pedir(enderecos.coreApi, '/documentos', { planejado: true });
      return Array.isArray(dados?.documentos) ? dados.documentos : [];
    },

    async enviarDocumento(novo) {
      return pedir(
        enderecos.coreApi,
        '/documentos',
        json({
          nome: texto(novo?.nome, 'nome', LIMITE_NOME),
          conteudo: texto(novo?.conteudo, 'conteudo', LIMITE_CONTEUDO),
          visibilidade: visibilidade(novo?.visibilidade),
        }),
      );
    },

    /** PDF e imagem: o conteúdo vai no corpo e o servidor põe na fila de processamento. */
    async enviarArquivo(novo) {
      const bytes = novo?.bytes instanceof ArrayBuffer ? new Uint8Array(novo.bytes) : novo?.bytes;
      if (!(bytes instanceof Uint8Array) || bytes.byteLength === 0) {
        throw new ErroBackend('invalido', 'Arquivo ausente ou vazio.');
      }
      if (bytes.byteLength > LIMITE_ARQUIVO) {
        throw new ErroBackend('invalido', 'Arquivo grande demais: o limite é 20 MB.');
      }
      const parametros = new URLSearchParams({
        nome: texto(novo?.nome, 'nome', LIMITE_NOME),
        visibilidade: visibilidade(novo?.visibilidade),
      });
      return pedir(enderecos.coreApi, `/documentos/arquivo?${parametros}`, {
        method: 'POST',
        headers: { 'content-type': 'application/octet-stream' },
        body: bytes,
        planejado: true,
      });
    },

    async excluirDocumento(id) {
      await pedir(enderecos.coreApi, `/documentos/${identificador(id)}`, {
        method: 'DELETE',
        planejado: true,
      });
      return null;
    },

    async alterarVisibilidade(pedido) {
      return pedir(enderecos.coreApi, `/documentos/${identificador(pedido?.id)}`, {
        ...json({ visibilidade: visibilidade(pedido?.visibilidade) }),
        method: 'PATCH',
        planejado: true,
      });
    },

    async detalharDocumento(id) {
      return pedir(enderecos.coreApi, `/documentos/${identificador(id)}`, { planejado: true });
    },

    async buscar(pedido) {
      const modo = pedido?.modo ?? 'semantica';
      if (!MODOS.has(modo)) throw new ErroBackend('invalido', 'Modo de busca inválido.');
      const parametros = new URLSearchParams({
        pergunta: texto(pedido?.pergunta, 'pergunta', LIMITE_PERGUNTA),
        k: String(inteiro(pedido?.k, 1, 10, 3)),
        visibilidade: visibilidade(pedido?.visibilidade),
        modo,
      });
      const dados = await pedir(enderecos.coreApi, `/busca?${parametros}`);
      return Array.isArray(dados?.resultados) ? dados.resultados : [];
    },

    async perguntarAoAtendente(pedido) {
      return pedir(enderecos.agente, '/perguntas', {
        ...json({ pergunta: texto(pedido?.pergunta, 'pergunta', LIMITE_PERGUNTA) }),
        planejado: true,
      });
    },

    async avaliacao() {
      return pedir(enderecos.coreApi, '/avaliacao', { planejado: true });
    },

    /** Roda de novo o último conjunto de perguntas contra o acervo de agora. */
    async rodarAvaliacao() {
      return pedir(enderecos.coreApi, '/avaliacao/execucoes', { ...json({}), planejado: true });
    },
  };
}
