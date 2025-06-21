// Global type definitions for Electron APIs
declare global {
  interface Window {
    electronAPI: {
      // App info
      getAppVersion: () => Promise<string>;
      
      // Window controls
      minimizeToTray: () => Promise<void>;
      showWindow: () => Promise<void>;
      
      // Navigation
      onNavigateTo: (callback: (event: any, route: string) => void) => void;
      
      // Backend communication
      connectToBackend: (url: string) => void;
      
      // Remove listeners
      removeAllListeners: (channel: string) => void;
    };
    
    nodeAPI: {
      platform: string;
      versions: {
        node: string;
        chrome: string;
        electron: string;
        [key: string]: string;
      };
    };
  }
}

// Backend WebSocket message types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: number;
}

// Pedal-related types
export interface PedalCalibrationData {
  throttle: number[];
  brake: number[];
  clutch: number[];
}

export interface PedalInput {
  throttle: number;
  brake: number;
  clutch: number;
  timestamp: number;
}

// Telemetry types
export interface TelemetryData {
  speed: number;
  throttle: number;
  brake: number;
  steering: number;
  gear: number;
  rpm: number;
  lapTime: number;
  sectorTimes: number[];
  timestamp: number;
}

// Race Coach types
export interface LapData {
  lapNumber: number;
  lapTime: number;
  sectorTimes: number[];
  telemetry: TelemetryData[];
  isValidLap: boolean;
}

// User types
export interface User {
  id: string;
  username: string;
  email: string;
  avatar?: string;
  xp: number;
  level: number;
}

// Community types
export interface CommunityPost {
  id: string;
  userId: string;
  username: string;
  content: string;
  timestamp: number;
  likes: number;
  comments: number;
}

export {};