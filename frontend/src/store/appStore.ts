import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface AppState {
  // App initialization
  isInitialized: boolean;
  initializeApp: () => Promise<void>;
  
  // Theme and UI
  theme: 'dark' | 'light';
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  
  // User preferences
  preferences: {
    autoStartBackend: boolean;
    minimizeToTray: boolean;
    showNotifications: boolean;
    telemetryUpdateRate: number;
  };
  updatePreferences: (prefs: Partial<AppState['preferences']>) => void;
  
  // App version and info
  version: string;
  platform: string;
  
  // Error handling
  error: string | null;
  setError: (error: string | null) => void;
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        isInitialized: false,
        theme: 'dark',
        sidebarCollapsed: false,
        preferences: {
          autoStartBackend: true,
          minimizeToTray: true,
          showNotifications: true,
          telemetryUpdateRate: 60, // Hz
        },
        version: '1.0.0',
        platform: typeof window !== 'undefined' ? window.nodeAPI?.platform || 'unknown' : 'unknown',
        error: null,

        // Actions
        initializeApp: async () => {
          try {
            // Get app version from Electron
            if (window.electronAPI) {
              const version = await window.electronAPI.getAppVersion();
              set({ version });
            }

            // Set platform info
            if (window.nodeAPI) {
              set({ platform: window.nodeAPI.platform });
            }

            // Initialize complete
            set({ isInitialized: true, error: null });
          } catch (error) {
            console.error('Failed to initialize app:', error);
            set({ error: error instanceof Error ? error.message : 'Failed to initialize app' });
          }
        },

        setSidebarCollapsed: (collapsed) => {
          set({ sidebarCollapsed: collapsed });
        },

        updatePreferences: (prefs) => {
          set((state) => ({
            preferences: { ...state.preferences, ...prefs }
          }));
        },

        setError: (error) => {
          set({ error });
        },
      }),
      {
        name: 'trackpro-app-store',
        partialize: (state) => ({
          preferences: state.preferences,
          sidebarCollapsed: state.sidebarCollapsed,
          theme: state.theme,
        }),
      }
    ),
    {
      name: 'TrackPro App Store',
    }
  )
);