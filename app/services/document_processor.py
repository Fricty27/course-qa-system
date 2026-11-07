import os
import fitz
import pdfplumber
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Callable

_splitter = RecursiveCharacterTextSplitter(
    separators=["。\n", "！\n", "？\n", "\n\n", "\n", "。", "！", "？", "；", " ", ""],
    chunk_size=600,
    chunk_overlap=100,
)

_ocr_engine = None


def _get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine


def _ocr_page_text(fitz_page) -> str:
    mat = fitz.Matrix(2, 2)
    pix = fitz_page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    result, _ = _get_ocr()(img)
    if not result:
        return ""
    return "\n".join(item[1] for item in result if item and len(item) > 1)


def process_pdf(
    file_path: str,
    course_id: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> List[Dict]:
    doc_name = os.path.basename(file_path)
    chunks = []
    fitz_doc = fitz.open(file_path)
    with pdfplumber.open(file_path) as pdf:
        total = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                try:
                    text = _ocr_page_text(fitz_doc[page_num - 1])
                except Exception:
                    pass
            if text.strip():
                for i, chunk in enumerate(_splitter.split_text(text)):
                    chunks.append({
                        "text": chunk,
                        "metadata": {
                            "course_id": course_id,
                            "doc_name": doc_name,
                            "page_num": page_num,
                            "chunk_id": f"{course_id}_{page_num}_{i}"
                        }
                    })
            if progress_callback:
                progress_callback(page_num, total)
    fitz_doc.close()
    return chunks
