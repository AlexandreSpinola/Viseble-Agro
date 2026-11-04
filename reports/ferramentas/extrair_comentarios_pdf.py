"""Extrai comentários e realces de um PDF anotado (Edge, Acrobat Reader, Foxit, Okular).

Uso:  venv\\Scripts\\python.exe reports\\ferramentas\\extrair_comentarios_pdf.py <arquivo.pdf> [saida.md]

Para cada anotação imprime página, tipo, autor, texto do comentário e, quando for
realce/sublinhado, o trecho aproximado da página que foi marcado.
"""
import sys
from pathlib import Path

from pypdf import PdfReader


def trecho_marcado(page, annot):
    """Texto da página que cai dentro do retângulo do realce (aproximação por linhas)."""
    rect = annot.get("/Rect")
    if not rect:
        return ""
    x0, y0, x1, y1 = [float(v) for v in rect]
    linhas = []

    def visitor(text, cm, tm, font_dict, font_size):
        x, y = tm[4], tm[5]
        if y0 - 2 <= y <= y1 + 2 and text.strip():
            linhas.append(text)

    try:
        page.extract_text(visitor_text=visitor)
    except Exception:
        return ""
    return " ".join(t.strip() for t in linhas).strip()


def main(pdf, saida=None):
    reader = PdfReader(pdf)
    out = []
    n = 0
    for i, page in enumerate(reader.pages, 1):
        for a in page.get("/Annots", []) or []:
            annot = a.get_object()
            tipo = str(annot.get("/Subtype", ""))[1:]
            if tipo in ("Link", "Popup", "Widget"):
                continue
            n += 1
            autor = annot.get("/T", "")
            texto = (annot.get("/Contents", "") or "").strip()
            marcado = trecho_marcado(page, annot) if tipo in ("Highlight", "Underline", "StrikeOut", "Squiggly") else ""
            out.append(f"### {n}. Página {i}, {tipo}" + (f", {autor}" if autor else ""))
            if marcado:
                out.append(f"> trecho marcado: {marcado[:400]}")
            out.append(texto if texto else "(sem texto; só a marcação)")
            out.append("")
    texto = f"# Comentários extraídos de {Path(pdf).name}: {n} anotações\n\n" + "\n".join(out)
    if saida:
        Path(saida).write_text(texto, encoding="utf-8")
        print(f"{n} anotações gravadas em {saida}")
    else:
        print(texto)


if __name__ == "__main__":
    main(*sys.argv[1:3])
