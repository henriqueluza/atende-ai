import { Check, CircleAlert, X } from 'lucide-react';
import { useEffect, useId, useRef, useState } from 'react';

import type { Formato, Visibilidade } from '../api';
import {
  ehTexto,
  EXTENSOES_ACEITAS,
  formatoDe,
  TAMANHO_MAXIMO_ARQUIVO,
  TAMANHO_MAXIMO_TEXTO,
} from '../api/formatos';
import { IconeDoFormato } from '../components/Comuns';
import { Dialogo } from '../components/Dialogo';
import { mensagemDe, useApp } from '../contexto';
import { plural, tamanho } from '../texto';

interface Item {
  arquivo: File;
  formato: Formato | null;
  /** Motivo pelo qual o arquivo não será enviado, conferido antes de sair da máquina. */
  recusa: string | null;
  estado: 'aguardando' | 'enviando' | 'enviado' | 'falhou';
  falha?: string;
}

function conferir(arquivo: File): Item {
  const formato = formatoDe(arquivo.name);
  let recusa: string | null = null;
  if (!formato) recusa = 'Formato não aceito. Use Markdown, texto, PDF ou imagem.';
  else if (arquivo.size === 0) recusa = 'O arquivo está vazio.';
  else if (ehTexto(formato) && arquivo.size > TAMANHO_MAXIMO_TEXTO) {
    recusa = `Texto grande demais: o limite é ${tamanho(TAMANHO_MAXIMO_TEXTO)}.`;
  } else if (arquivo.size > TAMANHO_MAXIMO_ARQUIVO) {
    recusa = `Arquivo grande demais: o limite é ${tamanho(TAMANHO_MAXIMO_ARQUIVO)}.`;
  } else if (arquivo.name.length > 200) recusa = 'Nome longo demais: o limite é 200 caracteres.';
  return { arquivo, formato, recusa, estado: 'aguardando' };
}

