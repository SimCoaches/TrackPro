import React from 'react';
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAppStore } from '@store/appStore';
import Navigation from './Navigation';
import { Menu, X } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { sidebarCollapsed, setSidebarCollapsed } = useAppStore();

  return (
    <div className="min-h-screen bg-dark-900 flex">
      {/* Sidebar */}
      <motion.aside
        className={`
          bg-dark-850 border-r border-dark-700 flex flex-col
          ${sidebarCollapsed ? 'w-16' : 'w-64'}
          transition-all duration-300 ease-in-out
        `}
        initial={false}
        animate={{ width: sidebarCollapsed ? 64 : 256 }}
      >
        {/* Header */}
        <div className="p-4 border-b border-dark-700">
          <div className="flex items-center justify-between">
            {!sidebarCollapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2"
              >
                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">TP</span>
                </div>
                <span className="text-white font-semibold">TrackPro</span>
              </motion.div>
            )}
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="p-2 hover:bg-dark-700 rounded-lg transition-colors"
            >
              {sidebarCollapsed ? (
                <Menu className="w-4 h-4 text-white" />
              ) : (
                <X className="w-4 h-4 text-white" />
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <Navigation collapsed={sidebarCollapsed} />

        {/* Footer */}
        <div className="mt-auto p-4 border-t border-dark-700">
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-xs text-dark-400 text-center"
            >
              TrackPro v1.0.0
            </motion.div>
          )}
        </div>
      </motion.aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Content Area */}
        <div className="flex-1 overflow-auto">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="p-6"
          >
            {children}
          </motion.div>
        </div>
      </main>
    </div>
  );
};

export default Layout;