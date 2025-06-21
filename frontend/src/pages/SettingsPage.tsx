import React from 'react';
import { motion } from 'framer-motion';
import { Settings, User, Bell, Palette, Database } from 'lucide-react';
import { useAppStore } from '@store/appStore';

const SettingsPage: React.FC = () => {
  const { preferences, updatePreferences, version, platform } = useAppStore();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
        <p className="text-dark-400">Configure your TrackPro preferences</p>
      </div>

      {/* Settings Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Application Settings */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card"
        >
          <div className="card-header">
            <div className="flex items-center gap-3">
              <Settings className="w-5 h-5 text-primary-500" />
              <h3 className="font-semibold text-white">Application</h3>
            </div>
          </div>
          <div className="card-content space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-white">Auto-start Backend</label>
                <p className="text-xs text-dark-400">Automatically start the Python backend</p>
              </div>
              <input
                type="checkbox"
                checked={preferences.autoStartBackend}
                onChange={(e) => updatePreferences({ autoStartBackend: e.target.checked })}
                className="w-4 h-4 text-primary-600 bg-dark-700 border-dark-600 rounded focus:ring-primary-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-white">Minimize to Tray</label>
                <p className="text-xs text-dark-400">Minimize to system tray instead of taskbar</p>
              </div>
              <input
                type="checkbox"
                checked={preferences.minimizeToTray}
                onChange={(e) => updatePreferences({ minimizeToTray: e.target.checked })}
                className="w-4 h-4 text-primary-600 bg-dark-700 border-dark-600 rounded focus:ring-primary-500"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-white">Show Notifications</label>
                <p className="text-xs text-dark-400">Display desktop notifications</p>
              </div>
              <input
                type="checkbox"
                checked={preferences.showNotifications}
                onChange={(e) => updatePreferences({ showNotifications: e.target.checked })}
                className="w-4 h-4 text-primary-600 bg-dark-700 border-dark-600 rounded focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-white mb-2 block">
                Telemetry Update Rate: {preferences.telemetryUpdateRate} Hz
              </label>
              <input
                type="range"
                min="10"
                max="120"
                step="10"
                value={preferences.telemetryUpdateRate}
                onChange={(e) => updatePreferences({ telemetryUpdateRate: parseInt(e.target.value) })}
                className="w-full h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-dark-400 mt-1">
                <span>10 Hz</span>
                <span>120 Hz</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* User Profile */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="card-header">
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-success-500" />
              <h3 className="font-semibold text-white">User Profile</h3>
            </div>
          </div>
          <div className="card-content space-y-4">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-white font-bold text-xl">U</span>
              </div>
              <p className="text-sm text-dark-400">Not signed in</p>
            </div>
            <button className="btn btn-primary btn-sm w-full">
              Sign In
            </button>
          </div>
        </motion.div>

        {/* Appearance */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="card-header">
            <div className="flex items-center gap-3">
              <Palette className="w-5 h-5 text-secondary-500" />
              <h3 className="font-semibold text-white">Appearance</h3>
            </div>
          </div>
          <div className="card-content space-y-4">
            <div>
              <label className="text-sm font-medium text-white mb-2 block">Theme</label>
              <select className="input w-full">
                <option value="dark">Dark</option>
                <option value="light" disabled>Light (Coming Soon)</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium text-white mb-2 block">Accent Color</label>
              <div className="flex gap-2">
                {['blue', 'purple', 'green', 'orange'].map((color) => (
                  <div
                    key={color}
                    className={`w-8 h-8 rounded-full cursor-pointer border-2 border-transparent hover:border-white transition-colors
                      ${color === 'blue' ? 'bg-primary-600 border-white' : ''}
                      ${color === 'purple' ? 'bg-purple-600' : ''}
                      ${color === 'green' ? 'bg-green-600' : ''}
                      ${color === 'orange' ? 'bg-orange-600' : ''}
                    `}
                  />
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* System Info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <div className="card-header">
            <div className="flex items-center gap-3">
              <Database className="w-5 h-5 text-warning-500" />
              <h3 className="font-semibold text-white">System Info</h3>
            </div>
          </div>
          <div className="card-content space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-dark-400">App Version</span>
              <span className="text-sm text-white">{version}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-dark-400">Platform</span>
              <span className="text-sm text-white">{platform}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-dark-400">Backend Status</span>
              <span className="text-sm text-error-500">Disconnected</span>
            </div>
            <div className="pt-3 border-t border-dark-600">
              <button className="btn btn-secondary btn-sm w-full">
                Check for Updates
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default SettingsPage;