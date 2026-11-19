"""Divide um documento em trechos pequenos o bastante para a busca. Ver ADR 0002."""

TAMANHO_MAXIMO = 800


def dividir_em_trechos(texto: str, tamanho_maximo: int = TAMANHO_MAXIMO) -> list[str]:
    """Um trecho novo começa a cada título markdown (#) ou quando o tamanho máximo estoura.

    Parágrafos (separados por linha em branco) nunca são cortados no meio, a não ser que um
    parágrafo sozinho passe do tamanho máximo.
    """
    trechos: list[str] = []
    atual = ""
    for paragrafo in _paragrafos(texto):
        comeca_secao = paragrafo.startswith("#")
        if atual and (comeca_secao or len(atual) + len(paragrafo) + 2 > tamanho_maximo):
            trechos.append(atual)
            atual = ""
        for pedaco in _cortar(paragrafo, tamanho_maximo):
            if atual and len(atual) + len(pedaco) + 2 > tamanho_maximo:
                trechos.append(atual)
                atual = ""
            atual = f"{atual}\n\n{pedaco}" if atual else pedaco
    if atual:
        trechos.append(atual)
    return trechos


def _paragrafos(texto: str) -> list[str]:
    blocos = texto.replace("\r\n", "\n").split("\n\n")
    return [bloco.strip() for bloco in blocos if bloco.strip()]


def _cortar(paragrafo: str, tamanho_maximo: int) -> list[str]:
    return [paragrafo[i : i + tamanho_maximo] for i in range(0, len(paragrafo), tamanho_maximo)]
