const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  
  // Window controls
  minimizeToTray: () => ipcRenderer.invoke('minimize-to-tray'),
  showWindow: () => ipcRenderer.invoke('show-window'),
  
  // Navigation
  onNavigateTo: (callback) => {
    ipcRenderer.on('navigate-to', callback);
  },
  
  // Backend communication (WebSocket will be handled in React)
  // These are placeholder methods for future backend communication
  connectToBackend: (url) => {
    // This will be implemented in React components using WebSocket
    console.log('Backend connection will be handled by React WebSocket client');
  },
  
  // Remove listeners
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});

// Expose a limited set of Node.js APIs
contextBridge.exposeInMainWorld('nodeAPI', {
  platform: process.platform,
  versions: process.versions
});