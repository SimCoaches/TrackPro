import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '@store/appStore';
import { useWebSocketStore } from '@store/websocketStore';

// Components
import Layout from '@components/Layout';
import ErrorBoundary from '@components/ErrorBoundary';
import ConnectionStatus from '@components/ConnectionStatus';

// Pages
import PedalsPage from '@pages/PedalsPage';
import RaceCoachPage from '@pages/RaceCoachPage';
import CommunityPage from '@pages/CommunityPage';
import SettingsPage from '@pages/SettingsPage';
import LoadingPage from '@pages/LoadingPage';

function App() {
  const { isInitialized, initializeApp } = useAppStore();
  const { connect, connectionStatus } = useWebSocketStore();

  useEffect(() => {
    // Initialize the application
    initializeApp();

    // Connect to backend WebSocket
    connect('ws://localhost:8000/ws');

    // Listen for Electron navigation events
    if (window.electronAPI) {
      window.electronAPI.onNavigateTo((event: any, route: string) => {
        // Handle navigation from system tray
        window.location.hash = route;
      });
    }

    // Cleanup on unmount
    return () => {
      if (window.electronAPI) {
        window.electronAPI.removeAllListeners('navigate-to');
      }
    };
  }, [initializeApp, connect]);

  if (!isInitialized) {
    return <LoadingPage />;
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-dark-900 text-white">
        <Layout>
          <ConnectionStatus 
            status={connectionStatus} 
            className="fixed top-4 right-4 z-50" 
          />
          
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<Navigate to="/pedals" replace />} />
              <Route
                path="/pedals"
                element={
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3 }}
                  >
                    <PedalsPage />
                  </motion.div>
                }
              />
              <Route
                path="/race-coach"
                element={
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3 }}
                  >
                    <RaceCoachPage />
                  </motion.div>
                }
              />
              <Route
                path="/community"
                element={
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3 }}
                  >
                    <CommunityPage />
                  </motion.div>
                }
              />
              <Route
                path="/settings"
                element={
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3 }}
                  >
                    <SettingsPage />
                  </motion.div>
                }
              />
            </Routes>
          </AnimatePresence>
        </Layout>
      </div>
    </ErrorBoundary>
  );
}

export default App;