"""Tira o texto de um PDF ou de uma imagem, página por página. Ver ADR 0005.

O arquivo vem de fora e é tratado como não confiável: o tipo é conferido pelos primeiros
bytes (não pelo nome), e há limite de páginas e de tamanho de imagem.
"""

import io
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import pypdfium2 as pdfium
from PIL import Image, UnidentifiedImageError

log = logging.getLogger("core_api")

TAMANHO_MAXIMO = 20 * 1024 * 1024
PAGINAS_MAXIMAS = 200
PIXELS_MAXIMOS = 40_000_000  # uma página A4 a 300 dpi tem uns 8,7 milhões
# Página com menos texto que isso é tratada como imagem (PDF escaneado) e vai para o OCR.
TEXTO_MINIMO_POR_PAGINA = 20
ESCALA_DO_OCR = 2.0  # 144 dpi: bom para texto impresso sem gastar memória demais

Image.MAX_IMAGE_PIXELS = PIXELS_MAXIMOS

_ASSINATURAS = {
    "pdf": (b"%PDF-",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "webp": (b"RIFF",),
}


class ErroDeExtracao(Exception):
    """O arquivo não pôde ser lido. A mensagem é para quem enviou e diz o que fazer."""


@dataclass(frozen=True)
class Pagina:
    numero: int
    texto: str
    ocr: bool


class Ocr(Protocol):
    """Lê o texto de uma imagem."""

    def ler(self, imagem: Image.Image) -> str: ...


def formato_de(nome: str) -> str | None:
    """A extensão, se for de um formato que passa pela fila (PDF ou imagem)."""
    extensao = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    return extensao if extensao in _ASSINATURAS else None


def conferir_arquivo(nome: str, conteudo: bytes) -> None:
    """Recusa o que não é o que o nome diz, antes de guardar qualquer coisa."""
    formato = formato_de(nome)
    if formato is None:
        raise ErroDeExtracao("Formato não aceito. Envie PDF, PNG, JPG ou WEBP.")
    if not conteudo:
        raise ErroDeExtracao("O arquivo está vazio.")
    if len(conteudo) > TAMANHO_MAXIMO:
        raise ErroDeExtracao("Arquivo grande demais: o limite é 20 MB.")
    webp_invalido = formato == "webp" and conteudo[8:12] != b"WEBP"
    if not conteudo.startswith(_ASSINATURAS[formato]) or webp_invalido:
        raise ErroDeExtracao(f"O conteúdo do arquivo não é um {formato.upper()} válido.")


class Extrator:
    def __init__(self, ocr: Ocr) -> None:
        self._ocr = ocr

    def extrair(
        self, nome: str, conteudo: bytes, avisar: Callable[[str], None] = lambda _: None
    ) -> list[Pagina]:
        """Devolve as páginas com texto. `avisar` recebe frases como "Lendo a página 2 de 3"."""
        conferir_arquivo(nome, conteudo)
        if formato_de(nome) == "pdf":
            paginas = self._pdf(conteudo, avisar)
        else:
            avisar("Lendo o texto da imagem")
            paginas = [Pagina(1, self._ocr.ler(_abrir_imagem(conteudo)).strip(), ocr=True)]
        com_texto = [pagina for pagina in paginas if pagina.texto]
        if not com_texto:
            raise ErroDeExtracao("Não encontrei texto neste arquivo.")
        return com_texto

    def _pdf(self, conteudo: bytes, avisar: Callable[[str], None]) -> list[Pagina]:
        try:
            pdf = pdfium.PdfDocument(conteudo)
        except pdfium.PdfiumError as erro:
            if "password" in str(erro).lower():
                raise ErroDeExtracao(
                    "O PDF está protegido por senha. Envie uma cópia sem senha."
                ) from None
            raise ErroDeExtracao("O PDF está corrompido ou incompleto.") from None
        try:
            total = len(pdf)
            if total > PAGINAS_MAXIMAS:
                raise ErroDeExtracao(
                    f"O PDF tem {total} páginas e o limite é {PAGINAS_MAXIMAS}. Divida o arquivo."
                )
            paginas = []
            for indice in range(total):
                avisar(f"Lendo a página {indice + 1} de {total}")
                paginas.append(self._pagina(pdf, indice))
            return paginas
        except pdfium.PdfiumError as erro:
            log.warning("PDF ilegível no meio da leitura: %s", type(erro).__name__)
            raise ErroDeExtracao("O PDF está corrompido ou incompleto.") from None
        finally:
            pdf.close()

    def _pagina(self, pdf: pdfium.PdfDocument, indice: int) -> Pagina:
        pagina = pdf[indice]
        try:
            folha = pagina.get_textpage()
            try:
                texto = folha.get_text_bounded().replace("\r\n", "\n").replace("\r", "\n").strip()
            finally:
                folha.close()
            if len(texto) >= TEXTO_MINIMO_POR_PAGINA:
                return Pagina(indice + 1, texto, ocr=False)
            # Sem texto de verdade: a página é uma foto. Vira imagem e passa pelo OCR.
            largura, altura = pagina.get_size()
            if largura * altura * ESCALA_DO_OCR**2 > PIXELS_MAXIMOS:
                raise ErroDeExtracao(f"A página {indice + 1} é grande demais para ser lida.")
            imagem = pagina.render(scale=ESCALA_DO_OCR).to_pil()
            return Pagina(indice + 1, self._ocr.ler(imagem).strip(), ocr=True)
        finally:
            pagina.close()


def _abrir_imagem(conteudo: bytes) -> Image.Image:
    try:
        imagem = Image.open(io.BytesIO(conteudo))
        imagem.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ErroDeExtracao("A imagem está corrompida ou é grande demais.") from None
    return imagem.convert("RGB")
