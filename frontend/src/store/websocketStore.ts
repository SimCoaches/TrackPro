import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: number;
}

interface WebSocketState {
  // Connection state
  ws: WebSocket | null;
  connectionStatus: ConnectionStatus;
  reconnectAttempts: number;
  lastError: string | null;
  
  // Message handling
  lastMessage: WebSocketMessage | null;
  messageHistory: WebSocketMessage[];
  
  // Actions
  connect: (url: string) => void;
  disconnect: () => void;
  sendMessage: (type: string, data: any) => void;
  
  // Message subscribers
  subscribers: Map<string, Set<(data: any) => void>>;
  subscribe: (messageType: string, callback: (data: any) => void) => () => void;
}

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 2000;

export const useWebSocketStore = create<WebSocketState>()(
  devtools(
    (set, get) => ({
      // Initial state
      ws: null,
      connectionStatus: 'disconnected',
      reconnectAttempts: 0,
      lastError: null,
      lastMessage: null,
      messageHistory: [],
      subscribers: new Map(),

      // Actions
      connect: (url: string) => {
        const { ws, connectionStatus } = get();
        
        // Don't connect if already connected or connecting
        if (ws && (connectionStatus === 'connected' || connectionStatus === 'connecting')) {
          return;
        }

        set({ connectionStatus: 'connecting', lastError: null });

        try {
          const websocket = new WebSocket(url);

          websocket.onopen = () => {
            console.log('WebSocket connected');
            set({ 
              connectionStatus: 'connected', 
              reconnectAttempts: 0,
              lastError: null 
            });
          };

          websocket.onmessage = (event) => {
            try {
              const message: WebSocketMessage = {
                ...JSON.parse(event.data),
                timestamp: Date.now()
              };

              // Update state
              set((state) => ({
                lastMessage: message,
                messageHistory: [...state.messageHistory.slice(-99), message] // Keep last 100 messages
              }));

              // Notify subscribers
              const { subscribers } = get();
              const callbacks = subscribers.get(message.type);
              if (callbacks) {
                callbacks.forEach(callback => {
                  try {
                    callback(message.data);
                  } catch (error) {
                    console.error('Error in message callback:', error);
                  }
                });
              }
            } catch (error) {
              console.error('Error parsing WebSocket message:', error);
            }
          };

          websocket.onclose = () => {
            console.log('WebSocket disconnected');
            set({ connectionStatus: 'disconnected', ws: null });
            
            // Attempt to reconnect
            const { reconnectAttempts } = get();
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
              setTimeout(() => {
                set((state) => ({ reconnectAttempts: state.reconnectAttempts + 1 }));
                get().connect(url);
              }, RECONNECT_DELAY * (reconnectAttempts + 1)); // Exponential backoff
            }
          };

          websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            set({ 
              connectionStatus: 'error', 
              lastError: 'Connection failed' 
            });
          };

          set({ ws: websocket });
        } catch (error) {
          console.error('Failed to create WebSocket:', error);
          set({ 
            connectionStatus: 'error', 
            lastError: error instanceof Error ? error.message : 'Failed to connect' 
          });
        }
      },

      disconnect: () => {
        const { ws } = get();
        if (ws) {
          ws.close();
          set({ ws: null, connectionStatus: 'disconnected' });
        }
      },

      sendMessage: (type: string, data: any) => {
        const { ws, connectionStatus } = get();
        
        if (!ws || connectionStatus !== 'connected') {
          console.warn('Cannot send message: WebSocket not connected');
          return;
        }

        try {
          const message = {
            type,
            data,
            timestamp: Date.now()
          };
          ws.send(JSON.stringify(message));
        } catch (error) {
          console.error('Error sending WebSocket message:', error);
          set({ lastError: 'Failed to send message' });
        }
      },

      subscribe: (messageType: string, callback: (data: any) => void) => {
        const { subscribers } = get();
        
        if (!subscribers.has(messageType)) {
          subscribers.set(messageType, new Set());
        }
        
        subscribers.get(messageType)!.add(callback);

        // Return unsubscribe function
        return () => {
          const callbacks = subscribers.get(messageType);
          if (callbacks) {
            callbacks.delete(callback);
            if (callbacks.size === 0) {
              subscribers.delete(messageType);
            }
          }
        };
      },
    }),
    {
      name: 'TrackPro WebSocket Store',
    }
  )
);