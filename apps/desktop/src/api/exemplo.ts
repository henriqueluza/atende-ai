// Servidor de exemplo, em memória: o acervo de um salão fictício (o mesmo dos arquivos em exemplos/).
// Serve para ver todas as telas sem subir o Docker e para as funções que o servidor ainda não tem.
// Nada aqui é digitado duas vezes: contagens e totais saem sempre das linhas abaixo.

import { ehTexto, formatoDe } from './formatos';
import {
  ErroDoServidor,
  type Avaliacao,
  type DetalheDoDocumento,
  type Documento,
  type ModoDeBusca,
  type PassoDoProcessamento,
  type ResultadoDeBusca,
  type Servidor,
  type Visibilidade,
} from './tipos';

interface Registro {
  documento: Documento;
  trechos: { texto: string; pagina?: number }[];
}

const SCORE_MINIMO = 0.2; // mesmo corte do agente (services/agent/agent/atendente.py)
export const SEM_RESPOSTA = 'Não encontrei essa informação no acervo.';

function registro(
  numero: number,
  dados: Omit<Documento, 'id' | 'trechos' | 'formato'>,
  trechos: Registro['trechos'],
): Registro {
  const id = `00000000-0000-4000-8000-${String(numero).padStart(12, '0')}`;
  return {
    documento: {
      ...dados,
      id,
      formato: formatoDe(dados.nome) ?? 'texto',
      trechos: dados.situacao === 'indexado' ? trechos.length : null,
    },
    trechos,
  };
}

function acervoInicial(): Registro[] {
  return [
    registro(1, { nome: 'faq-salao.md', visibilidade: 'publico', situacao: 'indexado', criadoEm: '2026-11-12T14:05:00-03:00' }, [
      { texto: 'Horário de funcionamento\nAbrimos de terça a sábado, das 9h às 19h. Fechamos aos domingos, segundas e feriados.' },
      { texto: 'Endereço e estacionamento\nEstamos na Rua das Acácias, 120, no Centro. Há estacionamento gratuito para clientes nos fundos.' },
      { texto: 'Agendamento\nAtendemos com hora marcada. O agendamento é feito pelo WhatsApp ou no balcão. Encaixes dependem da agenda do dia.' },
      { texto: 'Formas de pagamento\nAceitamos Pix, dinheiro e cartão de débito ou crédito. Parcelamos em até 3 vezes sem juros para valores acima de R$ 150.' },
      { texto: 'Cancelamento e atraso\nCancelamentos devem ser avisados com 4 horas de antecedência. A tolerância para atraso é de 15 minutos.' },
      { texto: 'Preços\nCorte feminino: R$ 80. Corte masculino: R$ 45. Escova: R$ 50. Coloração: a partir de R$ 160.' },
    ]),
    registro(2, { nome: 'tabela-de-precos-2026.pdf', visibilidade: 'publico', situacao: 'indexado', criadoEm: '2026-11-14T09:40:00-03:00', paginas: 2 }, [
      { pagina: 1, texto: 'Cabelo\nCorte feminino R$ 80. Corte masculino R$ 45. Corte infantil (até 10 anos) R$ 35. Escova R$ 50. Hidratação R$ 70.' },
      { pagina: 1, texto: 'Coloração e química\nColoração a partir de R$ 160. Mechas a partir de R$ 280. Progressiva a partir de R$ 220. O valor final depende do comprimento.' },
      { pagina: 2, texto: 'Unhas\nManicure R$ 35. Pedicure R$ 40. Manicure e pedicure juntas R$ 68. Esmaltação em gel R$ 90.' },
      { pagina: 2, texto: 'Pacotes\nDia da noiva (cabelo, maquiagem e unhas) R$ 520, com teste incluso. Pacote de 4 escovas no mês R$ 170.' },
    ]),
    registro(3, { nome: 'politica-de-cancelamento.md', visibilidade: 'publico', situacao: 'indexado', criadoEm: '2026-11-14T09:52:00-03:00' }, [
      { texto: 'Remarcação\nVocê pode remarcar sem custo até 4 horas antes do horário. Depois disso, a remarcação depende de vaga na agenda.' },
      { texto: 'Falta sem aviso\nDepois de duas faltas sem aviso, novos agendamentos passam a exigir um sinal de 30% por Pix.' },
      { texto: 'Devolução do sinal\nO sinal é devolvido integralmente quando o cancelamento é avisado com 4 horas de antecedência.' },
    ]),
    registro(4, { nome: 'quadro-de-servicos.jpg', visibilidade: 'publico', situacao: 'indexado', criadoEm: '2026-11-17T16:21:00-03:00', ocr: true, paginas: 1 }, [
      { pagina: 1, texto: 'Sobrancelha\nDesign de sobrancelha R$ 40. Design com henna R$ 55. Buço R$ 20.' },
      { pagina: 1, texto: 'Maquiagem\nMaquiagem social R$ 130. Maquiagem para noivas R$ 260, com teste agendado à parte.' },
    ]),
    registro(5, { nome: 'custos-internos.md', visibilidade: 'interno', situacao: 'indexado', criadoEm: '2026-11-12T14:11:00-03:00' }, [
      { texto: 'Margem por serviço\nCorte feminino: custo de R$ 22 e margem de 72%. Coloração: custo de R$ 95 e margem de 41%.' },
      { texto: 'Comissão da equipe\nCabeleireiros recebem 40% de comissão sobre o valor do serviço.' },
    ]),
    registro(6, { nome: 'escala-da-equipe-novembro.pdf', visibilidade: 'interno', situacao: 'extraindo', criadoEm: '2026-11-22T08:47:00-03:00', ocr: true, paginas: 3, andamento: 'Lendo a página 2 de 3' }, []),
    registro(7, { nome: 'contrato-fornecedor-tintas.pdf', visibilidade: 'interno', situacao: 'falhou', criadoEm: '2026-11-21T18:02:00-03:00', erro: 'O PDF está protegido por senha. Envie uma cópia sem senha.' }, []),
    registro(8, { nome: 'promocoes-de-dezembro.txt', visibilidade: 'publico', situacao: 'na_fila', criadoEm: '2026-11-22T08:49:00-03:00' }, []),
  ];
}