export function EnviarDocumentos({ iniciais, aoFechar }: { iniciais: File[]; aoFechar(): void }) {
  const { servidor, avisar, acervoMudou } = useApp();
  const [itens, definirItens] = useState<Item[]>([]);
  const [visibilidade, definirVisibilidade] = useState<Visibilidade | null>(null);
  const [existentes, definirExistentes] = useState<Set<string>>(new Set());
  const [enviando, definirEnviando] = useState(false);
  const [sobre, definirSobre] = useState(false);
  const [faltaEscolha, definirFaltaEscolha] = useState(false);
  const seletor = useRef<HTMLInputElement>(null);
  const idDica = useId();

  const acrescentar = (arquivos: File[]) =>
    definirItens((antes) => {
      const nomes = new Set(antes.map((item) => item.arquivo.name));
      return [...antes, ...arquivos.filter((arquivo) => !nomes.has(arquivo.name)).map(conferir)];
    });

  // Arquivos soltos na janela chegam por aqui, inclusive com o diálogo já aberto.
  useEffect(() => acrescentar(iniciais), [iniciais]);

  // Reenviar um nome que já existe substitui o documento: melhor avisar antes.
  useEffect(() => {
    servidor.listarDocumentos().then(
      (lista) => definirExistentes(new Set(lista.map((d) => d.nome))),
      () => undefined,
    );
  }, [servidor]);

  const validos = itens.filter((item) => !item.recusa && item.estado !== 'enviado');
  const terminou = itens.length > 0 && itens.every((item) => item.recusa || item.estado === 'enviado');

  async function enviar() {
    if (!visibilidade) {
      definirFaltaEscolha(true);
      return;
    }
    definirEnviando(true);
    let enviados = 0;
    for (const item of validos) {
      const marcar = (mudanca: Partial<Item>) =>
        definirItens((antes) => antes.map((outro) => (outro.arquivo === item.arquivo ? { ...outro, ...mudanca } : outro)));
      marcar({ estado: 'enviando', falha: undefined });
      try {
        const texto = item.formato && ehTexto(item.formato);
        await servidor.enviarDocumento({
          nome: item.arquivo.name,
          visibilidade,
          // Remove o marcador de ordem de bytes (BOM), como faz a linha de comando.
          conteudo: texto ? (await item.arquivo.text()).replace(/^﻿/, '') : null,
          arquivo: texto ? null : item.arquivo,
        });
        marcar({ estado: 'enviado' });
        enviados += 1;
      } catch (falha) {
        marcar({ estado: 'falhou', falha: mensagemDe(falha) });
      }
    }
    definirEnviando(false);
    if (enviados) {
      acervoMudou();
      avisar(`${plural(enviados, 'documento enviado', 'documentos enviados')} como ${visibilidade === 'publico' ? 'público' : 'interno'}.`);
    }
    if (enviados === validos.length) aoFechar();
  }

  return (
    <Dialogo titulo="Enviar documentos" aoFechar={() => !enviando && aoFechar()}>
      <div
        className="soltar"
        data-sobre={sobre}
        onDragEnter={() => definirSobre(true)}
        onDragLeave={() => definirSobre(false)}
        onDrop={() => definirSobre(false)}
      >
        <p>Arraste os arquivos para cá</p>
        <button className="btn" onClick={() => seletor.current?.click()} aria-describedby={idDica}>
          Escolher arquivos
        </button>
        <p className="dica" id={idDica}>
          Markdown e texto até {tamanho(TAMANHO_MAXIMO_TEXTO)}. PDF e imagem até {tamanho(TAMANHO_MAXIMO_ARQUIVO)}.
        </p>
        <input
          ref={seletor}
          type="file"
          multiple
          hidden
          accept={EXTENSOES_ACEITAS.join(',')}
          onChange={(evento) => {
            acrescentar([...(evento.target.files ?? [])]);
            evento.target.value = '';
          }}
        />
      </div>

      {itens.length > 0 && (
        <ul className="arquivos" aria-label="Arquivos escolhidos">
          {itens.map((item) => {
            const problema = item.recusa ?? item.falha;
            return (
              <li key={item.arquivo.name}>
                {item.estado === 'enviado' ? (
                  <Check width={16} height={16} color="var(--positive)" aria-hidden="true" />
                ) : problema ? (
                  <CircleAlert width={16} height={16} strokeWidth={1.5} color="var(--negative)" aria-hidden="true" />
                ) : (
                  <IconeDoFormato formato={item.formato ?? 'texto'} />
                )}
                <div className="nome">
                  <span>{item.arquivo.name}</span>
                  {problema ? (
                    <span className="sub falha">{problema}</span>
                  ) : item.estado === 'enviado' ? (
                    <span className="sub certo">Enviado</span>
                  ) : item.estado === 'enviando' ? (
                    <span className="sub">Enviando…</span>
                  ) : existentes.has(item.arquivo.name) ? (
                    <span className="sub">{tamanho(item.arquivo.size)}. Substitui o documento de mesmo nome.</span>
                  ) : (
                    <span className="sub">{tamanho(item.arquivo.size)}</span>
                  )}
                </div>
                {!enviando && item.estado !== 'enviado' && (
                  <button
                    className="btn fantasma so-icone"
                    aria-label={`Tirar ${item.arquivo.name} da lista`}
                    onClick={() => definirItens((antes) => antes.filter((outro) => outro !== item))}
                  >
                    <X aria-hidden="true" />
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <fieldset className="campo" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="rotulo" style={{ padding: 0, marginBottom: 8 }}>
          Quem pode ver estes documentos?
        </legend>
        <div className="escolha">
          <label>
            <input
              type="radio"
              name="visibilidade"
              checked={visibilidade === 'publico'}
              onChange={() => { definirVisibilidade('publico'); definirFaltaEscolha(false); }}
            />
            <strong>Público</strong>
            <span className="dica">O atendente pode usar nas respostas aos clientes.</span>
          </label>
          <label>
            <input
              type="radio"
              name="visibilidade"
              checked={visibilidade === 'interno'}
              onChange={() => { definirVisibilidade('interno'); definirFaltaEscolha(false); }}
            />
            <strong>Interno</strong>
            <span className="dica">Só a equipe pesquisa. Nunca chega ao cliente.</span>
          </label>
        </div>
        {faltaEscolha && (
          <span className="falha" role="alert">
            Escolha quem pode ver antes de enviar.
          </span>
        )}
      </fieldset>

      <div className="rodape">
        <button className="btn" onClick={aoFechar} disabled={enviando}>
          {terminou ? 'Fechar' : 'Cancelar'}
        </button>
        <button className="btn primario" onClick={enviar} disabled={enviando || validos.length === 0}>
          {enviando
            ? 'Enviando…'
            : validos.length
              ? `Enviar ${plural(validos.length, 'documento', 'documentos')}`
              : 'Enviar documentos'}
        </button>
      </div>
    </Dialogo>
  );
}
