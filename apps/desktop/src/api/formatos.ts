import type { Formato } from './tipos';

const POR_EXTENSAO: Record<string, Formato> = {
  md: 'markdown',
  markdown: 'markdown',
  txt: 'texto',
  pdf: 'pdf',
  png: 'imagem',
  jpg: 'imagem',
  jpeg: 'imagem',
  webp: 'imagem',
};

export const EXTENSOES_ACEITAS = Object.keys(POR_EXTENSAO).map((extensao) => `.${extensao}`);
export const TAMANHO_MAXIMO_TEXTO = 1_000_000; // mesmo limite do core-api
export const TAMANHO_MAXIMO_ARQUIVO = 20 * 1024 * 1024;

export function formatoDe(nome: string): Formato | null {
  const extensao = nome.includes('.') ? nome.split('.').pop()!.toLowerCase() : '';
  return POR_EXTENSAO[extensao] ?? null;
}

export const ehTexto = (formato: Formato) => formato === 'markdown' || formato === 'texto';

export const NOME_DO_FORMATO: Record<Formato, string> = {
  markdown: 'Markdown',
  texto: 'Texto',
  pdf: 'PDF',
  imagem: 'Imagem',
};
