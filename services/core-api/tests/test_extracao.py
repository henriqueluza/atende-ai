import shutil

import pypdfium2 as pdfium
import pytest
from arquivos_de_teste import imagem, pdf_com_texto, pdf_escaneado
from core_api.extracao import ErroDeExtracao, Extrator, conferir_arquivo
from core_api.ocr import OcrFalso, OcrIndisponivel, OcrTesseract

LIDO = "Escala de novembro: Ana atende de terça a sábado."


def test_pdf_com_texto_sai_pagina_por_pagina_sem_passar_pelo_ocr():
    ocr, avisos = OcrFalso(LIDO), []
    pdf = pdf_com_texto(
        "Preços de cabelo\nCorte feminino: R$ 80.", "Preços de unhas\nManicure: R$ 35."
    )

    paginas = Extrator(ocr).extrair("precos.pdf", pdf, avisos.append)

    assert [(p.numero, p.ocr) for p in paginas] == [(1, False), (2, False)]
    assert "Corte feminino: R$ 80." in paginas[0].texto and "Manicure" in paginas[1].texto
    assert avisos == ["Lendo a página 1 de 2", "Lendo a página 2 de 2"]
    assert ocr.lidas == 0


def test_pdf_escaneado_e_imagem_passam_pelo_ocr():
    ocr = OcrFalso(LIDO)

    do_pdf = Extrator(ocr).extrair("escala.pdf", pdf_escaneado(paginas=2))
    da_foto = Extrator(ocr).extrair("quadro.jpg", imagem(formato="JPEG"))

    assert [(p.numero, p.texto, p.ocr) for p in do_pdf] == [(1, LIDO, True), (2, LIDO, True)]
    assert [(p.numero, p.texto, p.ocr) for p in da_foto] == [(1, LIDO, True)]
    assert ocr.lidas == 3


def test_sem_ocr_o_pdf_com_texto_funciona_e_o_escaneado_explica_o_motivo():
    extrator = Extrator(OcrIndisponivel())

    assert extrator.extrair("precos.pdf", pdf_com_texto("Corte feminino: R$ 80, com lavagem."))
    with pytest.raises(ErroDeExtracao, match="leitura de imagem"):
        extrator.extrair("escala.pdf", pdf_escaneado())


@pytest.mark.parametrize(
    ("nome", "conteudo", "motivo"),
    [
        ("virus.exe", b"MZ", "Formato não aceito"),
        ("vazio.pdf", b"", "vazio"),
        ("falso.pdf", b"MZ\x90\x00 isto e um executavel", "não é um PDF válido"),
        ("falso.png", imagem(formato="JPEG"), "não é um PNG válido"),
        ("quebrado.pdf", b"%PDF-1.4\nlixo", "corrompido"),
        ("quebrada.png", b"\x89PNG\r\n\x1a\nlixo", "corrompida"),
        ("em-branco.pdf", pdf_escaneado(), "Não encontrei texto"),
    ],
)
def test_arquivo_ruim_e_recusado_com_uma_frase_para_quem_enviou(nome, conteudo, motivo):
    with pytest.raises(ErroDeExtracao, match=motivo):
        Extrator(OcrFalso("")).extrair(nome, conteudo)


def test_arquivo_acima_do_limite_e_recusado_antes_de_abrir():
    with pytest.raises(ErroDeExtracao, match="20 MB"):
        conferir_arquivo("grande.pdf", b"%PDF-" + b"0" * (20 * 1024 * 1024))


def test_pdf_com_senha_pede_uma_copia_sem_senha(monkeypatch):
    def com_senha(*_):
        raise pdfium.PdfiumError("Failed to load document (PDFium: Incorrect password error).")

    monkeypatch.setattr(pdfium, "PdfDocument", com_senha)

    with pytest.raises(ErroDeExtracao, match="protegido por senha"):
        Extrator(OcrFalso("")).extrair("contrato.pdf", pdf_com_texto("qualquer"))


def test_pdf_com_paginas_demais_e_recusado(monkeypatch):
    monkeypatch.setattr("core_api.extracao.PAGINAS_MAXIMAS", 1)

    with pytest.raises(ErroDeExtracao, match="limite é 1"):
        Extrator(OcrFalso("")).extrair("longo.pdf", pdf_com_texto("um texto qualquer aqui", "dois"))


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract não instalado")
def test_tesseract_de_verdade_le_o_texto_de_uma_imagem():
    from PIL import Image, ImageDraw, ImageFont

    figura = Image.new("RGB", (900, 200), "white")
    fonte = ImageFont.load_default(size=48)
    ImageDraw.Draw(figura).text((30, 60), "Corte feminino 80 reais", fill="black", font=fonte)

    texto = OcrTesseract().ler(figura)

    assert "Corte feminino" in texto
