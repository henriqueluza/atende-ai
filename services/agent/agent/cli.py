"""Linha de comando do agente.

python -m agent.cli ingest exemplos/faq-salao.md --visibilidade publico
python -m agent.cli ask "Qual o horário de funcionamento?"
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx

from agent.atendente import SCORE_MINIMO, ErroDeBusca, Resposta, busca_por_mcp, responder
from agent.llm import LLM, MODELO_PADRAO, ErroDoLLM, LLMClaude, LLMFalso


def main(argumentos: list[str] | None = None) -> int:
    carregar_env()
    opcoes = _ler_argumentos(argumentos)
    try:
        if opcoes.comando == "ingest":
            print(ingerir(Path(opcoes.arquivo), opcoes.visibilidade, _core_api()))
        else:
            buscar = busca_por_mcp(os.environ.get("MCP_SERVER_URL") or "http://localhost:8001/mcp")
            minimo = float(os.environ.get("SCORE_MINIMO") or SCORE_MINIMO)
            resposta = responder(opcoes.pergunta, buscar, escolher_llm(), opcoes.k, minimo)
            print(formatar(asyncio.run(resposta)))
    except (ErroDeBusca, ErroDoLLM, ErroDeUso, ValueError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    return 0


class ErroDeUso(Exception):
    """Problema que a pessoa resolve: arquivo, configuração ou serviço fora do ar."""


def ingerir(arquivo: Path, visibilidade: str, core_api: httpx.Client) -> str:
    try:
        conteudo = arquivo.read_text(encoding="utf-8-sig")  # aceita arquivo com BOM
    except (OSError, UnicodeDecodeError) as erro:
        raise ErroDeUso(f"Não consegui ler {arquivo} como texto UTF-8.") from erro
    corpo = {"nome": arquivo.name, "conteudo": conteudo, "visibilidade": visibilidade}
    try:
        resposta = core_api.post("/documentos", json=corpo)
    except httpx.HTTPError as erro:
        raise ErroDeUso("Não consegui falar com o core-api. Rodou docker compose up?") from erro
    try:
        dados = resposta.json()
    except ValueError:
        dados = {}
    if resposta.status_code != 201 or not isinstance(dados, dict):
        detalhe = dados.get("detail") if isinstance(dados, dict) else None
        motivo = f": {detalhe}" if isinstance(detalhe, str) else "."
        raise ErroDeUso(f"O core-api recusou o documento (HTTP {resposta.status_code}){motivo}")
    return (
        f"Documento {dados['nome']} indexado como {dados['visibilidade']}: "
        f"{dados['trechos']} trecho(s)."
    )


def escolher_llm(ambiente: dict[str, str] | None = None) -> LLM:
    ambiente = os.environ if ambiente is None else ambiente
    provedor = ambiente.get("LLM_PROVIDER") or "fake"
    if provedor == "fake":
        return LLMFalso()
    if provedor == "anthropic":
        if not ambiente.get("ANTHROPIC_API_KEY"):
            raise ErroDeUso("LLM_PROVIDER=anthropic exige ANTHROPIC_API_KEY no .env.")
        return LLMClaude(ambiente.get("LLM_MODEL") or MODELO_PADRAO)
    raise ErroDeUso(f"LLM_PROVIDER desconhecido: {provedor!r}. Use 'fake' ou 'anthropic'.")


def formatar(resposta: Resposta) -> str:
    linhas = ["Resposta:"] + [f"  {linha}" for linha in _sem_controle(resposta.texto).splitlines()]
    if resposta.fontes:
        linhas += ["", "Fontes:"]
    for numero, fonte in enumerate(resposta.fontes, start=1):
        linhas.append(f"  [{numero}] {_sem_controle(fonte.documento)} (score {fonte.score:.2f})")
        trecho = _sem_controle(fonte.trecho)
        linhas += [f"      {linha}" for linha in trecho.splitlines() if linha.strip()]
    return "\n".join(linhas)


def _sem_controle(texto: str) -> str:
    """Tira caracteres de controle (menos quebra de linha e tab) antes de imprimir.

    O texto vem de documentos enviados por pessoas e poderia trazer códigos que mexem no terminal.
    """
    return "".join(letra for letra in texto if letra in "\n\t" or letra.isprintable())


# Só estas variáveis são lidas do .env. Um .env desconhecido na pasta atual não consegue,
# por exemplo, desviar as chamadas da Anthropic para outro endereço.
VARIAVEIS_DO_ENV = {
    "LLM_PROVIDER",
    "LLM_MODEL",
    "ANTHROPIC_API_KEY",
    "CORE_API_URL",
    "MCP_SERVER_URL",
    "SCORE_MINIMO",
}


def carregar_env(arquivo: Path = Path(".env")) -> None:
    """Lê linhas CHAVE=valor do .env. Variável já definida no terminal tem prioridade."""
    if not arquivo.is_file():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        chave, separador, valor = linha.partition("=")
        if separador and chave.strip() in VARIAVEIS_DO_ENV:
            os.environ.setdefault(chave.strip(), valor.strip().strip("\"'"))


def _core_api() -> httpx.Client:
    return httpx.Client(
        base_url=os.environ.get("CORE_API_URL") or "http://localhost:8000", timeout=60
    )


def _ler_argumentos(argumentos: list[str] | None) -> argparse.Namespace:
    leitor = argparse.ArgumentParser(prog="python -m agent.cli", description="Agente do atende-ai")
    comandos = leitor.add_subparsers(dest="comando", required=True)
    ingest = comandos.add_parser("ingest", help="envia um documento de texto ou markdown ao acervo")
    ingest.add_argument("arquivo")
    ingest.add_argument("--visibilidade", required=True, choices=["publico", "interno"])
    ask = comandos.add_parser("ask", help="faz uma pergunta ao acervo público")
    ask.add_argument("pergunta")
    ask.add_argument(
        "-k",
        type=int,
        default=3,
        choices=range(1, 11),
        metavar="K",
        help="trechos a buscar (1 a 10)",
    )
    return leitor.parse_args(argumentos)


if __name__ == "__main__":
    sys.exit(main())
