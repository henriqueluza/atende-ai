import { Search } from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import { ErroDoServidor, type ModoDeBusca, type ResultadoDeBusca, type Visibilidade } from '../api';
import { palavras } from '../api/exemplo';
import { MarcaDeVisibilidade } from '../components/Comuns';
import { Falha, Osso, Vazio } from '../components/Estados';
import { irPara, useApp } from '../contexto';
import { partesDoTrecho, plural, score } from '../texto';

/** Abaixo disso o atendente ignora o trecho (SCORE_MINIMO do agente). */
const CORTE_DO_ATENDENTE = 0.2;

const MODOS: { id: ModoDeBusca; rotulo: string }[] = [
  { id: 'hibrida', rotulo: 'Híbrida' },
  { id: 'semantica', rotulo: 'Por significado' },
  { id: 'palavras', rotulo: 'Por palavras' },
];

const SUGESTOES = ['Qual o horário de funcionamento?', 'Quanto custa o corte feminino?', 'Posso pagar com Pix?'];

/** Marca no trecho as palavras da pergunta, ignorando acentos e maiúsculas. */
function Destacado({ texto, termos }: { texto: string; termos: Set<string> }) {
  const partes: ReactNode[] = [];
  texto.split(/([\p{L}\p{N}$]+)/u).forEach((parte, indice) => {
    const [normal] = palavras(parte);
    partes.push(normal && termos.has(normal) ? <mark key={indice}>{parte}</mark> : parte);
  });
  return <>{partes}</>;
}

type Estado =
  | { tipo: 'inicio' }
  | { tipo: 'buscando'; pergunta: string }
  | { tipo: 'pronto'; pergunta: string; resultados: ResultadoDeBusca[] }
  | { tipo: 'erro'; pergunta: string; erro: ErroDoServidor };

