"""Check screenshot/PDF correspondence and render every page for visual review."""
import json
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[2]
SCREENS = ROOT / 'docs/screens'
REVIEW = ROOT / 'runtime/0024/pdf-review'
REVIEW.mkdir(parents=True, exist_ok=True)
manifest = json.loads((SCREENS / 'capture.json').read_text())
document = fitz.open(SCREENS / 'WB_Credit_screens.pdf')
assert len(document) == len(manifest['shots'])
for index, (page, shot) in enumerate(zip(document, manifest['shots']), 1):
    png = fitz.Pixmap(SCREENS / shot['filename'])
    assert (png.width, png.height) == (2880, 1800), shot['filename']
    assert tuple(page.rect) == (0, 0, 1080, 720), page.rect
    text = ' '.join(page.get_text().split())
    assert f'Screen {index:02d} of {len(document)}' in text, text
    assert ' '.join(shot['caption'].split()) in text, (index, text)
    images = page.get_image_info()
    assert len(images) == 1, (index, images)
    rect = fitz.Rect(images[0]['bbox'])
    assert page.rect.contains(rect), (index, rect)
    assert abs(rect.width / rect.height - 1.6) < 0.001, (index, rect)
    page.get_pixmap(matrix=fitz.Matrix(4 / 3, 4 / 3)).save(REVIEW / f'page-{index:02d}.png')
# Contact pages are only a QA convenience; full-resolution page renders remain available.
for start in range(0, len(document), 6):
    contact = fitz.open()
    sheet = contact.new_page(width=1440, height=1440)
    for offset in range(min(6, len(document) - start)):
        x, y = (offset % 2) * 720, (offset // 2) * 480
        sheet.show_pdf_page(fitz.Rect(x, y, x + 720, y + 480), document, start + offset)
    sheet.get_pixmap().save(REVIEW / f'contact-{start + 1:02d}.png')
    contact.close()
print(f'{len(document)} PNGs and PDF pages verified; every PDF page rendered to {REVIEW.relative_to(ROOT)}')
