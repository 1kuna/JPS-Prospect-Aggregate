import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
// import './index.css' // Old import
import './tailwind-output.css' // New import for Tailwind CLI generated styles
// import { BrowserRouter } from 'react-router-dom' // Keep the import for now, or remove if not used elsewhere
import { AppProviders } from '@/contexts/AppContexts.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* <BrowserRouter> */}
      <AppProviders>
        <App />
      </AppProviders>
    {/* </BrowserRouter> */}
  </React.StrictMode>,
)
