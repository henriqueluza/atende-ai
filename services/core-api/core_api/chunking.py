"""Divide um documento em trechos pequenos o bastante para a busca. Ver ADR 0002."""

import re

TAMANHO_MAXIMO = 800


def dividir_em_trechos(texto: str, tamanho_maximo: int = TAMANHO_MAXIMO) -> list[str]:
    """Um trecho novo começa a cada título markdown ("# ") ou quando o tamanho máximo estoura.

    Parágrafos (separados por linha em branco) só são cortados quando um parágrafo sozinho
    passa do tamanho máximo, e o corte é feito num espaço. Um título nunca fica sozinho num
    trecho se houver texto depois dele: nesse caso o trecho pode passar do limite em até o
    tamanho do título.
    """
    trechos: list[str] = []
    atual = ""
    for paragrafo in _paragrafos(texto):
        if atual and _e_titulo(paragrafo):
            trechos.append(atual)
            atual = ""
        for pedaco in _cortar(paragrafo, tamanho_maximo):
            cabe = len(atual) + len(pedaco) + 2 <= tamanho_maximo
            if atual and not cabe and not _e_so_titulo(atual):
                trechos.append(atual)
                atual = ""
            atual = f"{atual}\n\n{pedaco}" if atual else pedaco
    if atual:
        trechos.append(atual)
    return trechos


def _paragrafos(texto: str) -> list[str]:
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    return [bloco.strip() for bloco in re.split(r"\n\s*\n", texto) if bloco.strip()]


def _e_titulo(paragrafo: str) -> bool:
    return re.match(r"#{1,6}\s", paragrafo) is not None


def _e_so_titulo(trecho: str) -> bool:
    return "\n" not in trecho and _e_titulo(trecho)


def _cortar(paragrafo: str, tamanho_maximo: int) -> list[str]:
    """Quebra um parágrafo grande demais, de preferência num espaço."""
    pedacos = []
    while len(paragrafo) > tamanho_maximo:
        corte = paragrafo.rfind(" ", 0, tamanho_maximo + 1)
        if corte <= 0:
            corte = tamanho_maximo
        pedacos.append(paragrafo[:corte].rstrip())
        paragrafo = paragrafo[corte:].lstrip()
    return pedacos + ([paragrafo] if paragrafo else [])
