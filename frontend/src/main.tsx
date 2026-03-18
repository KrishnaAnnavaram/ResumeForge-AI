import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#191d26',
            color: '#f0f2f7',
            border: '1px solid #252a38',
            fontFamily: "'DM Sans', sans-serif",
          },
          success: { iconTheme: { primary: '#22c55e', secondary: '#0a0b0e' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#0a0b0e' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)
