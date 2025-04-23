import React from 'react'
import ReactDOM from 'react-dom/client'
// import { QueryClientProvider, QueryClient } from '@tanstack/react-query' // Removed import
import App from './App.tsx'
// import { queryClient } from './lib/api-client'
// import { initializeWebSocket, setQueryClient } from './lib/websocket'
import './index.css'
import { BrowserRouter } from 'react-router-dom'
import { AppProviders } from './contexts/AppContexts.tsx'

// const queryClient = new QueryClient() // Removed QueryClient instance

// Initialize websocket with our queryClient instance
// setQueryClient(queryClient);
// initializeWebSocket();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* <QueryClientProvider client={queryClient}> */}
      <BrowserRouter>
        <AppProviders>
          <App />
        </AppProviders>
      </BrowserRouter>
    {/* </QueryClientProvider> */}
  </React.StrictMode>,
)
