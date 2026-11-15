import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Gate from './workbench/Login.jsx'
import './workbench/wb.css'

createRoot(document.getElementById('root')).render(<StrictMode><Gate /></StrictMode>)
