// Servidor de verdade: cada chamada atravessa o preload e é feita pelo processo principal.
import { ehTexto, formatoDe } from './formatos';
import {
  ErroDoServidor,
  type Avaliacao,
  type DetalheDoDocumento,
  type Enderecos,
  type Documento,
  type RespostaDoAtendente,
  type ResultadoDeBusca,
  type Saude,
  type Servidor,
  type Situacao,
  type TipoDeErro,
  type Visibilidade,
} from './tipos';

type Envelope<T> = { ok: true; dados: T } | { ok: false; erro: { tipo: TipoDeErro; mensagem: string } };

export interface Ponte {
  plataforma: string;
  chamar(metodo: string, argumento?: unknown): Promise<Envelope<unknown>>;
  enderecos(): Promise<Envelope<Enderecos>>;
  salvarEnderecos(novos: Enderecos): Promise<Envelope<Enderecos>>;
}

export function abrir<T>(envelope: Envelope<T>): T {
  if (envelope.ok) return envelope.dados;
  throw new ErroDoServidor(envelope.erro.tipo, envelope.erro.mensagem);
}

const SITUACOES: Situacao[] = ['na_fila', 'extraindo', 'indexando', 'indexado', 'falhou'];

/** O que vem do servidor é conferido campo a campo: nada entra na tela só por estar no JSON. */
export function lerDocumento(bruto: unknown): Documento | null {
  if (typeof bruto !== 'object' || bruto === null) return null;
  const d = bruto as Record<string, unknown>;
  if (typeof d.id !== 'string' || typeof d.nome !== 'string') return null;
  if (d.visibilidade !== 'publico' && d.visibilidade !== 'interno') return null;
  const situacao = SITUACOES.includes(d.situacao as Situacao) ? (d.situacao as Situacao) : 'indexado';
  return {
    id: d.id,
    nome: d.nome,
    visibilidade: d.visibilidade,
    trechos: typeof d.trechos === 'number' ? d.trechos : null,
    situacao,
    formato: formatoDe(d.nome) ?? 'texto',
    criadoEm: typeof d.criado_em === 'string' ? d.criado_em : null,
    andamento: typeof d.andamento === 'string' ? d.andamento : undefined,
    erro: typeof d.erro === 'string' ? d.erro : undefined,
    ocr: d.ocr === true ? true : undefined,
    paginas: typeof d.paginas === 'number' ? d.paginas : undefined,
  };
}

function lerResultados(bruto: unknown): ResultadoDeBusca[] {
  if (!Array.isArray(bruto)) return [];
  return bruto.flatMap((item) => {
    const r = item as Record<string, unknown> | null;
    return r && typeof r.trecho === 'string' && typeof r.documento === 'string' && typeof r.score === 'number'
      ? [{ trecho: r.trecho, documento: r.documento, score: r.score }]
      : [];
  });
}

export function criarServidorReal(ponte: Ponte): Servidor {
  const chamar = async <T>(metodo: string, argumento?: unknown) =>
    abrir(await ponte.chamar(metodo, argumento)) as T;

  return {
    saude: () => chamar<Saude>('saude'),

    async listarDocumentos() {
      const lista = await chamar<unknown[]>('listarDocumentos');
      return lista.flatMap((item) => lerDocumento(item) ?? []);
    },

    async enviarDocumento(novo) {
      const formato = formatoDe(novo.nome);
      if (!formato) throw new ErroDoServidor('recusado', 'Formato de arquivo não aceito.');
      if (!ehTexto(formato)) {
        if (!novo.arquivo) throw new ErroDoServidor('invalido', 'Arquivo ausente.');
        await chamar('enviarArquivo', {
          nome: novo.nome,
          visibilidade: novo.visibilidade,
          bytes: await novo.arquivo.arrayBuffer(),
        });
        return;
      }
      if (novo.conteudo === null) throw new ErroDoServidor('invalido', 'Conteúdo ausente.');
      await chamar('enviarDocumento', {
        nome: novo.nome,
        conteudo: novo.conteudo,
        visibilidade: novo.visibilidade,
      });
    },

    async excluirDocumento(id) {
      await chamar('excluirDocumento', id);
    },

    async alterarVisibilidade(id: string, visibilidade: Visibilidade) {
      await chamar('alterarVisibilidade', { id, visibilidade });
    },

    async detalharDocumento(id) {
      const bruto = await chamar<Record<string, unknown>>('detalharDocumento', id);
      const documento = lerDocumento(bruto?.documento);
      if (!documento) throw new ErroDoServidor('erro', 'O servidor respondeu fora do contrato.');
      return {
        documento,
        trechos: Array.isArray(bruto.trechos) ? (bruto.trechos as DetalheDoDocumento['trechos']) : [],
        passos: Array.isArray(bruto.passos) ? (bruto.passos as DetalheDoDocumento['passos']) : [],
      };
    },

    async buscar(pedido) {
      return lerResultados(await chamar('buscar', pedido));
    },

    async perguntarAoAtendente(pergunta) {
      const bruto = await chamar<Record<string, unknown>>('perguntarAoAtendente', { pergunta });
      if (typeof bruto?.texto !== 'string') {
        throw new ErroDoServidor('erro', 'O servidor respondeu fora do contrato.');
      }
      const fontes = lerResultados(bruto.fontes);
      const respondeu = typeof bruto.respondeu === 'boolean' ? bruto.respondeu : fontes.length > 0;
      return { texto: bruto.texto, fontes, respondeu } satisfies RespostaDoAtendente;
    },

    async avaliacao() {
      const bruto = await chamar<Partial<Avaliacao>>('avaliacao');
      return {
        k: typeof bruto?.k === 'number' ? bruto.k : 3,
        execucoes: Array.isArray(bruto?.execucoes) ? bruto.execucoes : [],
        perguntas: Array.isArray(bruto?.perguntas) ? bruto.perguntas : [],
      };
    },

    async rodarAvaliacao() {
      await chamar('rodarAvaliacao');
    },
  };
}
