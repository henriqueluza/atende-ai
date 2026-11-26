import { useState } from 'react';

import type { Documento } from '../api';
import { Dialogo } from '../components/Dialogo';
import { mensagemDe, useApp } from '../contexto';
import { plural } from '../texto';

export function ExcluirDocumento({
  documento,
  aoFechar,
  aoExcluir,
}: {
  documento: Documento;
  aoFechar(): void;
  aoExcluir?(): void;
}) {
  const { servidor, avisar, acervoMudou } = useApp();
  const [enviando, definirEnviando] = useState(false);
  const [falha, definirFalha] = useState<string | null>(null);

  async function confirmar() {
    definirEnviando(true);
    definirFalha(null);
    try {
      await servidor.excluirDocumento(documento.id);
      avisar(`${documento.nome} foi excluído.`);
      acervoMudou();
      aoFechar();
      aoExcluir?.();
    } catch (erro) {
      definirFalha(mensagemDe(erro));
      definirEnviando(false);
    }
  }

  return (
    <Dialogo titulo={`Excluir ${documento.nome}?`} aoFechar={aoFechar}>
      <p>
        {documento.trechos
          ? `${plural(documento.trechos, 'trecho sai', 'trechos saem')} da busca agora. `
          : 'O documento sai do acervo agora. '}
        {documento.visibilidade === 'publico' && 'O atendente deixa de usar este conteúdo nas respostas. '}
        Para voltar, é preciso enviar o arquivo de novo.
      </p>
      {falha && (
        <p className="campo">
          <span className="falha" role="alert">
            Não foi possível excluir. {falha}
          </span>
        </p>
      )}
      <div className="rodape">
        <button className="btn" onClick={aoFechar} disabled={enviando}>
          Cancelar
        </button>
        <button className="btn perigo" onClick={confirmar} disabled={enviando}>
          {enviando ? 'Excluindo…' : 'Excluir documento'}
        </button>
      </div>
    </Dialogo>
  );
}
