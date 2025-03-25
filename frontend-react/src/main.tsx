import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import { queryClient } from './lib/api-client'
import { initializeWebSocket, setQueryClient } from './lib/websocket'
import './index.css'

// Initialize websocket with our queryClient instance
setQueryClient(queryClient);
initializeWebSocket();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
)
