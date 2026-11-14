// Adapted from Phase 1 PdfViewer: page controls, fitted canvas and wide-page scrolling.
import { useEffect, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/TextLayer.css'

// Bundle locally: the saved-pack walkthrough must not load a CDN worker.
pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

export default function PdfViewer({ url, initialPage = 1 }) {
  const [pages, setPages] = useState(null)
  const [page, setPage] = useState(initialPage)
  const [width, setWidth] = useState(600)
  const [wide, setWide] = useState(false)
  const wrapper = useRef(null)
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(200, entry.contentRect.width - 32)))
    observer.observe(wrapper.current)
    return () => observer.disconnect()
  }, [])
  return <div className="pdf-viewer">
    <div className="toolbar">
      <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous page</button>
      <label>Page <input aria-label="PDF page" type="number" min="1" max={pages || 1} value={page}
        onChange={e => setPage(Math.max(1, Math.min(pages || 1, Number(e.target.value) || 1)))} /></label>
      <span>of {pages || '…'}</span>
      <button disabled={!pages || page >= pages} onClick={() => setPage(page + 1)}>Next page</button>
    </div>
    <div className="pdf-canvas" ref={wrapper}>
      <Document file={url} onLoadSuccess={({ numPages }) => { setPages(numPages); setPage(p => Math.min(p, numPages)) }}
        loading={<p>Loading source PDF…</p>} error={<p role="alert">PDF preview unavailable. Download the original for review.</p>}>
        <Page pageNumber={page} width={wide ? width * 2 : width} renderTextLayer renderAnnotationLayer={false}
          onLoadSuccess={pdfPage => { const [x0, y0, x1, y1] = pdfPage.view; setWide((x1 - x0) / (y1 - y0) > 1.3) }} />
      </Document>
    </div>
    {wide && <small>Wide source page: scroll horizontally to inspect both halves.</small>}
  </div>
}
