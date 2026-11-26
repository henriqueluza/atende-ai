"""Mede a busca com um conjunto fixo de perguntas de cliente. Ver ADR 0008.

Cada pergunta diz em que documento a resposta está. A medida é em que posição um trecho
desse documento aparece na busca pública, a mesma que o atendente usa.
"""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from core_api.acervo import Acervo
from core_api.dominio import Modo, Visibilidade

PROFUNDIDADE = 10  # até onde procurar o documento certo


@dataclass(frozen=True)
class PerguntaDeTeste:
    pergunta: str
    esperado: str  # nome do documento que tem a resposta


@dataclass(frozen=True)
class PerguntaAvaliada:
    pergunta: str
    esperado: str
    posicao: int | None  # None: o documento certo não veio entre os 10 primeiros
    primeiro: str  # o documento que veio em primeiro lugar ("" se não veio nada)


def avaliar(
    acervo: Acervo,
    perguntas: list[PerguntaDeTeste],
    k: int = 3,
    modo: Modo | None = None,
    versao: str = "",
    nota: str | None = None,
) -> dict[str, Any]:
    """Roda todas as perguntas e devolve a execução pronta para guardar e mostrar."""
    modo = modo or acervo.busca.modo
    avaliadas = []
    for item in perguntas:
        resultados = acervo.buscar(item.pergunta, PROFUNDIDADE, Visibilidade.PUBLICO, modo)
        documentos = [resultado.documento for resultado in resultados]
        posicao = documentos.index(item.esperado) + 1 if item.esperado in documentos else None
        primeiro = documentos[0] if documentos else ""
        avaliadas.append(PerguntaAvaliada(item.pergunta, item.esperado, posicao, primeiro))
    total = len(avaliadas)
    acertos = sum(1 for a in avaliadas if a.posicao is not None and a.posicao <= k)
    mrr = sum(1 / a.posicao for a in avaliadas if a.posicao) / total if total else 0.0
    return {
        "data": datetime.now(UTC).isoformat(),
        "versao": versao,
        "nota": nota,
        "modo": modo.value,
        "k": k,
        "perguntas": total,
        "acertos": acertos,
        "mrr": round(mrr, 4),
        "detalhe": [asdict(avaliada) for avaliada in avaliadas],
    }
