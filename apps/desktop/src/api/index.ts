import { criarServidorDeExemplo } from './exemplo';
import { abrir, criarServidorReal, type Ponte } from './real';
import type { Enderecos, Servidor } from './tipos';

declare global {
  interface Window {
    atende?: Ponte;
  }
}

export type Origem = 'servidor' | 'exemplo';

const CHAVE = 'atende.origem';

/** Fora do Electron (no navegador, durante o desenvolvimento) só existem os dados de exemplo. */
export const temPonte = () => typeof window !== 'undefined' && window.atende !== undefined;

export function origemInicial(): Origem {
  if (!temPonte()) return 'exemplo';
  try {
    return localStorage.getItem(CHAVE) === 'exemplo' ? 'exemplo' : 'servidor';
  } catch {
    return 'servidor';
  }
}

export function lembrarOrigem(origem: Origem) {
  try {
    localStorage.setItem(CHAVE, origem);
  } catch {
    // Sem armazenamento local, a escolha vale só até fechar o app.
  }
}

const exemplo = criarServidorDeExemplo();

export function servidorPara(origem: Origem): Servidor {
  return origem === 'servidor' && window.atende ? criarServidorReal(window.atende) : exemplo;
}

export const ENDERECOS_DE_EXEMPLO: Enderecos = {
  coreApi: 'http://localhost:8000',
  mcp: 'http://localhost:8001',
  agente: 'http://localhost:8002',
};

export async function lerEnderecos(): Promise<Enderecos> {
  return window.atende ? abrir(await window.atende.enderecos()) : ENDERECOS_DE_EXEMPLO;
}

export async function salvarEnderecos(novos: Enderecos): Promise<Enderecos> {
  if (!window.atende) return novos;
  return abrir(await window.atende.salvarEnderecos(novos));
}

export * from './tipos';
