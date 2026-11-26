import { ArrowRightLeft, FolderOpen, RefreshCw, Search, Trash2, Upload } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import type { Documento } from '../api';
import { NOME_DO_FORMATO } from '../api/formatos';
import { IconeDoFormato, MarcaDeVisibilidade, Situacao } from '../components/Comuns';
import { Falha, Osso, Vazio } from '../components/Estados';
import { Menu } from '../components/Menu';
import { irPara, mensagemDe, useApp, useConsulta } from '../contexto';
import { inteiro, plural, quando } from '../texto';
import { ExcluirDocumento } from './ExcluirDocumento';

type Aba = 'todos' | 'publicos' | 'internos' | 'processando' | 'falhas';

const emProcessamento = (d: Documento) => d.situacao !== 'indexado' && d.situacao !== 'falhou';

const ABAS: { id: Aba; rotulo: string; filtro(d: Documento): boolean }[] = [
  { id: 'todos', rotulo: 'Todos', filtro: () => true },
  { id: 'publicos', rotulo: 'Públicos', filtro: (d) => d.visibilidade === 'publico' },
  { id: 'internos', rotulo: 'Internos', filtro: (d) => d.visibilidade === 'interno' },
  { id: 'processando', rotulo: 'Em processamento', filtro: emProcessamento },
  { id: 'falhas', rotulo: 'Com falha', filtro: (d) => d.situacao === 'falhou' },
];

const somaDeTrechos = (lista: Documento[]) => lista.reduce((soma, d) => soma + (d.trechos ?? 0), 0);

/** A frase sob o título: o fato do acervo que mais pede atenção agora. */
function resumo(documentos: Documento[]): string {
  const falhas = documentos.filter((d) => d.situacao === 'falhou').length;
  const andando = documentos.filter(emProcessamento).length;
  const prontosPublicos = documentos.filter((d) => d.situacao === 'indexado' && d.visibilidade === 'publico').length;
  if (!documentos.length) return 'O acervo está vazio: o atendente ainda não tem de onde responder.';
  if (falhas) {
    return `${plural(falhas, 'documento não pôde ser lido', 'documentos não puderam ser lidos')} e ${falhas === 1 ? 'está' : 'estão'} fora das respostas.`;
  }
  if (andando) return `${plural(andando, 'documento ainda está', 'documentos ainda estão')} sendo processado${andando === 1 ? '' : 's'}.`;
  if (!prontosPublicos) return 'Nenhum documento público pronto: o atendente não tem de onde responder aos clientes.';
  return `O atendente responde aos clientes com ${plural(prontosPublicos, 'documento público', 'documentos públicos')}.`;
}

function descricao(d: Documento): string {
  const partes = [NOME_DO_FORMATO[d.formato]];
  if (d.paginas) partes.push(plural(d.paginas, 'página', 'páginas'));
  if (d.ocr) partes.push('texto lido da imagem');
  return partes.join(', ');
}

