import '../vendor/charts.js';

import { useEffect, useRef, useState } from 'react';

import type { Avaliacao, PerguntaAvaliada } from '../api';
import { Falha, Osso, Vazio } from '../components/Estados';
import { mensagemDe, useApp, useConsulta } from '../contexto';
import { dataCurta, inteiro, plural, pontos, porcento, score } from '../texto';

declare global {
  interface Window {
    Charts: {
      line(
        elemento: HTMLElement,
        opcoes: {
          labels: string[];
          series: { name: string; values: number[] }[];
          format: (valor: number) => string;
          height: number;
          yTicks: number[];
          xAt?: number[];
          annotations?: { at: number; label: string; short?: string }[];
        },
      ): unknown;
    };
  }
}

function Grafico({ avaliacao }: { avaliacao: Avaliacao }) {
  const alvo = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const elemento = alvo.current;
    if (!elemento) return;
    elemento.replaceChildren();
    const execucoes = avaliacao.execucoes;
    window.Charts.line(elemento, {
      labels: execucoes.map((e) => (e.versao ? `${dataCurta(e.data)}, ${e.versao}` : dataCurta(e.data))),
      series: [{ name: 'Acerto', values: execucoes.map((e) => e.acertos / e.perguntas) }],
      format: porcento,
      height: 240,
      yTicks: [0, 0.25, 0.5, 0.75, 1],
      xAt: [0, execucoes.length - 1],
      annotations: execucoes.flatMap((e, indice) => (e.nota ? [{ at: indice, label: e.nota }] : [])),
    });
  }, [avaliacao]);
  return <div className="grafico" ref={alvo} />;
}

const falhou = (p: PerguntaAvaliada, k: number) => p.posicao === null || p.posicao > k;

