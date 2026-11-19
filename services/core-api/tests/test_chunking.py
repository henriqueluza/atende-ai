from core_api.chunking import dividir_em_trechos


def test_cada_titulo_markdown_comeca_um_trecho():
    texto = "# FAQ\n\n## Horário\n\nDas 9h às 19h.\n\n## Preço\n\nCorte: R$ 50."

    assert dividir_em_trechos(texto) == [
        "# FAQ",
        "## Horário\n\nDas 9h às 19h.",
        "## Preço\n\nCorte: R$ 50.",
    ]


def test_texto_longo_e_dividido_sem_passar_do_tamanho_maximo():
    texto = "\n\n".join(["palavra " * 10] * 5) + "\n\n" + "x" * 250

    trechos = dividir_em_trechos(texto, tamanho_maximo=100)

    assert len(trechos) > 1
    assert all(len(trecho) <= 100 for trecho in trechos)
    assert "".join(trechos).count("x") == 250


def test_texto_so_com_espacos_nao_gera_trecho():
    assert dividir_em_trechos("  \n\n \n") == []


def test_titulo_nao_fica_sozinho_quando_o_paragrafo_seguinte_e_grande():
    texto = "# Contrato\n\n" + "palavra " * 99  # o parágrafo quase enche o limite sozinho

    trechos = dividir_em_trechos(texto)

    assert len(trechos) == 1
    assert trechos[0].startswith("# Contrato\n\npalavra")


def test_paragrafo_grande_e_cortado_em_espaco_e_nao_no_meio_da_palavra():
    trechos = dividir_em_trechos("abcdefghi " * 30, tamanho_maximo=25)

    assert all(set(trecho.split()) == {"abcdefghi"} for trecho in trechos)
    assert sum(len(trecho.split()) for trecho in trechos) == 30


def test_linha_em_branco_com_espacos_separa_e_hashtag_nao_e_titulo():
    assert dividir_em_trechos("um\n \ndois\r\rtrês", tamanho_maximo=4) == ["um", "dois", "três"]
    assert dividir_em_trechos("Promoção\n\n#oferta do dia") == ["Promoção\n\n#oferta do dia"]
