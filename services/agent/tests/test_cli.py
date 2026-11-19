import os

import httpx
import pytest
from agent.atendente import Resposta
from agent.cli import ErroDeUso, carregar_env, escolher_llm, formatar, ingerir, main
from agent.llm import Fonte, LLMClaude, LLMFalso


def _core_api(responder):
    return httpx.Client(transport=httpx.MockTransport(responder), base_url="http://core-api.test")


def test_ingest_envia_nome_conteudo_e_visibilidade(tmp_path):
    arquivo = tmp_path / "faq.md"
    arquivo.write_text("## Horário\n\nDas 9h às 19h.", encoding="utf-8")
    recebidos = []

    def responder(requisicao: httpx.Request) -> httpx.Response:
        recebidos.append((requisicao.url.path, requisicao.read()))
        return httpx.Response(201, json={"nome": "faq.md", "visibilidade": "interno", "trechos": 1})

    saida = ingerir(arquivo, "interno", _core_api(responder))

    [(caminho, corpo)] = recebidos
    assert caminho == "/documentos"
    assert b'"nome":"faq.md"' in corpo and b'"visibilidade":"interno"' in corpo
    assert saida == "Documento faq.md indexado como interno: 1 trecho(s)."


def test_ingest_explica_arquivo_ilegivel_e_core_api_recusando(tmp_path):
    arquivo = tmp_path / "faq.md"
    arquivo.write_text("texto", encoding="utf-8")

    with pytest.raises(ErroDeUso, match="ler"):
        ingerir(tmp_path / "nao-existe.md", "publico", _core_api(lambda _: httpx.Response(201)))
    with pytest.raises(ErroDeUso, match="HTTP 422"):
        ingerir(arquivo, "publico", _core_api(lambda _: httpx.Response(422, json={})))


def test_ingest_sem_visibilidade_e_recusado_pela_linha_de_comando(capsys):
    with pytest.raises(SystemExit):
        main(["ingest", "faq.md"])

    assert "--visibilidade" in capsys.readouterr().err


def test_escolha_do_llm_pelo_ambiente():
    assert isinstance(escolher_llm({}), LLMFalso)
    com_chave = {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "chave-de-teste"}
    assert isinstance(escolher_llm(com_chave), LLMClaude)
    with pytest.raises(ErroDeUso, match="ANTHROPIC_API_KEY"):
        escolher_llm({"LLM_PROVIDER": "anthropic"})
    with pytest.raises(ErroDeUso, match="desconhecido"):
        escolher_llm({"LLM_PROVIDER": "outro"})


def test_saida_mostra_resposta_trecho_e_nome_do_documento():
    fonte = Fonte("## Horário\n\nDas 9h às 19h.", "faq.md", 0.714)

    saida = formatar(Resposta("Das 9h às 19h. [faq.md]", [fonte]))

    assert saida.splitlines() == [
        "Resposta:",
        "  Das 9h às 19h. [faq.md]",
        "",
        "Fontes:",
        "  [1] faq.md (score 0.71)",
        "      ## Horário",
        "      Das 9h às 19h.",
    ]


def test_env_do_arquivo_nao_sobrescreve_o_que_ja_esta_no_terminal(tmp_path, monkeypatch):
    arquivo = tmp_path / ".env"
    arquivo.write_text("# comentário\nATENDE_TESTE_A=do-arquivo\nATENDE_TESTE_B=do-arquivo\n")
    monkeypatch.setenv("ATENDE_TESTE_A", "do-terminal")
    monkeypatch.delenv("ATENDE_TESTE_B", raising=False)

    carregar_env(arquivo)

    assert os.environ["ATENDE_TESTE_A"] == "do-terminal"
    assert os.environ.pop("ATENDE_TESTE_B") == "do-arquivo"
