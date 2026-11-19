"""O agente da Etapa 1: busca os trechos pelo servidor MCP e pede ao LLM a resposta."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from mcp import Client

from agent.llm import LLM, SEM_RESPOSTA, Fonte

# Abaixo disso o trecho quase não tem relação com a pergunta e só atrapalharia a resposta.
# O valor certo depende do modelo de embedding: 0.1 foi ajustado para o embedder falso.
# Ao trocar de modelo, ajuste pela variável SCORE_MINIMO (ver cli.py).
SCORE_MINIMO = 0.1

Buscar = Callable[[str, int], Awaitable[list[Fonte]]]


class ErroDeBusca(Exception):
    """O servidor MCP não conseguiu buscar. A mensagem já é própria para mostrar à pessoa."""


@dataclass(frozen=True)
class Resposta:
    texto: str
    fontes: list[Fonte]


async def responder(
    pergunta: str, buscar: Buscar, llm: LLM, k: int = 3, score_minimo: float = SCORE_MINIMO
) -> Resposta:
    fontes = [fonte for fonte in await buscar(pergunta, k) if fonte.score >= score_minimo]
    if not fontes:
        # Sem trecho relevante, nem chama o modelo: melhor dizer que não sabe do que inventar.
        return Resposta(SEM_RESPOSTA, [])
    return Resposta(llm.responder(pergunta, fontes), fontes)


def busca_por_mcp(servidor) -> Buscar:
    """`servidor` é o endereço do servidor MCP (ou, nos testes, o próprio servidor em memória).

    A única ferramenta que o agente conhece é a do contrato: buscar_conhecimento(pergunta, k).
    """

    async def buscar(pergunta: str, k: int) -> list[Fonte]:
        try:
            async with Client(servidor) as cliente:
                argumentos = {"pergunta": pergunta, "k": k}
                resultado = await cliente.call_tool("buscar_conhecimento", argumentos)
        except Exception as erro:  # o cliente MCP agrupa falhas de rede de formas variadas
            causa = type(erro).__name__  # ajuda a separar "fora do ar" de defeito no código
            raise ErroDeBusca(
                f"Não consegui falar com o servidor MCP ({causa}). Ele está no ar?"
            ) from erro
        if resultado.is_error:
            mensagens = [bloco.text for bloco in resultado.content if hasattr(bloco, "text")]
            raise ErroDeBusca(" ".join(mensagens) or "A busca falhou.")
        try:
            return [Fonte(**item) for item in resultado.structured_content["resultados"]]
        except (TypeError, KeyError) as erro:
            raise ErroDeBusca("O servidor MCP respondeu fora do contrato.") from erro

    return buscar
