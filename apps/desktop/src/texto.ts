// Formatação de números, datas e plurais em português do Brasil.

const numero = new Intl.NumberFormat('pt-BR');
const duasCasas = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const umaCasa = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const hora = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' });
const diaMes = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short' });
const diaMesAno = new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short', year: 'numeric' });

export const inteiro = (valor: number) => numero.format(valor);
export const score = (valor: number) => duasCasas.format(valor);
export const porcento = (fracao: number) => `${umaCasa.format(fracao * 100)}%`;
export const pontos = (fracao: number) => umaCasa.format(Math.abs(fracao) * 100);

export function plural(quantidade: number, um: string, varios: string): string {
  return `${inteiro(quantidade)} ${quantidade === 1 ? um : varios}`;
}

const mesmoDia = (a: Date, b: Date) => a.toDateString() === b.toDateString();

/** "Hoje, 08:47", "Ontem, 18:02", "14 de nov." */
export function quando(iso: string | null, agora = new Date()): string {
  if (!iso) return '–';
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return '–';
  if (mesmoDia(data, agora)) return `Hoje, ${hora.format(data)}`;
  const ontem = new Date(agora);
  ontem.setDate(agora.getDate() - 1);
  if (mesmoDia(data, ontem)) return `Ontem, ${hora.format(data)}`;
  return data.getFullYear() === agora.getFullYear() ? diaMes.format(data) : diaMesAno.format(data);
}

export const dataCurta = (iso: string) => {
  const data = new Date(iso);
  return Number.isNaN(data.getTime()) ? '–' : diaMes.format(data);
};

export function tamanho(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${umaCasa.format(bytes / 1024 / 1024)} MB`;
}

/** Divide o trecho em título (primeira linha) e corpo, como o chunking por título produz. */
export function partesDoTrecho(texto: string): { titulo: string | null; corpo: string } {
  const [primeira, ...resto] = texto.split('\n');
  if (!resto.length || primeira.length > 80) return { titulo: null, corpo: texto };
  return { titulo: primeira.replace(/^#+\s*/, ''), corpo: resto.join('\n').trim() };
}