const PARADAS = new Set('a o e de da do das dos em no na nos nas um uma para por com que qual quais como é ser são tem têm vocês voces os as ao à se'.split(' '));

// Um embedding de verdade aproxima "abrem" de "funcionamento". O exemplo imita isso com uma
// lista curta de sinônimos e cortando as palavras no radical.
const SINONIMOS: Record<string, string> = {
  abrem: 'funcionamento',
  abre: 'funcionamento',
  aberto: 'funcionamento',
  fecham: 'funcionamento',
  custa: 'preco',
  custam: 'preco',
  valor: 'preco',
  marcar: 'agendamento',
  agendar: 'agendamento',
  desmarcar: 'cancelamento',
  cancelar: 'cancelamento',
  fica: 'endereco',
};

function normalizar(texto: string): string[] {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .split(/[^a-z0-9$]+/)
    .filter((palavra) => palavra.length > 1 && !PARADAS.has(palavra));
}

/** As palavras que contam de um texto, sem acento, já reduzidas ao radical. */
export function palavras(texto: string): string[] {
  return normalizar(texto).map((palavra) => (/^\d/.test(palavra) ? palavra : palavra.slice(0, 4)));
}

/** A pergunta ganha os sinônimos; os trechos ficam como estão. */
function termosDaPergunta(pergunta: string): string[] {
  const normais = normalizar(pergunta);
  const extras = normais.flatMap((palavra) => (SINONIMOS[palavra] ? [SINONIMOS[palavra]] : []));
  return palavras([...normais, ...extras].join(' '));
}

/** Semelhança por palavras em comum (cosseno sobre conjuntos): o que o embedder falso faz. */
function semelhanca(pergunta: string[], trecho: string[]): number {
  const a = new Set(pergunta);
  const b = new Set(trecho);
  if (!a.size || !b.size) return 0;
  let comuns = 0;
  for (const palavra of a) if (b.has(palavra)) comuns += 1;
  return comuns / Math.sqrt(a.size * b.size);
}

/** Na busca por palavras-chave só conta quanto da pergunta aparece no trecho. */
function cobertura(pergunta: string[], trecho: string[]): number {
  const b = new Set(trecho);
  const unicas = [...new Set(pergunta)];
  return unicas.length ? unicas.filter((palavra) => b.has(palavra)).length / unicas.length : 0;
}

function pontuar(modo: ModoDeBusca, pergunta: string[], trecho: string[]): number {
  if (modo === 'semantica') return semelhanca(pergunta, trecho);
  if (modo === 'palavras') return cobertura(pergunta, trecho);
  return (semelhanca(pergunta, trecho) + cobertura(pergunta, trecho)) / 2;
}

