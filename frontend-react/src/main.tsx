import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
// import './index.css' // Old import
import './tailwind-output.css' // New import for Tailwind CLI generated styles

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
