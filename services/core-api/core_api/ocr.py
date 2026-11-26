"""Implementações de Ocr (leitura de texto em imagem). Ver ADR 0005."""

import shutil

import pytesseract
from PIL import Image

from core_api.extracao import ErroDeExtracao

TEMPO_LIMITE_POR_PAGINA = 60  # segundos


class OcrTesseract:
    """Tesseract instalado na máquina (na imagem Docker ele já vem, com português)."""

    def __init__(self, idioma: str = "por") -> None:
        self._idioma = idioma

    @staticmethod
    def disponivel() -> bool:
        return shutil.which("tesseract") is not None

    def ler(self, imagem: Image.Image) -> str:
        try:
            return pytesseract.image_to_string(
                imagem, lang=self._idioma, timeout=TEMPO_LIMITE_POR_PAGINA
            )
        except RuntimeError:  # o pytesseract usa RuntimeError para o tempo esgotado
            raise ErroDeExtracao(
                "A leitura da imagem demorou demais. Tente um arquivo menor."
            ) from None
        except (pytesseract.TesseractError, OSError) as erro:
            raise ErroDeExtracao("Não consegui ler o texto da imagem.") from erro


class OcrIndisponivel:
    """Sem Tesseract: PDF com texto continua funcionando; imagem e PDF escaneado falham."""

    def ler(self, imagem: Image.Image) -> str:
        raise ErroDeExtracao(
            "Este arquivo é uma imagem e a leitura de imagem (OCR) não está ligada neste servidor."
        )


class OcrFalso:
    """Para os testes: devolve sempre o mesmo texto, sem depender do Tesseract."""

    def __init__(self, texto: str = "") -> None:
        self.texto = texto
        self.lidas = 0

    def ler(self, imagem: Image.Image) -> str:
        self.lidas += 1
        return self.texto
