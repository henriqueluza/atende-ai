"""Fabrica PDFs e imagens pequenos para os testes, sem depender de arquivo guardado."""

import io

from PIL import Image, ImageDraw


def pdf_com_texto(*paginas: str) -> bytes:
    """Um PDF de verdade, com uma página de texto para cada argumento (linhas separadas por \\n)."""
    objetos: list[bytes] = []
    filhos = " ".join(f"{4 + 2 * i} 0 R" for i in range(len(paginas)))
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append(f"<< /Type /Pages /Kids [{filhos}] /Count {len(paginas)} >>".encode())
    objetos.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    for indice, texto in enumerate(paginas):
        linhas = [
            linha.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            for linha in texto.split("\n")
        ]
        desenho = "BT /F1 12 Tf 14 TL 72 760 Td " + " T* ".join(f"({linha}) Tj" for linha in linhas)
        fluxo = (desenho + " ET").encode("cp1252")
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * indice} 0 R >>".encode()
        )
        objetos.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(fluxo), fluxo))
    saida = io.BytesIO()
    saida.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posicoes = []
    for numero, corpo in enumerate(objetos, start=1):
        posicoes.append(saida.tell())
        saida.write(b"%d 0 obj\n%s\nendobj\n" % (numero, corpo))
    inicio_da_tabela = saida.tell()
    saida.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1))
    for posicao in posicoes:
        saida.write(b"%010d 00000 n \n" % posicao)
    saida.write(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objetos) + 1, inicio_da_tabela)
    )
    return saida.getvalue()


def imagem(texto: str = "Corte feminino R$ 80", formato: str = "PNG") -> bytes:
    figura = Image.new("RGB", (640, 200), "white")
    ImageDraw.Draw(figura).text((20, 80), texto, fill="black")
    saida = io.BytesIO()
    figura.save(saida, formato)
    return saida.getvalue()


def pdf_escaneado(paginas: int = 1) -> bytes:
    """Um PDF sem texto nenhum: cada página é só uma foto, como sai de um scanner."""
    figuras = [Image.new("RGB", (400, 560), "white") for _ in range(paginas)]
    saida = io.BytesIO()
    figuras[0].save(saida, "PDF", save_all=True, append_images=figuras[1:])
    return saida.getvalue()
