import { useEffect, useRef, type ReactNode } from 'react';

/** Diálogo modal nativo: o navegador cuida do foco preso, do Esc e do fundo inerte. */
export function Dialogo({
  titulo,
  aoFechar,
  children,
}: {
  titulo: string;
  aoFechar(): void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialogo = ref.current;
    if (dialogo && !dialogo.open) dialogo.showModal();
    return () => dialogo?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-label={titulo}
      onCancel={(evento) => {
        evento.preventDefault();
        aoFechar();
      }}
      onClick={(evento) => {
        if (evento.target === ref.current) aoFechar(); // clique no fundo
      }}
    >
      <div className="dialogo">
        <h2>{titulo}</h2>
        {children}
      </div>
    </dialog>
  );
}
