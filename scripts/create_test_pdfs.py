"""
Generate PDF test fixtures from the .txt files in tests/fixtures/.

Run from the repo root:
    python scripts/create_test_pdfs.py

Produces one .pdf for each .txt fixture so they can be uploaded via the
Streamlit UI for manual end-to-end testing. No extra dependencies beyond
requirements.txt are required.
"""

import pathlib

_FIXTURES_DIR = pathlib.Path("tests/fixtures")


def _escape_pdf_string(text: str) -> str:
    """Escape characters that are special inside a PDF string literal."""
    # Replace non-ASCII with '?' so the Type1 font can render them
    text = text.encode("ascii", errors="replace").decode("ascii")
    text = text.replace("\\", "\\\\")
    text = text.replace("(", "\\(")
    text = text.replace(")", "\\)")
    return text


def _text_to_pdf_bytes(text: str) -> bytes:
    """Build a minimal single-page PDF containing the given plain text.

    Uses Helvetica (built-in Type1 font) so pypdf can extract the text
    without needing an embedded font subset.
    """
    lines = text.splitlines()

    # --- Content stream ---
    stream_parts = [
        "BT",
        "/F1 11 Tf",
        "14 TL",       # text leading (line spacing) = 14 pt
        "50 770 Td",   # start position: left margin 50, near top of page
    ]
    for line in lines:
        stream_parts.append(f"({_escape_pdf_string(line)}) Tj")
        stream_parts.append("T*")  # advance to next line using TL
    stream_parts.append("ET")

    content = "\n".join(stream_parts).encode("latin-1")
    content_len = len(content)

    # --- PDF object bodies ---
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R\n"
        b"   /Resources << /Font << /F1 5 0 R >> >> >>\n"
        b"endobj\n"
    )
    obj4 = (
        f"4 0 obj\n<< /Length {content_len} >>\nstream\n".encode()
        + content
        + b"\nendstream\nendobj\n"
    )
    obj5 = (
        b"5 0 obj\n"
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica\n"
        b"   /Encoding /WinAnsiEncoding >>\n"
        b"endobj\n"
    )

    objects = [obj1, obj2, obj3, obj4, obj5]

    # --- Body + cross-reference table + trailer ---
    header = b"%PDF-1.4\n"
    pos = len(header)
    offsets: list[int] = []
    body = b""
    for obj in objects:
        offsets.append(pos)
        body += obj
        pos += len(obj)

    xref_offset = pos
    xref_entries = "0000000000 65535 f \n"
    for off in offsets:
        xref_entries += f"{off:010d} 00000 n \n"

    xref = f"xref\n0 {len(objects) + 1}\n{xref_entries}".encode()
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()

    return header + body + xref + trailer


def main() -> None:
    txt_files = sorted(_FIXTURES_DIR.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {_FIXTURES_DIR}")
        return

    for txt_path in txt_files:
        pdf_path = txt_path.with_suffix(".pdf")
        text = txt_path.read_text(encoding="utf-8")
        pdf_bytes = _text_to_pdf_bytes(text)
        pdf_path.write_bytes(pdf_bytes)
        print(f"  {pdf_path.name}  ({len(pdf_bytes):,} bytes)")

    print(f"\n{len(txt_files)} PDF(s) created in {_FIXTURES_DIR}/")
    print("Upload these via the Streamlit UI at http://localhost:8501")


if __name__ == "__main__":
    main()
