import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Plain "@vercel/analytics/react" — NOT the "/next" path the Vercel dashboard
// shows by default. That one is for Next.js and fails to resolve under Vite.
import { Analytics } from '@vercel/analytics/react'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    {/* Counts page views only. It sends no document text, no visitor id, and
        nothing a person uploaded — those never leave the isolated workspace. */}
    <Analytics />
  </StrictMode>,
)