function passosDe(d: Documento): PassoDoProcessamento[] {
  const leitura = d.formato === 'imagem' || d.ocr ? 'Leitura do texto (OCR)' : 'Extração do texto';
  const nomes = ['Arquivo recebido', leitura, 'Divisão em trechos', 'Indexação para a busca'];
  const ateOnde = { na_fila: 1, extraindo: 1, indexando: 3, indexado: 4, falhou: 1 }[d.situacao];
  return nomes.map((nome, indice) => {
    if (indice < ateOnde) {
      const detalhe = indice === 2 && d.trechos !== null ? `${d.trechos} trechos` : undefined;
      return { nome, estado: 'feito', detalhe, quando: indice === 0 ? (d.criadoEm ?? undefined) : undefined };
    }
    if (indice === ateOnde && d.situacao === 'falhou') return { nome, estado: 'falhou', detalhe: d.erro };
    if (indice === ateOnde && d.situacao !== 'na_fila') return { nome, estado: 'em_andamento', detalhe: d.andamento };
    return { nome, estado: 'pendente', detalhe: indice === ateOnde ? 'Aguardando a vez na fila' : undefined };
  });
}

const AVALIACAO: Avaliacao = (() => {
  const k = 3;
  const perguntas = [
    ['Que horas vocês abrem?', 'faq-salao.md', 1],
    ['Vocês abrem no domingo?', 'faq-salao.md', 1],
    ['Onde fica o salão?', 'faq-salao.md', 1],
    ['Tem estacionamento?', 'faq-salao.md', 1],
    ['Como faço para marcar um horário?', 'faq-salao.md', 2],
    ['Posso pagar com Pix?', 'faq-salao.md', 1],
    ['Dá para parcelar a coloração?', 'faq-salao.md', 4, 'tabela-de-precos-2026.pdf'],
    ['Quanto custa o corte feminino?', 'tabela-de-precos-2026.pdf', 1],
    ['Qual o preço do corte para criança?', 'tabela-de-precos-2026.pdf', 1],
    ['Quanto fica mão e pé juntos?', 'tabela-de-precos-2026.pdf', 5, 'faq-salao.md'],
    ['Vocês fazem progressiva?', 'tabela-de-precos-2026.pdf', 1],
    ['Tem pacote para noiva?', 'tabela-de-precos-2026.pdf', 2],
    ['Quanto custa a esmaltação em gel?', 'tabela-de-precos-2026.pdf', 1],
    ['Até quando posso desmarcar?', 'politica-de-cancelamento.md', 1],
    ['Me atrasei 10 minutos, perco o horário?', 'faq-salao.md', null, 'politica-de-cancelamento.md'],
    ['Preciso pagar sinal para agendar?', 'politica-de-cancelamento.md', 1],
    ['Devolvem o sinal se eu cancelar?', 'politica-de-cancelamento.md', 1],
    ['O que acontece se eu faltar?', 'politica-de-cancelamento.md', 2],
    ['Fazem sobrancelha com henna?', 'quadro-de-servicos.jpg', 1],
    ['Quanto é para tirar o buço?', 'quadro-de-servicos.jpg', 6, 'tabela-de-precos-2026.pdf'],
    ['Quanto custa maquiagem para festa?', 'quadro-de-servicos.jpg', 4, 'tabela-de-precos-2026.pdf'],
    ['A maquiagem de noiva tem teste?', 'quadro-de-servicos.jpg', 2],
    ['Aceitam cartão de crédito?', 'faq-salao.md', 1],
    ['Atendem sem hora marcada?', 'faq-salao.md', 1],
  ] as const;
  const avaliadas = perguntas.map(([pergunta, esperado, posicao, primeiro]) => ({
    pergunta,
    esperado,
    posicao,
    primeiro: primeiro ?? esperado,
  }));
  const acertos = avaliadas.filter((p) => p.posicao !== null && p.posicao <= k).length;
  const mrr = avaliadas.reduce((soma, p) => soma + (p.posicao ? 1 / p.posicao : 0), 0) / avaliadas.length;
  const total = avaliadas.length;
  return {
    k,
    perguntas: avaliadas,
    execucoes: [
      { data: '2026-11-18T10:00:00-03:00', versao: '8d87d75', perguntas: total, acertos: 12, mrr: 0.41, nota: 'Etapa 1' },
      { data: '2026-11-19T10:00:00-03:00', versao: 'a41c0e2', perguntas: total, acertos: 12, mrr: 0.41 },
      { data: '2026-11-19T10:00:00-03:00', versao: 'c7f1b93', perguntas: total, acertos: 13, mrr: 0.44 },
      { data: '2026-11-20T10:00:00-03:00', versao: '2be6a10', perguntas: total, acertos: 16, mrr: 0.58, nota: 'Modelo de embedding real' },
      { data: '2026-11-20T10:00:00-03:00', versao: '5d0e7fa', perguntas: total, acertos: 16, mrr: 0.6 },
      { data: '2026-11-21T10:00:00-03:00', versao: '91ac3d4', perguntas: total, acertos: 15, mrr: 0.57 },
      { data: '2026-11-21T10:00:00-03:00', versao: 'e3b8c55', perguntas: total, acertos: 18, mrr: 0.69, nota: 'Busca híbrida' },
      { data: '2026-11-22T10:00:00-03:00', versao: 'f02d9a7', perguntas: total, acertos, mrr: Math.round(mrr * 100) / 100 },
    ],
  };
})();

