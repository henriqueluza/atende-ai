import { ChartLine, FileText, Menu as IconeMenu, MessageCircle, Search, Settings } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { lembrarOrigem, origemInicial, servidorPara, temPonte, type Origem, type Saude } from './api';
import { Marca } from './components/Comuns';
import { ContextoDoApp, irPara, useRota, type Rota } from './contexto';
import { Atendente } from './screens/Atendente';
import { Configuracoes } from './screens/Configuracoes';
import { Documento } from './screens/Documento';
import { Documentos } from './screens/Documentos';
import { EnviarDocumentos } from './screens/EnviarDocumentos';
import { Pesquisa } from './screens/Pesquisa';
import { Qualidade } from './screens/Qualidade';

const NAVEGACAO = [
  { tela: 'documentos', rotulo: 'Documentos', icone: FileText },
  { tela: 'pesquisa', rotulo: 'Pesquisa', icone: Search },
  { tela: 'atendente', rotulo: 'Testar atendente', icone: MessageCircle },
  { tela: 'qualidade', rotulo: 'Qualidade da busca', icone: ChartLine },
] as const;

const NOME_DO_SERVICO = { no_ar: 'no ar', fora_do_ar: 'fora do ar', verificando: 'verificando' } as const;

function Tela({ rota }: { rota: Rota }) {
  switch (rota.tela) {
    case 'documento':
      return <Documento id={rota.id!} />;
    case 'pesquisa':
      return <Pesquisa perguntaInicial={rota.parametros.get('q') ?? ''} ondeInicial={rota.parametros.get('onde')} />;
    case 'atendente':
      return <Atendente perguntaInicial={rota.parametros.get('q') ?? ''} />;
    case 'qualidade':
      return <Qualidade />;
    case 'configuracoes':
      return <Configuracoes />;
    default:
      return <Documentos />;
  }
}

