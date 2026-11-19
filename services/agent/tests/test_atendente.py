"""O agente contra um servidor MCP simulado: não precisa de core-api, banco nem chave."""

import pytest
from agent.atendente import ErroDeBusca, busca_por_mcp, responder
from agent.llm import SEM_RESPOSTA, LLMFalso
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel

pytestmark = pytest.mark.anyio

HORARIO = {"trecho": "## Horário\n\nDas 9h às 19h.", "documento": "faq.md", "score": 0.7}
FRACO = {"trecho": "Aceitamos Pix.", "documento": "faq.md", "score": 0.02}


class Saida(BaseModel):
    resultados: list[dict]


def _mcp_simulado(resultados=None, erro=None, chamadas=None):
    servidor = MCPServer("simulado")

    @servidor.tool()
    async def buscar_conhecimento(pergunta: str, k: int = 3) -> Saida:
        if chamadas is not None:
            chamadas.append({"pergunta": pergunta, "k": k})
        if erro:
            raise ToolError(erro)
        return Saida(resultados=resultados)

    return servidor


async def test_responde_com_o_trecho_e_cita_o_documento_como_fonte():
    chamadas = []
    buscar = busca_por_mcp(_mcp_simulado([HORARIO, FRACO], chamadas=chamadas))

    resposta = await responder("Qual o horário?", buscar, LLMFalso(), k=2)

    assert resposta.texto == "Das 9h às 19h. [faq.md]"
    assert [(f.documento, f.trecho) for f in resposta.fontes] == [("faq.md", HORARIO["trecho"])]
    assert chamadas == [{"pergunta": "Qual o horário?", "k": 2}]


@pytest.mark.parametrize("resultados", [[], [FRACO]])
async def test_sem_trecho_relevante_diz_que_nao_encontrou_e_nem_chama_o_modelo(resultados):
    class LLMQueNaoPodeSerChamado:
        def responder(self, pergunta, fontes):
            raise AssertionError("o modelo não deveria ser chamado sem fonte")

    buscar = busca_por_mcp(_mcp_simulado(resultados))

    resposta = await responder("Vocês vendem carro?", buscar, LLMQueNaoPodeSerChamado())

    assert resposta.texto == SEM_RESPOSTA
    assert resposta.fontes == []


async def test_erro_da_ferramenta_vira_erro_de_busca_com_a_mensagem_do_servidor():
    buscar = busca_por_mcp(_mcp_simulado(erro="O acervo está indisponível no momento."))

    with pytest.raises(ErroDeBusca, match="indisponível"):
        await responder("Qual o horário?", buscar, LLMFalso())


async def test_servidor_mcp_fora_do_ar_vira_erro_de_busca():
    buscar = busca_por_mcp("http://127.0.0.1:9/mcp")  # porta sem ninguém ouvindo

    with pytest.raises(ErroDeBusca, match="servidor MCP"):
        await responder("Qual o horário?", buscar, LLMFalso())


async def test_resposta_fora_do_contrato_vira_erro_de_busca():
    buscar = busca_por_mcp(_mcp_simulado([{"texto": "campo com nome errado"}]))

    with pytest.raises(ErroDeBusca, match="fora do contrato"):
        await responder("Qual o horário?", buscar, LLMFalso())


async def test_score_minimo_e_ajustavel_para_outros_modelos_de_embedding():
    buscar = busca_por_mcp(_mcp_simulado([HORARIO]))  # score 0.7

    exigente = await responder("Qual o horário?", buscar, LLMFalso(), score_minimo=0.8)

    assert exigente.texto == SEM_RESPOSTA
