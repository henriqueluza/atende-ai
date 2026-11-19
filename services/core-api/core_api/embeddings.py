"""Implementações de Embedder. Ver ADR 0003."""

import hashlib
import math
import re
import unicodedata

import httpx

from core_api.dominio import AcervoIndisponivel


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


class EmbedderOpenAI:
    """Embedding real, por qualquer serviço que siga o formato da API de embeddings da OpenAI."""

    def __init__(
        self,
        base_url: str,
        modelo: str,
        chave: str,
        dimensao: int,
        cliente: httpx.Client | None = None,
    ) -> None:
        self.dimensao = dimensao
        self._modelo = modelo
        self._cliente = cliente or httpx.Client(timeout=30)
        self._url = base_url.rstrip("/") + "/embeddings"
        self._cabecalhos = {"Authorization": f"Bearer {chave}"}

    def gerar(self, textos: list[str]) -> list[list[float]]:
        corpo = {"model": self._modelo, "input": textos}
        try:
            resposta = self._cliente.post(self._url, json=corpo, headers=self._cabecalhos)
            resposta.raise_for_status()
            itens = sorted(resposta.json()["data"], key=lambda item: item["index"])
            vetores = [[float(valor) for valor in item["embedding"]] for item in itens]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as erro:
            raise AcervoIndisponivel("serviço de embeddings") from erro
        if len(vetores) != len(textos) or any(len(v) != self.dimensao for v in vetores):
            raise AcervoIndisponivel(
                f"serviço de embeddings não devolveu vetores de {self.dimensao} dimensões"
            )
        return vetores
