import { Eye, FileImage, FileText, FileType, Lock } from 'lucide-react';

import type { Documento, Formato, Visibilidade } from '../api';

/** A marca: um balão de conversa com a página de um documento dentro. */
export function Marca() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
      <path
        d="M4 2.5h14A2.5 2.5 0 0 1 20.5 5v9a2.5 2.5 0 0 1-2.5 2.5h-6.2L7 20.2v-3.7H4A2.5 2.5 0 0 1 1.5 14V5A2.5 2.5 0 0 1 4 2.5Z"
        fill="currentColor"
      />
      <path d="M6.5 7.2h9M6.5 10.2h9M6.5 13.2h5" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function IconeDoFormato({ formato }: { formato: Formato }) {
  const Icone = formato === 'pdf' ? FileType : formato === 'imagem' ? FileImage : FileText;
  return <Icone width={16} height={16} strokeWidth={1.5} color="var(--faint)" aria-hidden="true" />;
}

export const NOME_DA_VISIBILIDADE: Record<Visibilidade, string> = { publico: 'Público', interno: 'Interno' };

export function MarcaDeVisibilidade({ valor }: { valor: Visibilidade }) {
  const Icone = valor === 'publico' ? Eye : Lock;
  return (
    <span className="visib" data-v={valor}>
      <Icone aria-hidden="true" />
      {NOME_DA_VISIBILIDADE[valor]}
    </span>
  );
}

export function Situacao({ documento }: { documento: Documento }) {
  switch (documento.situacao) {
    case 'indexado':
      return <span className="pilula pos">Pronto</span>;
    case 'falhou':
      return <span className="pilula neg">Falhou</span>;
    case 'na_fila':
      return <span className="pilula">Na fila</span>;
    default:
      return (
        <span className="pilula">
          <span className="girando" aria-hidden="true" />
          {documento.situacao === 'extraindo' ? 'Lendo o arquivo' : 'Indexando'}
        </span>
      );
  }
}
