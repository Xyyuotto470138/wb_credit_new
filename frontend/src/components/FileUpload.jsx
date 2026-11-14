// Adapted from Phase 1 FileUpload: dropzone, keyboard browse and busy state.
import { useDropzone } from 'react-dropzone'

export default function FileUpload({ onFiles, busy }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: onFiles, multiple: true, disabled: busy,
  })
  return <div {...getRootProps({ className: `dropzone ${isDragActive ? 'active' : ''}`, 'aria-label': 'Choose or drop documents', 'aria-disabled': busy })}>
    <input {...getInputProps()} />
    <strong>{busy ? 'Processing documents…' : 'Drop documents here or browse files'}</strong>
    <span>PDF, Word, Excel, email, CSV or text · up to 25 MB per file</span>
    <small>Other formats are retained for manual review. You can add more files at any time.</small>
  </div>
}
