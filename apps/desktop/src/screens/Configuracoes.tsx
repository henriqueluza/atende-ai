import { useEffect, useState } from 'react';

import { lerEnderecos, salvarEnderecos, type Enderecos, type Saude } from '../api';
import { mensagemDe, useApp } from '../contexto';

export function Configuracoes() {
  const { origem, trocarOrigem, podeUsarServidor, servidor, avisar } = useApp();
  const [enderecos, definirEnderecos] = useState<Enderecos | null>(null);
  const [salvos, definirSalvos] = useState<Enderecos | null>(null);
  const [falha, definirFalha] = useState<string | null>(null);
  const [teste, definirTeste] = useState<Saude | 'testando' | null>(null);
  const [salvando, definirSalvando] = useState(false);

  useEffect(() => {
    lerEnderecos().then(
      (lidos) => { definirEnderecos(lidos); definirSalvos(lidos); },
      (erro) => definirFalha(mensagemDe(erro)),
    );
  }, []);

  const mudou =
    enderecos &&
    salvos &&
    (enderecos.coreApi !== salvos.coreApi || enderecos.mcp !== salvos.mcp || enderecos.agente !== salvos.agente);

  async function salvar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!enderecos) return;
    definirSalvando(true);
    definirFalha(null);
    try {
      const novos = await salvarEnderecos(enderecos);
      definirEnderecos(novos);
      definirSalvos(novos);
      definirTeste(null);
      avisar('Endereços salvos.');
    } catch (erro) {
      definirFalha(mensagemDe(erro));
    }
    definirSalvando(false);
  }

  async function testar() {
    definirTeste('testando');
    try {
      definirTeste(await servidor.saude());
    } catch {
      definirTeste({ coreApi: 'fora_do_ar', mcp: 'fora_do_ar', agente: 'fora_do_ar' });
    }
  }

  const resultado = (estado: Saude['coreApi']) =>
    estado === 'no_ar' ? <span className="pilula pos">No ar</span> : <span className="pilula neg">Sem resposta</span>;

  return (
    <>
      <div className="titulo">
        <div>
          <h1>Configurações</h1>
        </div>
      </div>

      <section className="ajuste" aria-labelledby="ajuste-servidor">
        <div>
          <h2 id="ajuste-servidor">Servidor</h2>
          <p className="descricao">
            Onde estão os serviços do atende-ai. Rodando com Docker nesta máquina, os endereços padrão já
            funcionam. Sem https, só é aceito um servidor neste computador: os serviços ainda não pedem senha.
          </p>
        </div>
        <form className="ajuste-painel" onSubmit={salvar}>
          <div className="campo">
            <label htmlFor="core-api">Núcleo de conhecimento (core-api)</label>
            <input
              id="core-api"
              className="entrada"
              inputMode="url"
              spellCheck={false}
              value={enderecos?.coreApi ?? ''}
              disabled={!podeUsarServidor || !enderecos}
              onChange={(evento) => enderecos && definirEnderecos({ ...enderecos, coreApi: evento.target.value })}
            />
          </div>
          <div className="campo">
            <label htmlFor="mcp">Ponte do atendente (servidor MCP)</label>
            <input
              id="mcp"
              className="entrada"
              inputMode="url"
              spellCheck={false}
              value={enderecos?.mcp ?? ''}
              disabled={!podeUsarServidor || !enderecos}
              onChange={(evento) => enderecos && definirEnderecos({ ...enderecos, mcp: evento.target.value })}
            />
          </div>
          <div className="campo">
            <label htmlFor="agente">Atendente</label>
            <input
              id="agente"
              className="entrada"
              inputMode="url"
              spellCheck={false}
              value={enderecos?.agente ?? ''}
              disabled={!podeUsarServidor || !enderecos}
              onChange={(evento) => enderecos && definirEnderecos({ ...enderecos, agente: evento.target.value })}
            />
            {!podeUsarServidor && (
              <span className="dica">Os endereços só podem ser alterados no aplicativo de desktop.</span>
            )}
            {falha && <span className="falha" role="alert">{falha}</span>}
          </div>
          {teste && teste !== 'testando' && (
            <div className="previstas" role="status">
              <div><span>Núcleo de conhecimento</span>{resultado(teste.coreApi)}</div>
              <div><span>Ponte do atendente</span>{resultado(teste.mcp)}</div>
              <div><span>Atendente</span>{resultado(teste.agente)}</div>
            </div>
          )}
          <div className="rodape">
            <button className="btn" type="button" onClick={testar} disabled={teste === 'testando' || Boolean(mudou)}>
              {teste === 'testando' ? 'Testando…' : 'Testar conexão'}
            </button>
            <button className="btn primario" type="submit" disabled={!mudou || salvando || !podeUsarServidor}>
              {salvando ? 'Salvando…' : 'Salvar endereços'}
            </button>
          </div>
        </form>
      </section>

      <section className="ajuste" aria-labelledby="ajuste-exemplo">
        <div>
          <h2 id="ajuste-exemplo">Dados de exemplo</h2>
          <p className="descricao">
            Um acervo fictício de salão, guardado só na memória do aplicativo. Serve para conhecer as telas
            sem mexer no acervo de verdade.
          </p>
        </div>
        <div className="ajuste-painel">
          <div className="linha-chave">
            <div>
              <label className="rotulo" htmlFor="usar-exemplo">Usar dados de exemplo</label>
              <p className="dica">
                {podeUsarServidor
                  ? 'Ligado, nada é lido nem gravado no servidor. O que você enviar some ao fechar o aplicativo.'
                  : 'Fora do aplicativo de desktop só existem os dados de exemplo.'}
              </p>
            </div>
            <input
              id="usar-exemplo"
              className="chave"
              type="checkbox"
              role="switch"
              checked={origem === 'exemplo'}
              disabled={!podeUsarServidor}
              onChange={(evento) => trocarOrigem(evento.target.checked ? 'exemplo' : 'servidor')}
            />
          </div>
        </div>
      </section>

    </>
  );
}
