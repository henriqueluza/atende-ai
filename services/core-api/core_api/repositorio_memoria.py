"""Repositório em memória: para testes e para rodar sem banco. Os dados somem no restart."""

from core_api.dominio import Documento, ResultadoBusca, Trecho, Visibilidade


class RepositorioMemoria:
    def __init__(self) -> None:
        self._acervo: dict[str, tuple[Documento, list[Trecho]]] = {}

    def salvar(self, documento: Documento, trechos: list[Trecho]) -> None:
        self._acervo[documento.nome] = (documento, trechos)

    def buscar(
        self, embedding: list[float], k: int, visibilidade: Visibilidade
    ) -> list[ResultadoBusca]:
        resultados = [
            ResultadoBusca(trecho.texto, documento.nome, _score(embedding, trecho.embedding))
            for documento, trechos in self._acervo.values()
            if documento.visibilidade == visibilidade
            for trecho in trechos
        ]
        return sorted(resultados, key=lambda resultado: resultado.score, reverse=True)[:k]


def _score(a: list[float], b: list[float]) -> float:
    """Semelhança de cosseno, limitada a 0..1 como manda o contrato."""
    produto = sum(x * y for x, y in zip(a, b, strict=True))
    normas = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return max(0.0, min(1.0, produto / normas)) if normas else 0.0
