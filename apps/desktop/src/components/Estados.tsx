import { CircleAlert } from 'lucide-react';
import type { ReactNode } from 'react';

import type { ErroDoServidor } from '../api';
import { irPara, useApp } from '../contexto';

/** Barra cinza no tamanho do valor que vai chegar. Sem brilho passando. */
export function Osso({ largura }: { largura: number | string }) {
  return <span className="osso" style={{ width: largura }} aria-hidden="true" />;
}

export function Vazio({ children, acoes }: { children: ReactNode; acoes?: ReactNode }) {
  return (
    <div className="vazio">
      <p>{children}</p>
      {acoes && <div className="acoes">{acoes}</div>}
    </div>
  );
}

/**
 * Falha dentro do bloco que falhou. Três casos com saídas diferentes: servidor fora do ar,
 * servidor de versão anterior (sem a função pedida) e erro comum.
 */
export function Falha({ erro, tentar, oQue }: { erro: ErroDoServidor; tentar: () => void; oQue: string }) {
  const { trocarOrigem, origem } = useApp();
  const verExemplo = origem === 'servidor' && (
    <button className="btn" onClick={() => trocarOrigem('exemplo')}>
      Ver com dados de exemplo
    </button>
  );

  if (erro.tipo === 'nao_disponivel') {
    return (
      <Vazio acoes={verExemplo}>
        <strong>O servidor em uso não oferece {oQue}.</strong> Ele parece ser de uma versão anterior.
        Atualize os serviços com <span className="mono">docker compose up -d --build</span> e tente de novo.
      </Vazio>
    );
  }
  return (
    <div className="erro-bloco" role="alert">
      <CircleAlert aria-hidden="true" />
      <p>
        {erro.tipo === 'fora_do_ar' && !erro.message.startsWith('Não consegui falar com o servidor.')
          ? `Não consegui carregar ${oQue}. ${erro.message}`
          : erro.tipo === 'fora_do_ar'
            ? `Não consegui carregar ${oQue}: o servidor não respondeu. Confira se o Docker está rodando.`
            : `Não consegui carregar ${oQue}. ${erro.message}`}
      </p>
      <button className="btn" onClick={tentar}>
        Tentar de novo
      </button>
      {erro.tipo === 'fora_do_ar' && (
        <button className="btn fantasma" onClick={() => irPara('/configuracoes')}>
          Ver endereço do servidor
        </button>
      )}
      {verExemplo}
    </div>
  );
}
