"""Envio de PDF e imagem, a fila de processamento e as rotas de administração do acervo."""

import pytest
from arquivos_de_teste import imagem, pdf_com_texto, pdf_escaneado
from core_api.acervo import Acervo
from core_api.dominio import AcervoIndisponivel
from core_api.embeddings import EmbedderFalso
from core_api.extracao import Extrator
from core_api.main import criar_app
from core_api.ocr import OcrFalso
from core_api.repositorio_memoria import RepositorioMemoria
from fastapi.testclient import TestClient

PRECOS = pdf_com_texto(
    "Tabela de preços de cabelo\nCorte feminino: R$ 80. Corte masculino: R$ 45.",
    "Tabela de preços de unhas\nManicure: R$ 35. Pedicure: R$ 40.",
)
LIDO_DA_FOTO = "Sobrancelha com henna custa R$ 55 no quadro de serviços."


@pytest.fixture
def acervo():
    return Acervo(RepositorioMemoria(), EmbedderFalso(64), Extrator(OcrFalso(LIDO_DA_FOTO)))


@pytest.fixture
def api(acervo):
    return TestClient(criar_app(acervo), base_url="http://localhost")


def _enviar(api, nome, conteudo, visibilidade="publico"):
    return api.post(
        "/documentos/arquivo", params={"nome": nome, "visibilidade": visibilidade}, content=conteudo
    )


def _buscar(api, pergunta, **parametros):
    resposta = api.get("/busca", params={"pergunta": pergunta, **parametros})
    return resposta.json()["resultados"]


def test_pdf_entra_na_fila_e_so_aparece_na_busca_depois_de_processado(api, acervo):
    recebido = _enviar(api, "precos.pdf", PRECOS)

    assert recebido.status_code == 202
    assert recebido.json()["situacao"] == "na_fila"
    [na_lista] = api.get("/documentos").json()["documentos"]
    assert (na_lista["situacao"], na_lista["trechos"]) == ("na_fila", 0)
    assert _buscar(api, "preço da manicure") == []

    assert acervo.processar_proximo() is True
    assert acervo.processar_proximo() is False  # fila vazia

    [pronto] = api.get("/documentos").json()["documentos"]
    assert (pronto["situacao"], pronto["trechos"], pronto["paginas"], pronto["ocr"]) == (
        "indexado",
        2,
        2,
        False,
    )
    melhor = _buscar(api, "preço da manicure")[0]
    assert melhor["documento"] == "precos.pdf" and "Manicure: R$ 35" in melhor["trecho"]


def test_detalhe_mostra_os_trechos_com_a_pagina_e_as_etapas(api, acervo):
    id = _enviar(api, "precos.pdf", PRECOS).json()["id"]

    antes = api.get(f"/documentos/{id}").json()
    acervo.processar_proximo()
    depois = api.get(f"/documentos/{id}").json()

    assert antes["trechos"] == []
    assert [p["estado"] for p in antes["passos"]] == ["feito", "pendente", "pendente", "pendente"]
    assert antes["passos"][1]["detalhe"] == "Aguardando a vez na fila"
    assert [(t["posicao"], t["pagina"]) for t in depois["trechos"]] == [(0, 1), (1, 2)]
    assert [p["estado"] for p in depois["passos"]] == ["feito"] * 4
    assert depois["passos"][2]["detalhe"] == "2 trecho(s)"
    assert api.get("/documentos/00000000-0000-4000-8000-000000000000").status_code == 404


def test_imagem_e_pdf_escaneado_sao_lidos_por_ocr(api, acervo):
    _enviar(api, "quadro.png", imagem())
    _enviar(api, "escala.pdf", pdf_escaneado(paginas=2), "interno")
    while acervo.processar_proximo():
        pass

    documentos = {d["nome"]: d for d in api.get("/documentos").json()["documentos"]}

    assert documentos["quadro.png"]["ocr"] is True and documentos["quadro.png"]["trechos"] == 1
    assert documentos["escala.pdf"]["paginas"] == 2 and documentos["escala.pdf"]["trechos"] == 2
    assert _buscar(api, "sobrancelha com henna")[0]["documento"] == "quadro.png"


