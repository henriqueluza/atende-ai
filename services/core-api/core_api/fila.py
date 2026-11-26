"""O trabalhador da fila: uma thread que lê e indexa os arquivos enviados. Ver ADR 0006."""

import logging
import threading

from core_api.acervo import Acervo
from core_api.dominio import AcervoIndisponivel

log = logging.getLogger("core_api")

PAUSA_SEM_TRABALHO = 1.0  # segundos entre uma olhada e outra quando a fila está vazia
PAUSA_APOS_ERRO = 5.0


class Trabalhador:
    def __init__(self, acervo: Acervo) -> None:
        self._acervo = acervo
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._rodar, name="fila-de-documentos", daemon=True)

    def iniciar(self) -> None:
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        self._thread.join(timeout=10)

    def _rodar(self) -> None:
        try:
            # O que ficou pela metade na última parada volta para a fila.
            retomados = self._acervo.repositorio.retomar_interrompidos()
            if retomados:
                log.info("%d documento(s) voltaram para a fila", retomados)
        except AcervoIndisponivel:
            log.error("Não consegui conferir a fila ao iniciar")
        while not self._parar.is_set():
            try:
                trabalhou = self._acervo.processar_proximo()
                pausa = 0 if trabalhou else PAUSA_SEM_TRABALHO
            except AcervoIndisponivel:
                log.error("Banco fora do ar: a fila tenta de novo em instantes")
                pausa = PAUSA_APOS_ERRO
            self._parar.wait(pausa)
