import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

import { ErroDoServidor, type Origem, type Servidor } from './api';

export interface Rota {
  tela: 'documentos' | 'documento' | 'pesquisa' | 'atendente' | 'qualidade' | 'configuracoes';
  id?: string;
  parametros: URLSearchParams;
}

const TELAS = new Set(['documentos', 'pesquisa', 'atendente', 'qualidade', 'configuracoes']);

export function lerRota(hash: string): Rota {
  const [caminho, consulta = ''] = hash.replace(/^#\/?/, '').split('?');
  const [tela, id] = caminho.split('/');
  const parametros = new URLSearchParams(consulta);
  if (tela === 'documentos' && id) return { tela: 'documento', id: decodeURIComponent(id), parametros };
  if (TELAS.has(tela)) return { tela: tela as Rota['tela'], parametros };
  return { tela: 'documentos', parametros };
}

export function useRota(): Rota {
  const [rota, definir] = useState(() => lerRota(window.location.hash));
  useEffect(() => {
    const aoMudar = () => definir(lerRota(window.location.hash));
    window.addEventListener('hashchange', aoMudar);
    return () => window.removeEventListener('hashchange', aoMudar);
  }, []);
  return rota;
}

export const irPara = (caminho: string) => {
  window.location.hash = caminho;
};

interface App {
  servidor: Servidor;
  origem: Origem;
  podeUsarServidor: boolean;
  trocarOrigem(origem: Origem): void;
  avisar(mensagem: string): void;
  pedirEnvio(arquivos?: File[]): void;
  /** Muda a cada alteração no acervo, para as listas recarregarem. */
  revisao: number;
  acervoMudou(): void;
}

export const ContextoDoApp = createContext<App | null>(null);

export function useApp(): App {
  const app = useContext(ContextoDoApp);
  if (!app) throw new Error('useApp fora do provedor');
  return app;
}

export type Consulta<T> =
  | { estado: 'carregando'; dados: T | null; erro: null }
  | { estado: 'pronto'; dados: T; erro: null }
  | { estado: 'erro'; dados: T | null; erro: ErroDoServidor };

/** Busca dados e guarda o estado. Ao recarregar, mantém na tela o que já havia. */
export function useConsulta<T>(buscar: () => Promise<T>, dependencias: unknown[]) {
  const [consulta, definir] = useState<Consulta<T>>({ estado: 'carregando', dados: null, erro: null });
  const [quandoCarregou, definirQuando] = useState<Date | null>(null);
  const rodada = useRef(0);

  const recarregar = useCallback(() => {
    const esta = ++rodada.current;
    definir((antes) => ({ estado: 'carregando', dados: antes.dados, erro: null }));
    buscar().then(
      (dados) => {
        if (esta !== rodada.current) return; // chegou uma resposta velha: ignora
        definir({ estado: 'pronto', dados, erro: null });
        definirQuando(new Date());
      },
      (falha: unknown) => {
        if (esta !== rodada.current) return;
        const erro =
          falha instanceof ErroDoServidor ? falha : new ErroDoServidor('erro', 'Algo deu errado ao carregar.');
        definir((antes) => ({ estado: 'erro', dados: antes.dados, erro }));
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencias);

  useEffect(() => {
    definir({ estado: 'carregando', dados: null, erro: null });
    recarregar();
  }, [recarregar]);

  return { ...consulta, recarregar, quandoCarregou };
}

export function mensagemDe(falha: unknown): string {
  return falha instanceof ErroDoServidor ? falha.message : 'Algo deu errado. Tente de novo.';
}
