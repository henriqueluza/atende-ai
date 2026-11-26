"""Repositório em memória: para testes e para rodar sem banco. Os dados somem no restart."""

import threading
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from core_api.dominio import (
    ArquivoNaFila,
    Consulta,
    Documento,
    DocumentoNoAcervo,
    Modo,
    ResultadoBusca,
    Situacao,
    Trecho,
    TrechoGuardado,
    Visibilidade,
)
from core_api.palavras import cobertura


@dataclass
class _Registro:
    ficha: DocumentoNoAcervo
    trechos: list[Trecho] = field(default_factory=list)
    arquivo: bytes | None = None


class RepositorioMemoria:
    def __init__(self) -> None:
        self._acervo: dict[str, _Registro] = {}  # por nome, que é a identidade do documento
        self._avaliacoes: list[dict[str, Any]] = []
        # A fila roda em outra thread: toda leitura e escrita passa por esta trava.
        self._trava = threading.RLock()

    def salvar(self, documento: Documento, trechos: list[Trecho]) -> None:
        with self._trava:
            ficha = DocumentoNoAcervo(
                documento.id, documento.nome, documento.visibilidade, len(trechos), _agora()
            )
            self._acervo[documento.nome] = _Registro(ficha, list(trechos))

    def buscar(self, consulta: Consulta) -> list[ResultadoBusca]:
        with self._trava:
            resultados = [
                ResultadoBusca(trecho.texto, registro.ficha.nome, _score(consulta, trecho))
                for registro in self._acervo.values()
                if registro.ficha.visibilidade == consulta.visibilidade
                for trecho in registro.trechos
            ]
        if consulta.modo == Modo.PALAVRAS:
            resultados = [resultado for resultado in resultados if resultado.score > 0]
        return sorted(resultados, key=lambda r: r.score, reverse=True)[: consulta.k]

    def listar(self) -> list[DocumentoNoAcervo]:
        with self._trava:
            fichas = [registro.ficha for registro in self._acervo.values()]
        return sorted(fichas, key=lambda ficha: ficha.criado_em, reverse=True)

    def obter(self, id: str) -> DocumentoNoAcervo | None:
        with self._trava:
            registro = self._por_id(id)
            return registro.ficha if registro else None

    def trechos_de(self, id: str) -> list[TrechoGuardado]:
        with self._trava:
            registro = self._por_id(id)
            trechos = registro.trechos if registro else []
            return [TrechoGuardado(i, t.texto, t.pagina) for i, t in enumerate(trechos)]

    def excluir(self, id: str) -> bool:
        with self._trava:
            registro = self._por_id(id)
            if registro:
                del self._acervo[registro.ficha.nome]
            return registro is not None

    def alterar_visibilidade(self, id: str, visibilidade: Visibilidade) -> bool:
        return self._mudar(id, visibilidade=visibilidade)

    def enfileirar(self, documento: Documento, conteudo: bytes) -> None:
        with self._trava:
            ficha = DocumentoNoAcervo(
                documento.id,
                documento.nome,
                documento.visibilidade,
                0,
                _agora(),
                situacao=Situacao.NA_FILA,
            )
            self._acervo[documento.nome] = _Registro(ficha, arquivo=conteudo)

    def proximo_da_fila(self) -> ArquivoNaFila | None:
        with self._trava:
            na_fila = [r for r in self._acervo.values() if r.ficha.situacao == Situacao.NA_FILA]
            if not na_fila:
                return None
            registro = min(na_fila, key=lambda r: r.ficha.criado_em)
            registro.ficha = replace(registro.ficha, situacao=Situacao.EXTRAINDO)
            ficha = registro.ficha
            documento = Documento(ficha.id, ficha.nome, ficha.visibilidade)
            return ArquivoNaFila(documento, registro.arquivo or b"")

    def registrar_andamento(self, id: str, situacao: Situacao, andamento: str | None) -> None:
        self._mudar(id, situacao=situacao, andamento=andamento)

    def concluir(self, id: str, trechos: list[Trecho], ocr: bool, paginas: int | None) -> None:
        with self._trava:
            registro = self._por_id(id)
            if registro is None:
                return  # excluído enquanto era processado
            registro.trechos = list(trechos)
            registro.arquivo = None
            registro.ficha = replace(
                registro.ficha,
                situacao=Situacao.INDEXADO,
                andamento=None,
                erro=None,
                trechos=len(trechos),
                ocr=ocr,
                paginas=paginas,
            )

    def falhar(self, id: str, erro: str) -> None:
        self._mudar(id, situacao=Situacao.FALHOU, andamento=None, erro=erro)

    def retomar_interrompidos(self) -> int:
        with self._trava:
            parados = [
                registro
                for registro in self._acervo.values()
                if registro.ficha.situacao in (Situacao.EXTRAINDO, Situacao.INDEXANDO)
            ]
            for registro in parados:
                registro.ficha = replace(registro.ficha, situacao=Situacao.NA_FILA, andamento=None)
            return len(parados)

    def guardar_avaliacao(self, dados: dict[str, Any]) -> None:
        with self._trava:
            self._avaliacoes.append(dados)

    def avaliacoes(self) -> list[dict[str, Any]]:
        with self._trava:
            return list(self._avaliacoes)

    def _por_id(self, id: str) -> _Registro | None:
        return next((r for r in self._acervo.values() if r.ficha.id == id), None)

    def _mudar(self, id: str, **campos: Any) -> bool:
        with self._trava:
            registro = self._por_id(id)
            if registro:
                registro.ficha = replace(registro.ficha, **campos)
            return registro is not None


def _agora() -> datetime:
    return datetime.now(UTC)


def _score(consulta: Consulta, trecho: Trecho) -> float:
    if consulta.modo == Modo.PALAVRAS:
        return cobertura(consulta.pergunta, trecho.texto)
    semantico = _cosseno(consulta.embedding, trecho.embedding)
    if consulta.modo == Modo.SEMANTICA:
        return semantico
    por_palavras = cobertura(consulta.pergunta, trecho.texto)
    return consulta.peso * semantico + (1 - consulta.peso) * por_palavras


def _cosseno(a: list[float], b: list[float]) -> float:
    """Semelhança de cosseno, limitada a 0..1 como manda o contrato."""
    produto = sum(x * y for x, y in zip(a, b, strict=True))
    normas = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return max(0.0, min(1.0, produto / normas)) if normas else 0.0
