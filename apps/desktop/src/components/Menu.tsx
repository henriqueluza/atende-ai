import { Ellipsis } from 'lucide-react';
import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

export interface ItemDeMenu {
  rotulo: string;
  icone?: ReactNode;
  perigo?: boolean;
  aoEscolher(): void;
}

/** Menu de ações de uma linha. Teclado: Enter abre, setas andam, Esc fecha e devolve o foco. */
export function Menu({ rotulo, itens }: { rotulo: string; itens: ItemDeMenu[] }) {
  const [aberto, abrir] = useState(false);
  const ancora = useRef<HTMLDivElement>(null);
  const botao = useRef<HTMLButtonElement>(null);
  const id = useId();

  useEffect(() => {
    if (!aberto) return;
    ancora.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    const fora = (evento: PointerEvent) => {
      if (!ancora.current?.contains(evento.target as Node)) abrir(false);
    };
    document.addEventListener('pointerdown', fora);
    return () => document.removeEventListener('pointerdown', fora);
  }, [aberto]);

  function aoTeclar(evento: React.KeyboardEvent) {
    if (evento.key === 'Escape') {
      abrir(false);
      botao.current?.focus();
      return;
    }
    if (evento.key !== 'ArrowDown' && evento.key !== 'ArrowUp') return;
    evento.preventDefault();
    const opcoes = [...(ancora.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? [])];
    const atual = opcoes.indexOf(document.activeElement as HTMLButtonElement);
    const passo = evento.key === 'ArrowDown' ? 1 : -1;
    opcoes[(atual + passo + opcoes.length) % opcoes.length]?.focus();
  }

  return (
    <div className="menu-ancora" ref={ancora} onKeyDown={aoTeclar}>
      <button
        ref={botao}
        className="btn fantasma so-icone"
        aria-label={rotulo}
        aria-haspopup="menu"
        aria-expanded={aberto}
        aria-controls={aberto ? id : undefined}
        onClick={() => abrir(!aberto)}
      >
        <Ellipsis aria-hidden="true" />
      </button>
      {aberto && (
        <div className="menu-lista" role="menu" id={id}>
          {itens.map((item) => (
            <button
              key={item.rotulo}
              role="menuitem"
              className={item.perigo ? 'perigo' : undefined}
              onClick={() => {
                abrir(false);
                item.aoEscolher();
              }}
            >
              {item.icone}
              {item.rotulo}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
