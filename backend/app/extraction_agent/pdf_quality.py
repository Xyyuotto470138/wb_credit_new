"""Adapted from Phase 1 skills/claude_full_extract.py, 2026-11-10.

DBS regression diagnostic for legacy parser text. Production spreading uses B08's
PyMuPDF normalization directly; physical pages and optional clips never renumber.
"""
import re
import fitz

_FINANCIAL_NUMBER_RE = re.compile(r'\b\d[\d,]*\b')


def count_financial_numbers(text):
    return sum(1 for token in _FINANCIAL_NUMBER_RE.findall(text)
               if int(token.replace(',', '')) > 500)


def apply_text_quality_gate(content, page, candidate_text, bbox=None):
    with fitz.open(stream=content, filetype='pdf') as pdf:
        if not 1 <= page <= len(pdf):
            raise ValueError('Original PDF page is out of bounds')
        source = pdf[page - 1]
        clip = fitz.Rect(bbox) if bbox else source.rect
        if clip.is_empty or clip.is_infinite or not source.rect.contains(clip):
            raise ValueError('Invalid original-page region')
        text = source.get_text(clip=clip, sort=True)
        candidate_count, source_count = count_financial_numbers(candidate_text), count_financial_numbers(text)
        use_source = source_count >= max(1, candidate_count * 2)
        return dict(text=text if use_source else candidate_text, page=page, bbox=list(clip),
            method='pymupdf' if use_source else 'candidate',
            candidate_count=candidate_count, pymupdf_count=source_count,
            note='Parser quality diagnostic only; numeric row and column validation is still required.')
