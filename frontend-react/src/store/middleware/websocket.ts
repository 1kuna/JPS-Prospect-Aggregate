import { StateCreator } from 'zustand';

// Define the WebSocket state and actions
export interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  socket: WebSocket | null;
  
  // Actions
  setupWebSocketListeners: () => void;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  sendMessage: (message: any) => void;
}

// Create a middleware function that adds WebSocket functionality
export const createWebSocketMiddleware = <T>(
  url: string, 
  options: { 
    onMessage?: (data: any, set: any) => void,
    onConnect?: (socket: WebSocket, set: any) => void,
    onDisconnect?: (set: any) => void,
    onError?: (error: Event, set: any) => void,
  } = {}
) => {
  return (
    config: StateCreator<T & WebSocketState>
  ): StateCreator<T & WebSocketState> => 
    (set, get, api) => {
      const webSocketState: WebSocketState = {
        connected: false,
        connecting: false,
        socket: null,
        
        // Connect to the WebSocket server
        connectWebSocket: () => {
          const state = get();
          
          // Don't connect if we're already connected or connecting
          if (state.socket || state.connecting) return;
          
          set({ connecting: true });
          
          try {
            const socket = new WebSocket(url);
            
            socket.onopen = () => {
              set({ socket, connected: true, connecting: false });
              if (options.onConnect) {
                options.onConnect(socket, set);
              }
            };
            
            socket.onclose = () => {
              set({ socket: null, connected: false, connecting: false });
              if (options.onDisconnect) {
                options.onDisconnect(set);
              }
              
              // Auto-reconnect after delay
              setTimeout(() => {
                if (!get().connected && !get().connecting) {
                  get().connectWebSocket();
                }
              }, 5000);
            };
            
            socket.onerror = (error) => {
              console.error('WebSocket error:', error);
              if (options.onError) {
                options.onError(error, set);
              }
            };
            
            socket.onmessage = (event) => {
              try {
                const data = JSON.parse(event.data);
                if (options.onMessage) {
                  options.onMessage(data, set);
                }
              } catch (error) {
                console.error('Error parsing WebSocket message:', error);
              }
            };
          } catch (error) {
            console.error('Error connecting to WebSocket:', error);
            set({ connecting: false });
          }
        },
        
        // Disconnect from the WebSocket server
        disconnectWebSocket: () => {
          const { socket } = get();
          if (socket) {
            socket.close();
            set({ socket: null, connected: false });
          }
        },
        
        // Setup WebSocket listeners
        setupWebSocketListeners: () => {
          // This is a placeholder - implementation depends on the app's needs
          // The actual listeners are set up in the connectWebSocket method
        },
        
        // Send a message through the WebSocket
        sendMessage: (message: any) => {
          const { socket, connected } = get();
          if (socket && connected) {
            socket.send(JSON.stringify(message));
          } else {
            console.warn('Cannot send message: WebSocket not connected');
          }
        }
      };
      
      return {
        ...config(set, get, api),
        ...webSocketState
      };
    };
}; 