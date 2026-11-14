#!/bin/sh
# Render a Word file to PDF and page PNGs for visual review.
#   scripts/render_docx.sh <file.docx> <output folder>
# Uses the LibreOffice bundled with the local Codex runtime (the same renderer as earlier reviews).
set -e
R="${RENDER_RUNTIME:-$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies}"
mkdir -p "$2"
TMPDIR=/private/tmp "$R/bin/override/soffice" --headless "-env:UserInstallation=file:///private/tmp/wb_credit_lo_profile" --convert-to pdf --outdir "$2" "$1" >/dev/null 2>&1
pdf="$2/$(basename "${1%.*}").pdf"
"$R/bin/override/pdftoppm" -r 80 -png "$pdf" "$2/page"
"$R/bin/override/pdfinfo" "$pdf" | grep Pages