export function App() {
  const rota = useRota();
  const [origem, definirOrigem] = useState<Origem>(origemInicial);
  const [revisao, definirRevisao] = useState(0);
  const [saude, definirSaude] = useState<Saude | null>(null);
  const [envio, definirEnvio] = useState<File[] | null>(null);
  const [avisos, definirAvisos] = useState<{ id: number; texto: string }[]>([]);
  const [menuAberto, abrirMenu] = useState(false);
  const busca = useRef<HTMLInputElement>(null);
  const servidor = useMemo(() => servidorPara(origem), [origem]);

  const avisar = useCallback((texto: string) => {
    const id = Date.now() + Math.random();
    definirAvisos((antes) => [...antes, { id, texto }]);
    setTimeout(() => definirAvisos((antes) => antes.filter((aviso) => aviso.id !== id)), 4000);
  }, []);

  const app = useMemo(
    () => ({
      servidor,
      origem,
      podeUsarServidor: temPonte(),
      trocarOrigem(nova: Origem) {
        lembrarOrigem(nova);
        definirOrigem(nova);
      },
      avisar,
      pedirEnvio: (arquivos: File[] = []) => definirEnvio(arquivos),
      revisao,
      acervoMudou: () => definirRevisao((antes) => antes + 1),
    }),
    [servidor, origem, avisar, revisao],
  );

  // Situação dos serviços: confere ao abrir e a cada 20 segundos.
  useEffect(() => {
    let ativo = true;
    const conferir = () =>
      servidor.saude().then(
        (nova) => ativo && definirSaude(nova),
        () => ativo && definirSaude({ coreApi: 'fora_do_ar', mcp: 'fora_do_ar', agente: 'fora_do_ar' }),
      );
    definirSaude(null);
    conferir();
    const relogio = setInterval(conferir, 20_000);
    return () => {
      ativo = false;
      clearInterval(relogio);
    };
  }, [servidor]);

  // Soltar arquivos em qualquer lugar da janela abre o envio. Atalho: Ctrl/Cmd+K vai para a busca.
  useEffect(() => {
    const temArquivo = (evento: DragEvent) => evento.dataTransfer?.types.includes('Files') ?? false;
    const sobre = (evento: DragEvent) => temArquivo(evento) && evento.preventDefault();
    const soltar = (evento: DragEvent) => {
      if (!temArquivo(evento)) return;
      evento.preventDefault();
      const arquivos = [...(evento.dataTransfer?.files ?? [])];
      if (arquivos.length) definirEnvio((antes) => [...(antes ?? []), ...arquivos]);
    };
    const tecla = (evento: KeyboardEvent) => {
      if ((evento.metaKey || evento.ctrlKey) && evento.key.toLowerCase() === 'k') {
        evento.preventDefault();
        busca.current?.focus();
      }
    };
    window.addEventListener('dragover', sobre);
    window.addEventListener('drop', soltar);
    window.addEventListener('keydown', tecla);
    return () => {
      window.removeEventListener('dragover', sobre);
      window.removeEventListener('drop', soltar);
      window.removeEventListener('keydown', tecla);
    };
  }, []);

  useEffect(() => abrirMenu(false), [rota]);

  const telaAtiva = rota.tela === 'documento' ? 'documentos' : rota.tela;
  const plataforma = window.atende?.plataforma ?? 'web';
  const mac = plataforma === 'darwin' || /Mac/.test(navigator.userAgent);

  return (
    <ContextoDoApp.Provider value={app}>
      <div className="app" data-plataforma={plataforma}>
        <nav className="lateral" aria-label="Principal" data-aberta={menuAberto}>
          <div className="marca">
            <Marca />
            atende-ai
          </div>
          <p className="escopo">{origem === 'exemplo' ? 'Salão Bela Vista (exemplo)' : 'Acervo do negócio'}</p>
          {NAVEGACAO.map(({ tela, rotulo, icone: Icone }) => (
            <a
              key={tela}
              className="nav-item"
              href={`#/${tela}`}
              aria-current={telaAtiva === tela ? 'page' : undefined}
            >
              <Icone aria-hidden="true" />
              {rotulo}
            </a>
          ))}
          <div className="fundo">
            <ul className="servicos" aria-label="Situação dos serviços">
              {(
                [
                  ['Núcleo de conhecimento', saude?.coreApi],
                  ['Ponte do atendente (MCP)', saude?.mcp],
                  ['Atendente', saude?.agente],
                ] as const
              ).map(([nome, estado]) => (
                <li key={nome} className="servico">
                  <span className="ponto" data-estado={estado ?? 'verificando'} aria-hidden="true" />
                  {nome}
                  <span className="so-leitor">: {NOME_DO_SERVICO[estado ?? 'verificando']}</span>
                </li>
              ))}
            </ul>
            <a
              className="nav-item"
              href="#/configuracoes"
              aria-current={telaAtiva === 'configuracoes' ? 'page' : undefined}
            >
              <Settings aria-hidden="true" />
              Configurações
            </a>
          </div>
        </nav>

        <header className="barra">
          <button className="btn fantasma so-icone menu" aria-label="Abrir menu" onClick={() => abrirMenu(true)}>
            <IconeMenu aria-hidden="true" />
          </button>
          <form
            className="barra-busca"
            role="search"
            onSubmit={(evento) => {
              evento.preventDefault();
              const pergunta = busca.current?.value.trim();
              if (pergunta) irPara(`/pesquisa?q=${encodeURIComponent(pergunta)}`);
            }}
          >
            <Search aria-hidden="true" />
            <input
              ref={busca}
              type="search"
              name="q"
              maxLength={500}
              aria-label="Pesquisar no acervo"
              placeholder="Pesquisar no acervo"
              autoComplete="off"
            />
            <kbd aria-hidden="true">{mac ? '⌘K' : 'Ctrl K'}</kbd>
          </form>
          <div className="barra-direita">
            {origem === 'exemplo' && (
              <span className="pilula aviso" title="Nada aqui vem do seu servidor nem é salvo.">
                Dados de exemplo
              </span>
            )}
          </div>
        </header>

        <main className="folha">
          <div className="rolagem">
            <div className="tela" key={`${rota.tela}:${rota.id ?? ''}:${origem}`}>
              <Tela rota={rota} />
            </div>
          </div>
        </main>
      </div>

      {envio && <EnviarDocumentos iniciais={envio} aoFechar={() => definirEnvio(null)} />}
      <div className="avisos" role="status" aria-live="polite">
        {avisos.map((aviso) => (
          <div key={aviso.id} className="aviso">
            {aviso.texto}
          </div>
        ))}
      </div>
    </ContextoDoApp.Provider>
  );
}
