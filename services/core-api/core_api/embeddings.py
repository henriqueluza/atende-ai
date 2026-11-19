"""Implementações de Embedder. Ver ADR 0003."""

import hashlib
import math
import re
import unicodedata


class EmbedderFalso:
    """Embedding determinístico, sem rede e sem chave de API. É o padrão do projeto.

    Cada palavra do texto soma 1 numa posição do vetor, escolhida pelo hash da palavra.
    Textos com palavras em comum ficam próximos. Não entende sinônimo nem significado:
    serve para o CI e para rodar o sistema de graça, não para medir qualidade de busca.
    """

    def __init__(self, dimensao: int = 256) -> None:
        self.dimensao = dimensao

    def gerar(self, textos: list[str]) -> list[list[float]]:
        return [self._vetor(texto) for texto in textos]

    def _vetor(self, texto: str) -> list[float]:
        vetor = [0.0] * self.dimensao
        for palavra in _palavras(texto):
            resumo = hashlib.sha256(palavra.encode()).digest()
            vetor[int.from_bytes(resumo[:4]) % self.dimensao] += 1.0
        norma = math.sqrt(sum(valor * valor for valor in vetor))
        return [valor / norma for valor in vetor] if norma else vetor


def _palavras(texto: str) -> list[str]:
    """Minúsculas, sem acento, e sem palavras de até 2 letras (o, de, a...)."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(letra for letra in sem_acento if not unicodedata.combining(letra))
    return [palavra for palavra in re.findall(r"[a-z0-9]+", sem_acento) if len(palavra) > 2]
