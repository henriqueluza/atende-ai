// O contrato entre a tela e o servidor (core-api e serviço do atendente).

export type Visibilidade = 'publico' | 'interno';
export type Situacao = 'na_fila' | 'extraindo' | 'indexando' | 'indexado' | 'falhou';
export type Formato = 'markdown' | 'texto' | 'pdf' | 'imagem';
export type ModoDeBusca = 'semantica' | 'hibrida' | 'palavras';
export type EstadoServico = 'no_ar' | 'fora_do_ar';

export interface Documento {
  id: string;
  nome: string;
  visibilidade: Visibilidade;
  /** null enquanto o documento não terminou de ser processado. */
  trechos: number | null;
  situacao: Situacao;
  formato: Formato;
  criadoEm: string | null;
  /** Andamento da leitura, por exemplo "Lendo a página 2 de 3". */
  andamento?: string;
  /** Motivo da falha, em palavras de quem usa. */
  erro?: string;
  /** O texto veio de leitura de imagem (OCR). */
  ocr?: boolean;
  paginas?: number;
}

export interface PassoDoProcessamento {
  nome: string;
  estado: 'feito' | 'em_andamento' | 'pendente' | 'falhou';
  detalhe?: string;
  quando?: string;
}

export interface DetalheDoDocumento {
  documento: Documento;
  trechos: { posicao: number; texto: string; pagina?: number }[];
  passos: PassoDoProcessamento[];
}

export interface NovoDocumento {
  nome: string;
  visibilidade: Visibilidade;
  /** Texto e markdown vão como texto e são indexados na hora. PDF e imagem entram na fila. */
  conteudo: string | null;
  arquivo: File | null;
}

export interface ResultadoDeBusca {
  trecho: string;
  documento: string;
  score: number;
}

export interface PedidoDeBusca {
  pergunta: string;
  k: number;
  visibilidade: Visibilidade;
  modo: ModoDeBusca;
}

export interface RespostaDoAtendente {
  texto: string;
  fontes: ResultadoDeBusca[];
  /** false quando o atendente respondeu que não encontrou a informação. */
  respondeu: boolean;
}

export interface ExecucaoDaAvaliacao {
  /** Data e hora da execução (ISO). */
  data: string;
  versao: string;
  modo?: ModoDeBusca;
  perguntas: number;
  acertos: number;
  /** Posição média invertida do trecho certo (MRR), de 0 a 1. */
  mrr: number;
  nota?: string | null;
}

export interface PerguntaAvaliada {
  pergunta: string;
  esperado: string;
  /** Posição em que o documento certo apareceu; null se não apareceu entre os 10 primeiros. */
  posicao: number | null;
  primeiro: string;
}

export interface Avaliacao {
  execucoes: ExecucaoDaAvaliacao[];
  /** Todas as perguntas da última execução. */
  perguntas: PerguntaAvaliada[];
  k: number;
}

export interface Saude {
  coreApi: EstadoServico;
  mcp: EstadoServico;
  agente: EstadoServico;
}

export interface Enderecos {
  coreApi: string;
  mcp: string;
  agente: string;
}

export type TipoDeErro = 'fora_do_ar' | 'nao_disponivel' | 'recusado' | 'invalido' | 'erro';

export class ErroDoServidor extends Error {
  constructor(
    readonly tipo: TipoDeErro,
    mensagem: string,
  ) {
    super(mensagem);
  }
}

export interface Servidor {
  saude(): Promise<Saude>;
  listarDocumentos(): Promise<Documento[]>;
  enviarDocumento(novo: NovoDocumento): Promise<void>;
  excluirDocumento(id: string): Promise<void>;
  alterarVisibilidade(id: string, visibilidade: Visibilidade): Promise<void>;
  detalharDocumento(id: string): Promise<DetalheDoDocumento>;
  buscar(pedido: PedidoDeBusca): Promise<ResultadoDeBusca[]>;
  perguntarAoAtendente(pergunta: string): Promise<RespostaDoAtendente>;
  avaliacao(): Promise<Avaliacao>;
  /** Repete o último conjunto de perguntas contra o acervo de agora. */
  rodarAvaliacao(): Promise<void>;
}
