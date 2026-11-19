from core_api.embeddings import EmbedderFalso


def _semelhanca(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_mesmo_texto_gera_sempre_o_mesmo_vetor():
    embedder = EmbedderFalso()

    assert embedder.gerar(["Horário de funcionamento"]) == embedder.gerar(
        ["Horário de funcionamento"]
    )
    assert len(embedder.gerar(["oi mundo"])[0]) == embedder.dimensao


def test_texto_com_palavras_em_comum_fica_mais_proximo():
    pergunta, horario, preco = EmbedderFalso().gerar(
        [
            "Qual o horario de funcionamento?",
            "Horário de funcionamento: terça a sábado, das 9h às 19h.",
            "Corte feminino custa R$ 80 e escova R$ 50.",
        ]
    )

    assert _semelhanca(pergunta, horario) > _semelhanca(pergunta, preco)
