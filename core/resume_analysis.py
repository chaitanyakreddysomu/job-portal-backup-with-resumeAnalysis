import os
import re
import io
from typing import Tuple

import fitz  # PyMuPDF
from PyPDF2 import PdfReader
# from pdfminer.high_level import extract_text as pdfminer_extract_text
from PIL import Image
import pytesseract
from sentence_transformers import SentenceTransformer, util


# Initialize SBERT model once for similarity calculations
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)


# Regex Patterns
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\-\s()]{7,}\d)")
YEAR_RANGE_RE = re.compile(r"(20\d{2}\s*[-–]\s*20\d{2})")
YEAR_SINGLE_RE = re.compile(r"(20\d{2})")
BULLET_RE = re.compile(r"(^|\n)\s*[\-\•\●\▪\▶\*]\s+", re.MULTILINE)

# Resume section headers & keywords
POS_SECTION_HEADERS = {
    "education", "work experience", "experience", "professional experience",
    "projects", "skills", "technical skills", "summary", "profile",
    "certifications", "achievements", "publications", "responsibilities",
    "languages", "interests"
}
DEGREE_KEYWORDS = {
    "b.e", "btech", "b.tech", "mtech", "m.tech", "bsc", "b.sc",
    "msc", "m.sc", "mba", "bca", "mca", "phd"
}
NEG_KEYWORDS = {
    "offer", "invoice", "policy", "quotation", "purchase order", "receipt",
    "terms and conditions", "agreement", "nda", "contract", "gst", "bill to",
    "ship to", "tax", "pan", "aadhaar", "bank account"
}


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF byte stream using multiple methods.
    """
    text = ""

    # 1. PyMuPDF (fitz)
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract_text
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        if text.strip():
            return text
    except Exception as e:
        print(f"[WARN] PyMuPDF extraction failed: {e}")

    # 2. pdfminer.six
    try:
        with io.BytesIO(pdf_bytes) as buffer:
            text = pdfminer_extract_text(buffer)
        if text and text.strip():
            return text
    except Exception as e:
        print(f"[WARN] pdfminer.six extraction failed: {e}")

    # 3. PyPDF2
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(text_parts).strip()
        if text.strip():
            return text
    except Exception as e:
        print(f"[WARN] PyPDF2 extraction failed: {e}")

    # 4. OCR fallback using Tesseract
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        ocr_texts = []
        for page in doc:
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_text = pytesseract.image_to_string(img)
            ocr_texts.append(ocr_text)
        doc.close()
        text = "\n".join(ocr_texts).strip()
        if text.strip():
            return text
    except Exception as e:
        print(f"[ERROR] OCR extraction failed: {e}")

    return text.strip()


def extract_metadata_text(pdf_path: str) -> str:
    """
    Extract metadata text from PDF file.
    """
    try:
        reader = PdfReader(pdf_path)
        meta = reader.metadata
        if not meta:
            return ""
        return " ".join(str(v) for v in meta.values() if v)
    except Exception:
        return ""


def _count_bullets(text: str) -> int:
    return len(BULLET_RE.findall(text))


def _is_contact_list_like(text: str, section_hits: int, degree_hits: int) -> bool:
    """
    Avoid misclassifying contact lists as resumes.
    """
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    return len(emails) >= 5 and len(phones) >= 5 and section_hits == 0 and degree_hits == 0


def looks_like_resume(text: str) -> Tuple[bool, str, bool]:
    """
    Heuristic to determine if text resembles a resume.
    Returns (is_resume: bool, note: str, has_negatives: bool)
    """
    if not text:
        return False, "Empty or unreadable PDF.", False

    t = text.lower()
    words = len(t.split())
    if words < 50:
        return False, "Too little text to be a resume.", False

    has_email = EMAIL_RE.search(t) is not None
    has_phone = PHONE_RE.search(t) is not None
    section_hits = sum(1 for s in POS_SECTION_HEADERS if s in t)
    degree_hits = sum(1 for d in DEGREE_KEYWORDS if d in t)

    if _is_contact_list_like(t, section_hits, degree_hits):
        return False, "Looks like a contacts/directory list, not a resume.", False

    has_bullets = _count_bullets(text) >= 1
    has_year_range = YEAR_RANGE_RE.search(t) is not None
    has_enough_years = len(YEAR_SINGLE_RE.findall(t)) >= 1

    neg_hits = sum(1 for k in NEG_KEYWORDS if k in t)
    has_negatives = neg_hits > 0

    if (has_email or has_phone) and (section_hits >= 1 or degree_hits >= 1 or has_year_range or has_enough_years):
        return True, "Looks like a resume.", has_negatives

    return False, "Does not match resume structure.", has_negatives


def sbert_similarity_percent(jd: str, resume_text: str) -> float:
    """
    Compute semantic similarity percentage between job description and resume text.
    """
    job_emb = model.encode(jd, normalize_embeddings=True)
    res_emb = model.encode(resume_text, normalize_embeddings=True)
    sim = float(util.cos_sim(job_emb, res_emb)[0][0])
    return round(max(0.0, min(1.0, sim)) * 100.0, 2)


