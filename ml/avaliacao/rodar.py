"""Mede a busca com o acervo de exemplo e reprova se ela piorar. Ver ADR 0008.

    python ml/avaliacao/rodar.py                 # em memória
    python ml/avaliacao/rodar.py --banco URL     # no Postgres (APAGA o acervo desse banco)

Envia os documentos de exemplos/ e roda dois conjuntos de perguntas, nos três modos de busca:
- perguntas.jsonl: perguntas de cliente com o documento que tem a resposta. Mede se a busca
  traz esse documento entre os k primeiros (acerto) e em que posição (MRR).
- fora-do-acervo.jsonl: perguntas que o acervo público não responde. Mede quantas delas o
  atendente recusaria com o corte de score atual, em vez de responder com um trecho qualquer.

O embedder é o da configuração (EMBEDDINGS_PROVIDER); o padrão é o falso.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from agent.atendente import SCORE_MINIMO
from core_api.acervo import Acervo
from core_api.avaliacao import PerguntaDeTeste, avaliar
from core_api.config import montar_acervo
from core_api.dominio import Modo, Visibilidade

AQUI = Path(__file__).parent
EXEMPLOS = AQUI.parent.parent / "exemplos"
K = 3


def _linhas(arquivo: Path) -> list[dict]:
    return [json.loads(linha) for linha in arquivo.read_text("utf-8").splitlines() if linha.strip()]


def montar(banco: str | None) -> Acervo:
    ambiente = {chave: valor for chave, valor in os.environ.items() if chave != "DATABASE_URL"}
    if banco:
        ambiente["DATABASE_URL"] = banco
    acervo = montar_acervo(ambiente)
    for documento in acervo.listar():
        acervo.excluir(documento.id)
    for nome, visibilidade in json.loads((AQUI / "acervo.json").read_text("utf-8")).items():
        acervo.ingerir(nome, (EXEMPLOS / nome).read_text("utf-8"), Visibilidade(visibilidade))
    return acervo


def medir(acervo: Acervo, corte: float) -> dict[str, dict[str, float]]:
    perguntas = [PerguntaDeTeste(**linha) for linha in _linhas(AQUI / "perguntas.jsonl")]
    fora = [linha["pergunta"] for linha in _linhas(AQUI / "fora-do-acervo.jsonl")]
    medidas = {}
    for modo in Modo:
        execucao = avaliar(acervo, perguntas, K, modo)
        # Uma pergunta fora do acervo é recusada quando nenhum trecho passa do corte.
        recusadas = sum(
            1
            for pergunta in fora
            if not [
                r
                for r in acervo.buscar(pergunta, K, Visibilidade.PUBLICO, modo)
                if r.score >= corte
            ]
        )
        # E uma pergunta que tem resposta não pode ser recusada pelo mesmo corte.
        respondidas = sum(
            1
            for item in perguntas
            if [
                r
                for r in acervo.buscar(item.pergunta, K, Visibilidade.PUBLICO, modo)
                if r.score >= corte
            ]
        )
        medidas[modo.value] = {
            "acerto": execucao["acertos"] / execucao["perguntas"],
            "mrr": execucao["mrr"],
            "recusa_fora_do_acervo": recusadas / len(fora),
            "respondidas": respondidas / len(perguntas),
        }
    return medidas


def main() -> int:
    leitor = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    leitor.add_argument("--banco", help="URL do Postgres; sem isso, roda em memória")
    leitor.add_argument(
        "--corte", type=float, default=SCORE_MINIMO, help="score mínimo do atendente"
    )
    opcoes = leitor.parse_args()

    acervo = montar(opcoes.banco)
    medidas = medir(acervo, opcoes.corte)
    minimos = json.loads((AQUI / "minimos.json").read_text("utf-8"))

    print(
        f"Acervo de exemplo, k={K}, corte={opcoes.corte}, "
        f"padrão do servidor: {acervo.busca.modo.value}"
    )
    print(f"{'modo':<10} {'acerto':>7} {'MRR':>6} {'recusa fora':>12} {'respondidas':>12}")
    for modo, m in medidas.items():
        print(
            f"{modo:<10} {m['acerto']:>7.1%} {m['mrr']:>6.2f} "
            f"{m['recusa_fora_do_acervo']:>12.0%} {m['respondidas']:>12.0%}"
        )

    padrao = medidas[acervo.busca.modo.value]
    abaixo = [
        f"{nome} {padrao[nome]:.3f} < {minimo}"
        for nome, minimo in minimos.items()
        if padrao[nome] < minimo
    ]
    if abaixo:
        print("\nREPROVADO: o modo padrão ficou abaixo do mínimo em " + "; ".join(abaixo))
        return 1
    print("\nAprovado: o modo padrão está acima dos mínimos de ml/avaliacao/minimos.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
