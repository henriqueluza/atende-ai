"""Casos de uso do núcleo: receber documentos, processar a fila e buscar no acervo."""

import logging
import uuid

from core_api.chunking import dividir_em_trechos
from core_api.dominio import (
    AcervoIndisponivel,
    Consulta,
    Documento,
    DocumentoNoAcervo,
    Embedder,
    Repositorio,
    ResultadoBusca,
    Situacao,
    Trecho,
    TrechoGuardado,
    Visibilidade,
)
from core_api.extracao import ErroDeExtracao, Extrator, conferir_arquivo
from core_api.ocr import OcrIndisponivel

log = logging.getLogger("core_api")

LOTE_DE_EMBEDDINGS = 64


class DocumentoVazio(ValueError):
    """O conteúdo enviado não tem texto para indexar."""


class Acervo:
    def __init__(
        self,
        repositorio: Repositorio,
        embedder: Embedder,
        extrator: Extrator | None = None,
    ) -> None:
        self.repositorio = repositorio
        self._embedder = embedder
        self._extrator = extrator or Extrator(OcrIndisponivel())

    def ingerir(
        self, nome: str, conteudo: str, visibilidade: Visibilidade
    ) -> tuple[Documento, int]:
        """Texto e markdown: divide, gera os embeddings e guarda na hora."""
        textos = dividir_em_trechos(conteudo)
        if not textos:
            raise DocumentoVazio(nome)
        trechos = self._com_embeddings([(texto, None) for texto in textos])
        documento = Documento(id=str(uuid.uuid4()), nome=nome, visibilidade=visibilidade)
        self.repositorio.salvar(documento, trechos)
        return documento, len(trechos)

    def receber_arquivo(self, nome: str, conteudo: bytes, visibilidade: Visibilidade) -> Documento:
        """PDF e imagem: confere o arquivo e põe na fila. Ler e indexar acontece depois."""
        conferir_arquivo(nome, conteudo)  # levanta ErroDeExtracao
        documento = Documento(id=str(uuid.uuid4()), nome=nome, visibilidade=visibilidade)
        self.repositorio.enfileirar(documento, conteudo)
        return documento

    def processar_proximo(self) -> bool:
        """Processa um arquivo da fila. Devolve False quando a fila está vazia.

        Nenhuma falha de um arquivo derruba a fila: ela vira a situação FALHOU, com uma frase
        que quem enviou consegue entender.
        """
        arquivo = self.repositorio.proximo_da_fila()
        if arquivo is None:
            return False
        id, nome = arquivo.documento.id, arquivo.documento.nome
        try:
            paginas = self._extrator.extrair(
                nome,
                arquivo.conteudo,
                lambda frase: self.repositorio.registrar_andamento(id, Situacao.EXTRAINDO, frase),
            )
            self.repositorio.registrar_andamento(id, Situacao.INDEXANDO, None)
            textos = [
                (texto, pagina.numero)
                for pagina in paginas
                for texto in dividir_em_trechos(pagina.texto)
            ]
            if not textos:
                raise ErroDeExtracao("Não encontrei texto neste arquivo.")
            self.repositorio.concluir(
                id,
                self._com_embeddings(textos),
                ocr=any(pagina.ocr for pagina in paginas),
                paginas=max(pagina.numero for pagina in paginas),
            )
        except ErroDeExtracao as erro:
            self.repositorio.falhar(id, str(erro))
        except AcervoIndisponivel as erro:
            log.error("Processamento interrompido (%s): dependência fora do ar", erro)
            self.repositorio.falhar(
                id, "O servidor ficou indisponível durante o processamento. Envie de novo."
            )
        except Exception:  # um arquivo estranho não pode parar os outros
            log.exception("Falha inesperada ao processar um arquivo")
            self.repositorio.falhar(id, "Não consegui processar este arquivo.")
        return True

    def buscar(self, pergunta: str, k: int, visibilidade: Visibilidade) -> list[ResultadoBusca]:
        [embedding] = self._embedder.gerar([pergunta])
        return self.repositorio.buscar(Consulta(pergunta, embedding, k, visibilidade))

    def listar(self) -> list[DocumentoNoAcervo]:
        """Todos os documentos do acervo. É para quem administra: inclui os internos."""
        return self.repositorio.listar()

    def detalhar(self, id: str) -> tuple[DocumentoNoAcervo, list[TrechoGuardado]] | None:
        documento = self.repositorio.obter(id)
        return (documento, self.repositorio.trechos_de(id)) if documento else None

    def excluir(self, id: str) -> bool:
        return self.repositorio.excluir(id)

    def alterar_visibilidade(self, id: str, visibilidade: Visibilidade) -> bool:
        return self.repositorio.alterar_visibilidade(id, visibilidade)

    def _com_embeddings(self, textos: list[tuple[str, int | None]]) -> list[Trecho]:
        trechos: list[Trecho] = []
        for inicio in range(0, len(textos), LOTE_DE_EMBEDDINGS):
            lote = textos[inicio : inicio + LOTE_DE_EMBEDDINGS]
            vetores = self._embedder.gerar([texto for texto, _ in lote])
            trechos += [
                Trecho(texto, vetor, pagina)
                for (texto, pagina), vetor in zip(lote, vetores, strict=True)
            ]
        return trechos
