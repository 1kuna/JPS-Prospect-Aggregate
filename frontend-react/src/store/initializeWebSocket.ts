import { io, Socket } from 'socket.io-client';
import { useStore } from './useStore';
import { createWebSocketMiddleware } from './middleware/websocketMiddleware';

let socket: Socket | null = null;

/**
 * Initialize the WebSocket connection
 * This should be called once in your app's entry point
 */
export function initializeWebSocket() {
  // Only initialize once
  if (socket) return;
  
  // Create the socket.io connection
  socket = io({
    path: '/api/socket',
    transports: ['websocket', 'polling'],
    reconnectionAttempts: 5,
    reconnectionDelay: 3000,
    timeout: 10000
  });
  
  // Log socket connection events
  socket.on('connect', () => {
    console.log('Socket connected with ID:', socket?.id);
  });
  
  socket.on('error', (error) => {
    console.error('Socket error:', error);
  });
  
  socket.on('disconnect', (reason) => {
    console.log('Socket disconnected:', reason);
  });
  
  socket.on('reconnect_attempt', (attemptNumber) => {
    console.log(`Socket reconnection attempt ${attemptNumber}`);
  });
  
  socket.on('reconnect_failed', () => {
    console.error('Socket reconnection failed');
  });
  
  // Create and apply the WebSocket middleware to the store
  const webSocketMiddleware = createWebSocketMiddleware(socket);
  
  // Add the middleware state and methods to the store
  const store = useStore.getState();
  const middlewareState = webSocketMiddleware(useStore.setState, useStore.getState);
  
  // Extend the store with the WebSocket middleware
  useStore.setState({
    ...store,
    ...middlewareState
  });
  
  // Set up the WebSocket listeners
  useStore.getState().setupWebSocketListeners();
  
  return socket;
}

/**
 * Get the socket instance once it's been initialized
 */
export function getSocket(): Socket | null {
  return socket;
}

/**
 * Send a message to the server through the WebSocket
 * @param event The event name
 * @param data The data to send
 */
export function emit(event: string, data: any) {
  if (!socket) {
    console.error('WebSocket not initialized');
    return;
  }
  
  socket.emit(event, data);
} 