export function Qualidade() {
  const { servidor, avisar } = useApp();
  const consulta = useConsulta(() => servidor.avaliacao(), [servidor]);
  const [aba, definirAba] = useState<'falhas' | 'todas'>('falhas');
  const [rodando, definirRodando] = useState(false);
  const avaliacao = consulta.dados;

  async function rodar() {
    definirRodando(true);
    try {
      await servidor.rodarAvaliacao();
      avisar('Avaliação concluída.');
      consulta.recarregar();
    } catch (falha) {
      avisar(`A avaliação não rodou. ${mensagemDe(falha)}`);
    }
    definirRodando(false);
  }

  if (consulta.estado === 'erro' && !avaliacao) {
    return (
      <>
        <div className="titulo">
          <div>
            <h1>Qualidade da busca</h1>
            <p className="sub">Um conjunto fixo de perguntas de cliente, conferido a cada mudança no sistema.</p>
          </div>
        </div>
        <Falha erro={consulta.erro} tentar={consulta.recarregar} oQue="a avaliação da busca" />
      </>
    );
  }

  if (avaliacao && avaliacao.execucoes.length === 0) {
    return (
      <>
        <div className="titulo">
          <div>
            <h1>Qualidade da busca</h1>
            <p className="sub">Um conjunto fixo de perguntas de cliente, conferido a cada mudança no sistema.</p>
          </div>
        </div>
        <Vazio>
          <strong>Nenhuma avaliação rodou ainda.</strong> Escreva as perguntas que os clientes fazem e em que
          documento está a resposta (uma por linha, como em{' '}
          <span className="mono">ml/avaliacao/perguntas.jsonl</span>) e envie com{' '}
          <span className="mono">python -m agent.cli avaliar arquivo.jsonl</span>. Depois disso, dá para
          repetir a avaliação por aqui.
        </Vazio>
      </>
    );
  }

  const ultima = avaliacao?.execucoes.at(-1);
  const anterior = avaliacao?.execucoes.at(-2);
  const taxa = ultima ? ultima.acertos / ultima.perguntas : 0;
  const mudanca = ultima && anterior ? taxa - anterior.acertos / anterior.perguntas : null;
  const falhas = avaliacao ? avaliacao.perguntas.filter((p) => falhou(p, avaliacao.k)) : [];
  const foraDaLista = falhas.filter((p) => p.posicao === null).length;
  const linhas = aba === 'falhas' ? falhas : (avaliacao?.perguntas ?? []);

  return (
    <>
      <div className="titulo">
        <div>
          <h1>Qualidade da busca</h1>
          <p className="sub">
            {avaliacao && ultima ? (
              `${inteiro(ultima.acertos)} de ${plural(ultima.perguntas, 'pergunta de teste traz', 'perguntas de teste trazem')} o documento certo entre os ${avaliacao.k} primeiros trechos; ${falhas.length === 0 ? 'nenhuma falha' : plural(falhas.length, 'ainda falha', 'ainda falham')}.`
            ) : (
              <Osso largura={420} />
            )}
          </p>
        </div>
        {ultima && (
          <div className="acoes" style={{ alignItems: 'center' }}>
            <span className="carimbo">
              Última execução: {dataCurta(ultima.data)}
              {ultima.versao && <>, versão <span className="mono">{ultima.versao}</span></>}
            </span>
            <button className="btn" onClick={rodar} disabled={rodando}>
              {rodando ? 'Avaliando…' : 'Avaliar de novo'}
            </button>
          </div>
        )}
      </div>

      <section className="painel relatorio" aria-label="Acerto por execução">
        <div>
          <p className="destaque num">{ultima ? porcento(taxa) : <Osso largura={110} />}</p>
          <p className="destaque-rotulo">Acerto entre os {avaliacao?.k ?? 3} primeiros</p>
          <p className="variacao">
            {mudanca === null || !anterior ? (
              'Primeira execução: ainda sem comparação.'
            ) : mudanca === 0 ? (
              <>Igual à execução anterior</>
            ) : (
              <>
                <span className={mudanca > 0 ? 'bom' : 'ruim'}>
                  {mudanca > 0 ? '+' : '−'}
                  {pontos(mudanca)} p.p.
                </span>{' '}
                em relação à execução anterior
              </>
            )}
          </p>
          <dl className="medidas">
            <div>
              <dt>Perguntas de teste</dt>
              <dd>{ultima ? inteiro(ultima.perguntas) : '–'}</dd>
            </div>
            <div>
              <dt>Posição média do acerto (MRR)</dt>
              <dd>{ultima ? score(ultima.mrr) : '–'}</dd>
            </div>
            <div>
              <dt>Documento certo fora da lista</dt>
              <dd>{avaliacao ? inteiro(foraDaLista) : '–'}</dd>
            </div>
          </dl>
        </div>
        <div>
          <div className="grafico-cabeca">
            <h3>Acerto por execução</h3>
            {avaliacao && <span className="carimbo">{plural(avaliacao.execucoes.length, 'execução', 'execuções')}</span>}
          </div>
          {avaliacao ? <Grafico avaliacao={avaliacao} /> : <div style={{ height: 240 }} />}
        </div>
      </section>

      <div className="abas" role="tablist" aria-label="Perguntas de teste">
        <button role="tab" aria-selected={aba === 'falhas'} onClick={() => definirAba('falhas')}>
          Falharam<span className="conta num">{avaliacao ? inteiro(falhas.length) : ''}</span>
        </button>
        <button role="tab" aria-selected={aba === 'todas'} onClick={() => definirAba('todas')}>
          Todas<span className="conta num">{avaliacao ? inteiro(avaliacao.perguntas.length) : ''}</span>
        </button>
      </div>

      {avaliacao && linhas.length === 0 ? (
        <div className="vazio">
          <p>Nenhuma pergunta falhou na última execução.</p>
        </div>
      ) : (
        <div className="tabela-rolagem">
          <table>
            <thead>
              <tr>
                <th>Pergunta</th>
                <th>Documento esperado</th>
                <th>Veio em primeiro</th>
                <th className="n">Posição do certo</th>
              </tr>
            </thead>
            <tbody>
              {!avaliacao &&
                [0, 1, 2].map((linha) => (
                  <tr key={linha}>
                    <td><Osso largura={240} /></td>
                    <td><Osso largura={150} /></td>
                    <td><Osso largura={150} /></td>
                    <td className="n"><Osso largura={16} /></td>
                  </tr>
                ))}
              {linhas.map((p) => (
                <tr key={p.pergunta}>
                  <td style={{ width: '38%', fontWeight: 500 }}>{p.pergunta}</td>
                  <td>{p.esperado}</td>
                  <td style={{ color: p.primeiro === p.esperado ? undefined : 'var(--muted)' }}>{p.primeiro}</td>
                  <td className="n">
                    {p.posicao === null ? (
                      <span style={{ color: 'var(--negative)' }}>não veio</span>
                    ) : (
                      <span style={{ color: falhou(p, avaliacao!.k) ? 'var(--negative)' : undefined }}>{p.posicao}º</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
