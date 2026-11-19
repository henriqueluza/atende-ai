"""O critério de pronto da Etapa 1: um documento entra e o agente responde citando a fonte."""

from pathlib import Path

import pytest
from agent.atendente import responder
from agent.cli import formatar, ingerir
from agent.llm import SEM_RESPOSTA, LLMFalso

pytestmark = pytest.mark.anyio

FAQ = Path(__file__).parent.parent / "exemplos" / "faq-salao.md"


async def test_documento_ingerido_e_encontrado_e_citado_como_fonte(sistema):
    saida = ingerir(FAQ, "publico", sistema.core_api)
    assert saida == "Documento faq-salao.md indexado como publico: 7 trecho(s)."

    resposta = await responder("Qual o horário de funcionamento?", sistema.buscar, LLMFalso())

    assert "terça a sábado, das 9h às 19h" in resposta.texto
    assert resposta.texto.endswith("[faq-salao.md]")
    assert resposta.fontes[0].documento == "faq-salao.md"
    assert "## Horário de funcionamento" in resposta.fontes[0].trecho
    impresso = formatar(resposta)
    assert "Fontes:" in impresso and "[1] faq-salao.md" in impresso


async def test_cada_pergunta_encontra_a_secao_certa_do_documento(sistema):
    ingerir(FAQ, "publico", sistema.core_api)
    esperado = {
        "Quais as formas de pagamento?": "Pix",
        "Tem estacionamento?": "Rua das Acácias",
        "Qual o preço do corte feminino?": "R$ 80",
        "Como funciona o cancelamento?": "4 horas de antecedência",
    }

    for pergunta, trecho_esperado in esperado.items():
        resposta = await responder(pergunta, sistema.buscar, LLMFalso())
        assert trecho_esperado in resposta.texto, pergunta


async def test_acervo_vazio_responde_que_nao_encontrou(sistema):
    resposta = await responder("Qual o horário de funcionamento?", sistema.buscar, LLMFalso())

    assert resposta.texto == SEM_RESPOSTA
    assert resposta.fontes == []
