import '@testing-library/jest-dom';

// Mock Electron APIs
Object.defineProperty(window, 'electronAPI', {
  value: {
    getAppVersion: jest.fn().mockResolvedValue('1.0.0'),
    minimizeToTray: jest.fn().mockResolvedValue(undefined),
    showWindow: jest.fn().mockResolvedValue(undefined),
    onNavigateTo: jest.fn(),
    connectToBackend: jest.fn(),
    removeAllListeners: jest.fn()
  },
  writable: true
});

Object.defineProperty(window, 'nodeAPI', {
  value: {
    platform: 'win32',
    versions: {
      node: '20.0.0',
      chrome: '120.0.0',
      electron: '29.0.0'
    }
  },
  writable: true
});

// Mock WebSocket
global.WebSocket = jest.fn().mockImplementation(() => ({
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  send: jest.fn(),
  close: jest.fn(),
  readyState: 1
}));

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: 'div',
    aside: 'aside',
    section: 'section'
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => children
}));

// Suppress console errors during tests
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: unknown[]) => {
    if (typeof args[0] === 'string' && args[0].includes('Warning: ReactDOM.render is no longer supported')) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});