def test_arquivo_que_nao_pode_ser_lido_fica_como_falhou_e_a_fila_segue(api, acervo):
    ruim = _enviar(api, "quebrado.pdf", b"%PDF-1.4\nlixo").json()["id"]
    _enviar(api, "precos.pdf", PRECOS)
    while acervo.processar_proximo():
        pass

    detalhe = api.get(f"/documentos/{ruim}").json()
    documentos = {d["nome"]: d["situacao"] for d in api.get("/documentos").json()["documentos"]}

    assert documentos == {"quebrado.pdf": "falhou", "precos.pdf": "indexado"}
    assert detalhe["documento"]["erro"] == "O PDF está corrompido ou incompleto."
    assert [p["estado"] for p in detalhe["passos"]] == ["feito", "falhou", "pendente", "pendente"]


def test_falha_do_servico_de_embeddings_no_meio_da_fila_vira_falhou_sem_derrubar(acervo, api):
    class EmbedderFora:
        dimensao = 64

        def gerar(self, textos):
            raise AcervoIndisponivel("serviço de embeddings")

    _enviar(api, "precos.pdf", PRECOS)
    acervo._embedder = EmbedderFora()

    assert acervo.processar_proximo() is True

    [documento] = api.get("/documentos").json()["documentos"]
    assert documento["situacao"] == "falhou" and "indisponível" in documento["erro"]


@pytest.mark.parametrize(
    ("nome", "conteudo", "status"),
    [
        ("planilha.xlsx", b"PK\x03\x04", 422),
        ("falso.pdf", b"MZ isto nao e pdf", 422),
        ("vazio.pdf", b"", 422),
        ("../../etc/passwd.pdf", PRECOS, 422),
        ("grande.pdf", b"%PDF-" + b"0" * (20 * 1024 * 1024), 413),
    ],
)
def test_envio_invalido_e_recusado_e_nada_entra_no_acervo(api, nome, conteudo, status):
    assert _enviar(api, nome, conteudo).status_code == status
    assert api.get("/documentos").json()["documentos"] == []


def test_visibilidade_do_arquivo_e_obrigatoria_e_o_interno_nao_vaza(api, acervo):
    sem_escolha = api.post("/documentos/arquivo", params={"nome": "precos.pdf"}, content=PRECOS)
    _enviar(api, "precos.pdf", PRECOS, "interno")
    acervo.processar_proximo()

    assert sem_escolha.status_code == 422
    assert _buscar(api, "preço da manicure") == []
    internos = _buscar(api, "preço da manicure", visibilidade="interno")
    assert internos[0]["documento"] == "precos.pdf"


def test_tornar_interno_tira_o_documento_da_busca_publica(api, acervo):
    id = _enviar(api, "precos.pdf", PRECOS).json()["id"]
    acervo.processar_proximo()

    mudou = api.patch(f"/documentos/{id}", json={"visibilidade": "interno"})

    assert mudou.status_code == 200 and mudou.json()["visibilidade"] == "interno"
    assert _buscar(api, "preço da manicure") == []
    assert api.patch(f"/documentos/{id}", json={"visibilidade": "todos"}).status_code == 422
    inexistente = "/documentos/00000000-0000-4000-8000-000000000000"
    assert api.patch(inexistente, json={"visibilidade": "interno"}).status_code == 404


def test_reenviar_o_mesmo_nome_substitui_o_documento_anterior(api, acervo):
    _enviar(api, "precos.pdf", PRECOS)
    acervo.processar_proximo()
    _enviar(api, "precos.pdf", pdf_com_texto("Tabela nova\nCorte feminino agora custa R$ 95."))

    assert _buscar(api, "corte feminino") == []  # o antigo saiu, o novo ainda está na fila
    acervo.processar_proximo()

    [documento] = api.get("/documentos").json()["documentos"]
    assert documento["trechos"] == 1
    assert "R$ 95" in _buscar(api, "corte feminino")[0]["trecho"]


def test_o_trabalhador_processa_a_fila_sozinho(acervo):
    import time

    with TestClient(criar_app(acervo, processar_fila=True), base_url="http://localhost") as api:
        _enviar(api, "precos.pdf", PRECOS)
        for _ in range(100):
            [documento] = api.get("/documentos").json()["documentos"]
            if documento["situacao"] == "indexado":
                break
            time.sleep(0.05)

    assert documento["situacao"] == "indexado"
