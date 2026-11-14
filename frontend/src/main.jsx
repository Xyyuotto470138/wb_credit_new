import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Root from './workbench/Root.jsx'
import './workbench/wb.css'

createRoot(document.getElementById('root')).render(<StrictMode><Root /></StrictMode>)