export function Pesquisa({ perguntaInicial, ondeInicial }: { perguntaInicial: string; ondeInicial: string | null }) {
  const { servidor, revisao } = useApp();
  const [texto, definirTexto] = useState(perguntaInicial);
  const [onde, definirOnde] = useState<Visibilidade>(ondeInicial === 'interno' ? 'interno' : 'publico');
  const [modo, definirModo] = useState<ModoDeBusca>('hibrida');
  const [k, definirK] = useState(5);
  const [estado, definirEstado] = useState<Estado>({ tipo: 'inicio' });
  const [pergunta, definirPergunta] = useState(perguntaInicial.trim());
  const [tentativa, tentarDeNovo] = useState(0);
  const campo = useRef<HTMLInputElement>(null);
  const rodada = useRef(0);
  const documentos = useRef<Map<string, string>>(new Map());

  // A busca devolve o nome do documento; para abrir a página dele é preciso o id.
  useEffect(() => {
    servidor.listarDocumentos().then(
      (lista) => { documentos.current = new Map(lista.map((d) => [d.nome, d.id])); },
      () => undefined,
    );
  }, [servidor, revisao]);

  // A pergunta vinda da barra do topo muda com a página aberta.
  useEffect(() => {
    definirTexto(perguntaInicial);
    definirPergunta(perguntaInicial.trim());
  }, [perguntaInicial]);

  useEffect(() => {
    if (!pergunta) {
      definirEstado({ tipo: 'inicio' });
      campo.current?.focus();
      return;
    }
    const esta = ++rodada.current;
    definirEstado({ tipo: 'buscando', pergunta });
    servidor.buscar({ pergunta, k, visibilidade: onde, modo }).then(
      (resultados) => esta === rodada.current && definirEstado({ tipo: 'pronto', pergunta, resultados }),
      (falha: unknown) =>
        esta === rodada.current &&
        definirEstado({
          tipo: 'erro',
          pergunta,
          erro: falha instanceof ErroDoServidor ? falha : new ErroDoServidor('erro', 'A busca falhou.'),
        }),
    );
  }, [servidor, pergunta, k, onde, modo, revisao, tentativa]);

  const termos = useMemo(() => new Set(palavras(pergunta)), [pergunta]);
  const resultados = estado.tipo === 'pronto' ? estado.resultados : [];
  const uteis = resultados.filter((r) => r.score >= CORTE_DO_ATENDENTE).length;

  function resumo(): ReactNode {
    if (estado.tipo === 'buscando') return <Osso largura={260} />;
    if (estado.tipo !== 'pronto') return 'O que o acervo devolve para uma pergunta, trecho por trecho.';
    if (!resultados.length) return `Nenhum trecho ${onde === 'publico' ? 'público' : 'interno'} parecido com “${estado.pergunta}”.`;
    const total = plural(resultados.length, 'trecho', 'trechos');
    if (onde === 'interno') return `${total} do acervo interno para “${estado.pergunta}”.`;
    if (uteis === resultados.length) return `${total} para “${estado.pergunta}”, todos acima do corte do atendente.`;
    return `${total} para “${estado.pergunta}”; o atendente usaria ${uteis === 0 ? 'nenhum' : `só ${uteis}`}.`;
  }

  return (
    <>
      <div className="titulo">
        <div>
          <h1>Pesquisa</h1>
          <p className="sub">{resumo()}</p>
        </div>
      </div>

      <form
        className="pergunta"
        role="search"
        onSubmit={(evento) => {
          evento.preventDefault();
          definirPergunta(texto.trim());
        }}
      >
        <div className="com-icone">
          <Search aria-hidden="true" />
          <input
            ref={campo}
            className="entrada"
            type="search"
            value={texto}
            maxLength={500}
            onChange={(evento) => definirTexto(evento.target.value)}
            placeholder="Escreva a pergunta como o cliente escreveria"
            aria-label="Pergunta"
          />
        </div>
        <button className="btn primario grande" type="submit" disabled={!texto.trim()}>
          Pesquisar
        </button>
      </form>

      <div className="filtros" style={{ marginBottom: 8 }}>
        <div className="segmentado" role="group" aria-label="Onde procurar">
          {(['publico', 'interno'] as const).map((opcao) => (
            <button key={opcao} type="button" aria-pressed={onde === opcao} onClick={() => definirOnde(opcao)}>
              {opcao === 'publico' ? 'Acervo público' : 'Acervo interno'}
            </button>
          ))}
        </div>
        <div className="segmentado" role="group" aria-label="Modo de busca">
          {MODOS.map(({ id, rotulo }) => (
            <button key={id} type="button" aria-pressed={modo === id} onClick={() => definirModo(id)}>
              {rotulo}
            </button>
          ))}
        </div>
        <span className="espaco" />
        <select
          className="entrada pequena"
          value={k}
          onChange={(evento) => definirK(Number(evento.target.value))}
          aria-label="Quantos trechos mostrar"
        >
          {[3, 5, 10].map((quantidade) => (
            <option key={quantidade} value={quantidade}>
              Até {quantidade} trechos
            </option>
          ))}
        </select>
      </div>

      {estado.tipo === 'inicio' && (
        <Vazio
          acoes={
            <div className="sugestoes">
              {SUGESTOES.map((sugestao) => (
                <button key={sugestao} className="btn" onClick={() => { definirTexto(sugestao); definirPergunta(sugestao); }}>
                  {sugestao}
                </button>
              ))}
            </div>
          }
        >
          <strong>Pergunte como um cliente perguntaria.</strong> A pesquisa mostra os trechos que o acervo
          devolve e a nota de cada um, para você saber o que o atendente teria em mãos.
        </Vazio>
      )}

      {estado.tipo === 'erro' &&
        (estado.erro.tipo === 'nao_disponivel' && modo !== 'semantica' ? (
          <Vazio acoes={<button className="btn" onClick={() => definirModo('semantica')}>Pesquisar por significado</button>}>
            <strong>O servidor em uso não faz busca {modo === 'hibrida' ? 'híbrida' : 'por palavras'}.</strong> Ele
            parece ser de uma versão anterior, que só compara por significado.
          </Vazio>
        ) : (
          <Falha erro={estado.erro} tentar={() => tentarDeNovo((antes) => antes + 1)} oQue="a pesquisa" />
        ))}

      {estado.tipo === 'buscando' && (
        <ul className="resultados" aria-busy="true" aria-label="Pesquisando">
          {[0, 1, 2].map((linha) => (
            <li key={linha}>
              <div className="score"><Osso largura={36} /></div>
              <div><Osso largura="40%" /><br /><Osso largura="85%" /></div>
            </li>
          ))}
        </ul>
      )}

      {estado.tipo === 'pronto' && resultados.length === 0 && (
        <Vazio
          acoes={
            onde === 'publico' ? (
              <button className="btn" onClick={() => definirOnde('interno')}>Procurar no acervo interno</button>
            ) : (
              <button className="btn" onClick={() => definirOnde('publico')}>Procurar no acervo público</button>
            )
          }
        >
          <strong>Nada parecido no acervo {onde === 'publico' ? 'público' : 'interno'}.</strong>{' '}
          {onde === 'publico'
            ? 'Se um cliente perguntar isso, o atendente responde que não encontrou. Vale enviar um documento público que cubra o assunto.'
            : 'Tente outras palavras ou confira se o documento foi enviado.'}
        </Vazio>
      )}

      {estado.tipo === 'pronto' && resultados.length > 0 && (
        <ol className="resultados">
          {resultados.map((resultado, indice) => {
            const { titulo, corpo } = partesDoTrecho(resultado.trecho);
            const fraco = resultado.score < CORTE_DO_ATENDENTE;
            const id = documentos.current.get(resultado.documento);
            return (
              <li key={`${resultado.documento}-${indice}`} data-fraco={fraco}>
                <div className="score">
                  <span className="valor" aria-label={`Nota ${score(resultado.score)}`}>{score(resultado.score)}</span>
                  <div className="trilho" aria-hidden="true">
                    <i style={{ width: `${Math.round(resultado.score * 100)}%` }} />
                  </div>
                </div>
                <div>
                  {titulo && <p className="trecho-titulo"><Destacado texto={titulo} termos={termos} /></p>}
                  <p className="trecho-texto"><Destacado texto={corpo} termos={termos} /></p>
                  <p className="origem">
                    {id ? (
                      <button onClick={() => irPara(`/documentos/${id}`)}>{resultado.documento}</button>
                    ) : (
                      <span>{resultado.documento}</span>
                    )}
                    <MarcaDeVisibilidade valor={onde} />
                    {fraco && onde === 'publico' && (
                      <span>Abaixo do corte de {score(CORTE_DO_ATENDENTE)}: o atendente ignora este trecho.</span>
                    )}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </>
  );
}
