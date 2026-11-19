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
