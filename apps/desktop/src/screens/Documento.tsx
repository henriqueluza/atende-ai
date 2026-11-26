import { ChevronRight, Circle, CircleCheck, CircleDashed, CircleX } from 'lucide-react';
import { useEffect, useState } from 'react';

import { ErroDoServidor, type DetalheDoDocumento } from '../api';
import { NOME_DO_FORMATO } from '../api/formatos';
import { MarcaDeVisibilidade, Situacao } from '../components/Comuns';
import { Falha, Osso, Vazio } from '../components/Estados';
import { irPara, mensagemDe, useApp, useConsulta } from '../contexto';
import { inteiro, partesDoTrecho, plural, quando } from '../texto';
import { ExcluirDocumento } from './ExcluirDocumento';

const ICONE_DO_PASSO = { feito: CircleCheck, em_andamento: CircleDashed, pendente: Circle, falhou: CircleX };
const NOME_DO_ESTADO = { feito: 'feito', em_andamento: 'em andamento', pendente: 'pendente', falhou: 'falhou' };

interface Carregado extends DetalheDoDocumento {
  /** false quando o servidor só soube dizer o básico (sem trechos nem etapas). */
  completo: boolean;
}

export function Documento({ id }: { id: string }) {
  const { servidor, revisao, avisar, acervoMudou } = useApp();
  const [aba, definirAba] = useState<'trechos' | 'processamento'>('trechos');
  const [excluindo, excluir] = useState(false);

  const consulta = useConsulta<Carregado>(async () => {
    try {
      return { ...(await servidor.detalharDocumento(id)), completo: true };
    } catch (falha) {
      // Um servidor de versão anterior lista os documentos mas não abre um por um:
      // mostra o que a lista sabe e deixa claro o que falta.
      if (!(falha instanceof ErroDoServidor) || falha.tipo !== 'nao_disponivel') throw falha;
      const documento = (await servidor.listarDocumentos()).find((d) => d.id === id);
      if (!documento) throw new ErroDoServidor('recusado', 'Documento não encontrado.');
      return { documento, trechos: [], passos: [], completo: false };
    }
  }, [servidor, id, revisao]);

  const d = consulta.dados?.documento;
  // Enquanto o arquivo é processado, a página acompanha o andamento.
  const andando = d ? d.situacao !== 'indexado' && d.situacao !== 'falhou' : false;
  const { recarregar } = consulta;
  useEffect(() => {
    if (!andando) return;
    const relogio = setInterval(recarregar, 2000);
    return () => clearInterval(relogio);
  }, [andando, recarregar]);

  async function trocarVisibilidade() {
    if (!d) return;
    const nova = d.visibilidade === 'publico' ? 'interno' : 'publico';
    try {
      await servidor.alterarVisibilidade(d.id, nova);
      avisar(nova === 'publico' ? `${d.nome} agora é público.` : `${d.nome} agora é interno.`);
      acervoMudou();
    } catch (falha) {
      avisar(`Não foi possível mudar a visibilidade. ${mensagemDe(falha)}`);
    }
  }

  return (
    <>
      <div className="titulo" style={{ alignItems: 'center' }}>
        <div className="migalhas">
          <a href="#/documentos">Documentos</a>
          <ChevronRight aria-hidden="true" />
          <h1>{d ? d.nome : consulta.estado === 'erro' ? 'Documento' : <Osso largura={180} />}</h1>
        </div>
        {d && (
          <div className="acoes">
            <button className="btn" onClick={trocarVisibilidade}>
              {d.visibilidade === 'publico' ? 'Tornar interno' : 'Tornar público'}
            </button>
            <button className="btn perigo" onClick={() => excluir(true)}>
              Excluir
            </button>
          </div>
        )}
      </div>

      {consulta.estado === 'erro' && !d && (
        <Falha erro={consulta.erro} tentar={consulta.recarregar} oQue="este documento" />
      )}

      {d && consulta.dados && (
        <>
          <div className="ficha">
            <Situacao documento={d} />
            <MarcaDeVisibilidade valor={d.visibilidade} />
            <span>{NOME_DO_FORMATO[d.formato]}{d.paginas ? `, ${plural(d.paginas, 'página', 'páginas')}` : ''}</span>
            <span>Enviado: <b>{quando(d.criadoEm)}</b></span>
            {d.visibilidade === 'publico' && d.situacao === 'indexado' && <span>O atendente usa este documento nas respostas.</span>}
            {d.visibilidade === 'interno' && <span>Nunca chega ao cliente.</span>}
          </div>

          <div className="abas" role="tablist" aria-label="Partes do documento">
            <button role="tab" aria-selected={aba === 'trechos'} onClick={() => definirAba('trechos')}>
              Trechos
              {d.trechos !== null && <span className="conta num">{inteiro(d.trechos)}</span>}
            </button>
            <button role="tab" aria-selected={aba === 'processamento'} onClick={() => definirAba('processamento')}>
              Processamento
            </button>
          </div>

          {aba === 'trechos' &&
            (consulta.dados.trechos.length ? (
              <ol className="trechos">
                {consulta.dados.trechos.map((trecho) => {
                  const { titulo, corpo } = partesDoTrecho(trecho.texto);
                  return (
                    <li key={trecho.posicao}>
                      <span className="pos" aria-hidden="true">{trecho.posicao + 1}</span>
                      <div>
                        {titulo && <p className="trecho-titulo">{titulo}</p>}
                        <p className="trecho-texto">{corpo}</p>
                        {trecho.pagina && <p className="origem">Página {trecho.pagina}</p>}
                      </div>
                    </li>
                  );
                })}
              </ol>
            ) : !consulta.dados.completo ? (
              <Vazio>
                <strong>O servidor em uso não mostra os trechos de um documento.</strong> Ele parece ser de uma
                versão anterior. Para conferir o que foi indexado, pesquise por um assunto dele.
              </Vazio>
            ) : d.situacao === 'falhou' ? (
              <Vazio acoes={<button className="btn" onClick={() => definirAba('processamento')}>Ver o que falhou</button>}>
                <strong>Nenhum trecho: o arquivo não pôde ser lido.</strong> {d.erro}
              </Vazio>
            ) : (
              <Vazio>Os trechos aparecem aqui quando o processamento terminar.</Vazio>
            ))}

          {aba === 'processamento' &&
            (consulta.dados.passos.length ? (
              <ol className="passos">
                {consulta.dados.passos.map((passo) => {
                  const Icone = ICONE_DO_PASSO[passo.estado];
                  return (
                    <li key={passo.nome} data-estado={passo.estado}>
                      <Icone aria-hidden="true" />
                      <div>
                        <span className="passo-nome">{passo.nome}</span>
                        <span className="so-leitor"> ({NOME_DO_ESTADO[passo.estado]})</span>
                        {passo.detalhe && <span className="sub">{passo.detalhe}</span>}
                      </div>
                      <span className="carimbo">{passo.quando ? quando(passo.quando) : ''}</span>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <Vazio>
                <strong>O servidor em uso não informa as etapas do processamento.</strong> Ele parece ser de uma
                versão anterior.
              </Vazio>
            ))}
        </>
      )}

      {excluindo && d && (
        <ExcluirDocumento documento={d} aoFechar={() => excluir(false)} aoExcluir={() => irPara('/documentos')} />
      )}
    </>
  );
}
