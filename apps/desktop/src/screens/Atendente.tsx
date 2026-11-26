import { SendHorizontal } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { ErroDoServidor, type RespostaDoAtendente } from '../api';
import { Marca } from '../components/Comuns';
import { Falha, Vazio } from '../components/Estados';
import { irPara, useApp } from '../contexto';
import { partesDoTrecho, plural, score } from '../texto';

interface Troca {
  id: number;
  pergunta: string;
  resposta: RespostaDoAtendente | null;
  erro: ErroDoServidor | null;
}

const SUGESTOES = ['Que horas vocês abrem?', 'Quanto custa a coloração?', 'Qual a comissão da equipe?'];

export function Atendente({ perguntaInicial = '' }: { perguntaInicial?: string }) {
  const { servidor, pedirEnvio } = useApp();
  const [trocas, definirTrocas] = useState<Troca[]>([]);
  const [texto, definirTexto] = useState('');
  const [escolhida, escolher] = useState<number | null>(null);
  const [documentos, definirDocumentos] = useState<Map<string, string>>(new Map());
  const fim = useRef<HTMLDivElement>(null);
  const campo = useRef<HTMLInputElement>(null);
  const esperando = trocas.some((troca) => !troca.resposta && !troca.erro);

  useEffect(() => {
    servidor.listarDocumentos().then(
      (lista) => definirDocumentos(new Map(lista.map((d) => [d.nome, d.id]))),
      () => undefined,
    );
  }, [servidor]);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: 'end' });
  }, [trocas]);

  // Vindo de outra tela com uma pergunta pronta (#/atendente?q=...), ela já é enviada.
  const jaPerguntou = useRef(false);
  useEffect(() => {
    if (perguntaInicial.trim() && !jaPerguntou.current) {
      jaPerguntou.current = true;
      perguntar(perguntaInicial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [perguntaInicial]);

  async function perguntar(pergunta: string) {
    const limpa = pergunta.trim();
    if (!limpa || esperando) return;
    const id = Date.now();
    definirTexto('');
    definirTrocas((antes) => [...antes, { id, pergunta: limpa, resposta: null, erro: null }]);
    escolher(id);
    const atualizar = (mudanca: Partial<Troca>) =>
      definirTrocas((antes) => antes.map((troca) => (troca.id === id ? { ...troca, ...mudanca } : troca)));
    try {
      atualizar({ resposta: await servidor.perguntarAoAtendente(limpa) });
    } catch (falha) {
      atualizar({ erro: falha instanceof ErroDoServidor ? falha : new ErroDoServidor('erro', 'O atendente falhou.') });
    }
    campo.current?.focus();
  }

  const atual = trocas.find((troca) => troca.id === escolhida) ?? trocas.at(-1) ?? null;
  const respondidas = trocas.filter((troca) => troca.resposta);
  const semResposta = respondidas.filter((troca) => !troca.resposta!.respondeu).length;

  return (
    <>
      <div className="titulo">
        <div>
          <h1>Testar atendente</h1>
          <p className="sub">
            {respondidas.length === 0
              ? 'A resposta que o cliente receberia no WhatsApp, feita só com documentos públicos.'
              : semResposta
                ? `${plural(semResposta, 'pergunta ficou', 'perguntas ficaram')} sem resposta de ${respondidas.length} nesta conversa.`
                : `${plural(respondidas.length, 'pergunta respondida', 'perguntas respondidas')} com base no acervo público.`}
          </p>
        </div>
        {trocas.length > 0 && (
          <div className="acoes">
            <button className="btn" onClick={() => { definirTrocas([]); escolher(null); }} disabled={esperando}>
              Limpar conversa
            </button>
          </div>
        )}
      </div>

      <div className="atendimento">
        <section className="conversa" aria-label="Conversa de teste">
          <div className="conversa-topo">
            <span style={{ color: 'var(--accent)' }}><Marca /></span>
            <div>
              <p className="quem">Atendente</p>
              <p className="sub">Você escreve no lugar do cliente</p>
            </div>
          </div>
          <div className="mensagens" role="log" aria-live="polite">
            {trocas.length === 0 && (
              <Vazio
                acoes={SUGESTOES.map((sugestao) => (
                  <button key={sugestao} className="btn" onClick={() => perguntar(sugestao)}>
                    {sugestao}
                  </button>
                ))}
              >
                <strong>Faça uma pergunta de cliente.</strong> Experimente também algo que só está em documento
                interno: o atendente tem que dizer que não encontrou.
              </Vazio>
            )}
            {trocas.map((troca) => (
              <div key={troca.id} style={{ display: 'contents' }}>
                <p className="balao cliente">
                  <span className="so-leitor">Cliente: </span>
                  {troca.pergunta}
                </p>
                {troca.resposta ? (
                  <button
                    className="balao atendente"
                    aria-pressed={atual?.id === troca.id}
                    onClick={() => escolher(troca.id)}
                  >
                    <span className="so-leitor">Atendente: </span>
                    {troca.resposta.texto}
                    <span className="rodape">
                      {troca.resposta.respondeu
                        ? plural(troca.resposta.fontes.length, 'fonte', 'fontes')
                        : 'Sem fonte no acervo público'}
                    </span>
                  </button>
                ) : troca.erro ? (
                  <p className="balao atendente">
                    <span className="rodape">A resposta não chegou.</span>
                  </p>
                ) : (
                  <p className="balao atendente digitando">Procurando no acervo…</p>
                )}
              </div>
            ))}
            <div ref={fim} />
          </div>
          <form
            className="compor"
            onSubmit={(evento) => {
              evento.preventDefault();
              perguntar(texto);
            }}
          >
            <input
              ref={campo}
              className="entrada"
              value={texto}
              maxLength={500}
              onChange={(evento) => definirTexto(evento.target.value)}
              placeholder="Escreva como o cliente"
              aria-label="Mensagem do cliente"
              autoComplete="off"
            />
            <button className="btn primario grande so-icone" style={{ width: 40 }} type="submit" disabled={!texto.trim() || esperando} aria-label="Enviar mensagem">
              <SendHorizontal aria-hidden="true" />
            </button>
          </form>
        </section>

        <aside aria-label="Fontes da resposta">
          <h2 className="fontes-titulo">De onde veio a resposta</h2>
          {!atual && <Vazio>As fontes de cada resposta aparecem aqui: documento, trecho e nota.</Vazio>}
          {atual?.erro && (
            <Falha erro={atual.erro} tentar={() => perguntar(atual.pergunta)} oQue="o teste do atendente" />
          )}
          {atual && !atual.erro && !atual.resposta && <Vazio>Procurando trechos para “{atual.pergunta}”…</Vazio>}
          {atual?.resposta && !atual.resposta.respondeu && (
            <Vazio
              acoes={
                <>
                  <button className="btn" onClick={() => irPara(`/pesquisa?onde=interno&q=${encodeURIComponent(atual.pergunta)}`)}>
                    Procurar no acervo interno
                  </button>
                  <button className="btn" onClick={() => pedirEnvio()}>Enviar documento</button>
                </>
              }
            >
              <strong>Nenhum trecho público respondia “{atual.pergunta}”.</strong> Se a informação pode ir ao
              cliente, envie um documento público com ela. Se é interna, o atendente fez o certo.
            </Vazio>
          )}
          {atual?.resposta?.respondeu && (
            <ol className="fontes">
              {atual.resposta.fontes.map((fonte, indice) => {
                const { titulo, corpo } = partesDoTrecho(fonte.trecho);
                const id = documentos.get(fonte.documento);
                return (
                  <li key={indice}>
                    <div className="cabeca">
                      {id ? (
                        <button onClick={() => irPara(`/documentos/${id}`)}>{fonte.documento}</button>
                      ) : (
                        <b style={{ fontWeight: 500 }}>{fonte.documento}</b>
                      )}
                      <span className="num" aria-label={`Nota ${score(fonte.score)}`}>{score(fonte.score)}</span>
                    </div>
                    {titulo && <p>{titulo}</p>}
                    <p className="texto">{corpo}</p>
                  </li>
                );
              })}
            </ol>
          )}
        </aside>
      </div>
    </>
  );
}