export function criarServidorDeExemplo(espera = 380): Servidor {
  let acervo = acervoInicial();
  let proximo = acervo.length + 1;
  let avaliacao = AVALIACAO;
  const pausa = () => new Promise((resolver) => setTimeout(resolver, espera));
  const achar = (id: string) => {
    const encontrado = acervo.find((r) => r.documento.id === id);
    if (!encontrado) throw new ErroDoServidor('recusado', 'Documento não encontrado.');
    return encontrado;
  };

  function buscarNoAcervo(pergunta: string, k: number, visibilidade: Visibilidade, modo: ModoDeBusca) {
    const termos = termosDaPergunta(pergunta);
    const resultados: ResultadoDeBusca[] = acervo
      .filter((r) => r.documento.situacao === 'indexado' && r.documento.visibilidade === visibilidade)
      .flatMap((r) =>
        r.trechos.map((t) => ({
          trecho: t.texto,
          documento: r.documento.nome,
          score: pontuar(modo, termos, palavras(t.texto)),
        })),
      );
    return resultados
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, k);
  }

  return {
    async saude() {
      await pausa();
      return { coreApi: 'no_ar', mcp: 'no_ar', agente: 'no_ar' };
    },

    async listarDocumentos() {
      await pausa();
      return acervo.map((r) => ({ ...r.documento }));
    },

    async enviarDocumento(novo) {
      await pausa();
      const formato = formatoDe(novo.nome);
      if (!formato) throw new ErroDoServidor('recusado', 'Formato de arquivo não aceito.');
      const texto = ehTexto(formato) ? (novo.conteudo ?? '') : '';
      if (ehTexto(formato) && !texto.trim()) {
        throw new ErroDoServidor('recusado', 'O documento não tem texto para indexar.');
      }
      // Um trecho por título, como o chunking do core-api (ADR 0002).
      const trechos = texto
        .split(/\n(?=#{1,6} )/)
        .map((parte) => parte.replace(/^#{1,6} /, '').trim())
        .filter(Boolean)
        .map((parte) => ({ texto: parte }));
      const novoRegistro = registro(
        proximo++,
        {
          nome: novo.nome,
          visibilidade: novo.visibilidade,
          // Texto indexa na hora. PDF e imagem entram na fila de extração.
          situacao: ehTexto(formato) ? 'indexado' : 'na_fila',
          criadoEm: new Date().toISOString(),
        },
        trechos,
      );
      // O nome é a identidade: reenviar substitui o anterior (regra atual do core-api).
      acervo = [novoRegistro, ...acervo.filter((r) => r.documento.nome !== novo.nome)];
    },

    async excluirDocumento(id) {
      await pausa();
      achar(id);
      acervo = acervo.filter((r) => r.documento.id !== id);
    },

    async alterarVisibilidade(id, visibilidade) {
      await pausa();
      achar(id).documento.visibilidade = visibilidade;
    },

    async detalharDocumento(id): Promise<DetalheDoDocumento> {
      await pausa();
      const { documento, trechos } = achar(id);
      return {
        documento: { ...documento },
        trechos: trechos.map((t, posicao) => ({ posicao, ...t })),
        passos: passosDe(documento),
      };
    },

    async buscar({ pergunta, k, visibilidade, modo }) {
      await pausa();
      return buscarNoAcervo(pergunta, k, visibilidade, modo);
    },

    async perguntarAoAtendente(pergunta) {
      await pausa();
      // O atendente só enxerga conteúdo público, sempre.
      const fontes = buscarNoAcervo(pergunta, 3, 'publico', 'hibrida').filter((f) => f.score >= SCORE_MINIMO);
      if (!fontes.length) return { texto: SEM_RESPOSTA, fontes: [], respondeu: false };
      const corpo = fontes[0].trecho.split('\n').slice(1).join(' ') || fontes[0].trecho;
      return { texto: corpo, fontes, respondeu: true };
    },

    async avaliacao() {
      await pausa();
      return avaliacao;
    },

    async rodarAvaliacao() {
      await pausa();
      const ultima = avaliacao.execucoes.at(-1)!;
      const nova = { ...ultima, data: new Date().toISOString(), versao: 'exemplo', nota: null };
      avaliacao = { ...avaliacao, execucoes: [...avaliacao.execucoes, nova] };
    },
  };
}