export function Documentos() {
  const { servidor, revisao, pedirEnvio, avisar, acervoMudou } = useApp();
  const consulta = useConsulta(() => servidor.listarDocumentos(), [servidor, revisao]);
  const [aba, definirAba] = useState<Aba>('todos');
  const [filtro, definirFiltro] = useState('');
  const [excluindo, excluir] = useState<Documento | null>(null);

  const documentos = consulta.dados;
  // Enquanto houver arquivo na fila, a lista se atualiza sozinha a cada 2 segundos.
  const temFila = (documentos ?? []).some(emProcessamento);
  const { recarregar } = consulta;
  useEffect(() => {
    if (!temFila) return;
    const relogio = setInterval(recarregar, 2000);
    return () => clearInterval(relogio);
  }, [temFila, recarregar]);
  const visiveis = useMemo(() => {
    const termo = filtro.trim().toLowerCase();
    const daAba = ABAS.find((a) => a.id === aba)!.filtro;
    return (documentos ?? []).filter((d) => daAba(d) && d.nome.toLowerCase().includes(termo));
  }, [documentos, aba, filtro]);

  const prontos = (documentos ?? []).filter((d) => d.situacao === 'indexado');
  const publicos = prontos.filter((d) => d.visibilidade === 'publico');
  const internos = prontos.filter((d) => d.visibilidade === 'interno');
  const andando = (documentos ?? []).filter(emProcessamento);
  const falhas = (documentos ?? []).filter((d) => d.situacao === 'falhou');
  const carregandoDoZero = consulta.estado === 'carregando' && !documentos;

  async function trocarVisibilidade(d: Documento) {
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
      <div className="titulo">
        <div>
          <h1>Documentos</h1>
          <p className="sub">{documentos ? resumo(documentos) : <Osso largura={320} />}</p>
        </div>
        <div className="acoes">
          <button className="btn primario" onClick={() => pedirEnvio()}>
            <Upload aria-hidden="true" />
            Enviar documentos
          </button>
        </div>
      </div>

      <dl className="faixa">
        <div>
          <dt>O atendente usa</dt>
          <dd className="num">
            {carregandoDoZero ? <Osso largura={48} /> : inteiro(publicos.length)}
            {!carregandoDoZero && <small>{publicos.length === 1 ? 'documento' : 'documentos'}</small>}
          </dd>
          <p className="legenda">{plural(somaDeTrechos(publicos), 'trecho público', 'trechos públicos')}</p>
        </div>
        <div>
          <dt>Só a equipe vê</dt>
          <dd className="num">
            {carregandoDoZero ? <Osso largura={48} /> : inteiro(internos.length)}
            {!carregandoDoZero && <small>{internos.length === 1 ? 'documento' : 'documentos'}</small>}
          </dd>
          <p className="legenda">{plural(somaDeTrechos(internos), 'trecho interno', 'trechos internos')}</p>
        </div>
        <div>
          <dt>Em processamento</dt>
          <dd className="num">{carregandoDoZero ? <Osso largura={24} /> : inteiro(andando.length)}</dd>
          <p className="legenda">Entram na busca ao terminar</p>
        </div>
        <div>
          <dt>Com falha</dt>
          <dd className="num">{carregandoDoZero ? <Osso largura={24} /> : inteiro(falhas.length)}</dd>
          <p className={falhas.length ? 'legenda alerta' : 'legenda'}>
            {falhas.length === 0 ? 'Nenhum arquivo recusado' : falhas.length === 1 ? 'Precisa ser reenviado' : 'Precisam ser reenviados'}
          </p>
        </div>
      </dl>

      <div className="abas" role="tablist" aria-label="Filtrar documentos">
        {ABAS.map(({ id, rotulo, filtro: daAba }) => (
          <button key={id} role="tab" aria-selected={aba === id} onClick={() => definirAba(id)}>
            {rotulo}
            {documentos && <span className="conta num">{inteiro(documentos.filter(daAba).length)}</span>}
          </button>
        ))}
      </div>

      <div className="filtros">
        <div className="com-icone">
          <Search aria-hidden="true" />
          <input
            className="entrada pequena"
            style={{ width: 280 }}
            type="search"
            value={filtro}
            onChange={(evento) => definirFiltro(evento.target.value)}
            placeholder="Filtrar por nome"
            aria-label="Filtrar por nome"
          />
        </div>
        <span className="espaco" />
        {consulta.quandoCarregou && (
          <span className="carimbo">Atualizado às {quando(consulta.quandoCarregou.toISOString()).replace('Hoje, ', '')}</span>
        )}
        <button className="btn so-icone" aria-label="Atualizar lista" onClick={consulta.recarregar}>
          <RefreshCw aria-hidden="true" />
        </button>
      </div>

      {consulta.estado === 'erro' && (
        <Falha erro={consulta.erro} tentar={consulta.recarregar} oQue="a lista de documentos" />
      )}

      {consulta.estado !== 'erro' && documentos?.length === 0 && (
        <Vazio
          acoes={
            <button className="btn primario" onClick={() => pedirEnvio()}>
              <Upload aria-hidden="true" />
              Enviar o primeiro documento
            </button>
          }
        >
          <strong>Nenhum documento no acervo.</strong> Envie o que o cliente costuma perguntar: horários,
          preços, formas de pagamento, política de cancelamento. Você também pode arrastar os arquivos para
          esta janela.
        </Vazio>
      )}

      {consulta.estado !== 'erro' && (carregandoDoZero || (documentos && documentos.length > 0)) && (
        <div className="tabela-rolagem">
          <table>
            <thead>
              <tr>
                <th>Documento</th>
                <th className="oculta-estreito">Quem vê</th>
                <th className="n oculta-estreito">Trechos</th>
                <th>Situação</th>
                <th className="oculta-estreito">Enviado</th>
                <th className="celula-acao">
                  <span className="so-leitor">Ações</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {carregandoDoZero &&
                [220, 260, 180, 240, 200].map((largura) => (
                  <tr key={largura}>
                    <td><Osso largura={largura} /></td>
                    <td className="oculta-estreito"><Osso largura={64} /></td>
                    <td className="n oculta-estreito"><Osso largura={20} /></td>
                    <td><Osso largura={56} /></td>
                    <td className="oculta-estreito"><Osso largura={72} /></td>
                    <td />
                  </tr>
                ))}
              {visiveis.map((d) => (
                <tr key={d.id}>
                  <td className="celula-nome">
                    <button className="nome-doc" onClick={() => irPara(`/documentos/${d.id}`)}>
                      <IconeDoFormato formato={d.formato} />
                      <span>{d.nome}</span>
                    </button>
                    <span className="sub" style={{ paddingLeft: 24 }}>{descricao(d)}</span>
                    <span className="sub so-estreito" style={{ paddingLeft: 24 }}>
                      {d.visibilidade === 'publico' ? 'Público' : 'Interno'}
                      {d.trechos !== null && `, ${plural(d.trechos, 'trecho', 'trechos')}`}
                    </span>
                  </td>
                  <td className="oculta-estreito">
                    <MarcaDeVisibilidade valor={d.visibilidade} />
                  </td>
                  <td className="n oculta-estreito">
                    {d.trechos === null ? <span style={{ color: 'var(--muted)' }}>–</span> : inteiro(d.trechos)}
                  </td>
                  <td>
                    <Situacao documento={d} />
                    {d.andamento && <span className="sub">{d.andamento}</span>}
                    {d.erro && <span className="sub falha">{d.erro}</span>}
                  </td>
                  <td className="oculta-estreito" style={{ whiteSpace: 'nowrap', color: 'var(--muted)' }}>
                    {quando(d.criadoEm)}
                  </td>
                  <td className="celula-acao">
                    <Menu
                      rotulo={`Ações de ${d.nome}`}
                      itens={[
                        { rotulo: 'Abrir', icone: <FolderOpen aria-hidden="true" />, aoEscolher: () => irPara(`/documentos/${d.id}`) },
                        {
                          rotulo: d.visibilidade === 'publico' ? 'Tornar interno' : 'Tornar público',
                          icone: <ArrowRightLeft aria-hidden="true" />,
                          aoEscolher: () => trocarVisibilidade(d),
                        },
                        { rotulo: 'Excluir', icone: <Trash2 aria-hidden="true" />, perigo: true, aoEscolher: () => excluir(d) },
                      ]}
                    />
                  </td>
                </tr>
              ))}
              {documentos && documentos.length > 0 && visiveis.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <Vazio
                      acoes={
                        <button className="btn" onClick={() => { definirAba('todos'); definirFiltro(''); }}>
                          Limpar filtros
                        </button>
                      }
                    >
                      Nenhum documento {filtro.trim() ? `com “${filtro.trim()}” no nome ` : ''}nesta aba.
                    </Vazio>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {excluindo && <ExcluirDocumento documento={excluindo} aoFechar={() => excluir(null)} />}
    </>
  );
}
