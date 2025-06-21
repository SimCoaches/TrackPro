import React from 'react';
import { motion } from 'framer-motion';
import { Gamepad2, Settings, TrendingUp } from 'lucide-react';

const PedalsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Pedal Calibration</h1>
          <p className="text-dark-400">Configure and calibrate your racing pedals</p>
        </div>
        <button className="btn btn-primary btn-md flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Settings
        </button>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-3">
              <Gamepad2 className="w-5 h-5 text-primary-500" />
              <h3 className="font-semibold text-white">Hardware Status</h3>
            </div>
            <p className="text-dark-300 text-sm mb-3">
              No pedals detected. Connect your pedals to begin calibration.
            </p>
            <div className="text-xs text-dark-400">
              Supported: Logitech, Thrustmaster, Fanatec
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-3">
              <TrendingUp className="w-5 h-5 text-success-500" />
              <h3 className="font-semibold text-white">Calibration</h3>
            </div>
            <p className="text-dark-300 text-sm mb-3">
              Ready to calibrate. Connect pedals and follow the calibration wizard.
            </p>
            <div className="text-xs text-dark-400">
              Last calibrated: Never
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-3">
              <Settings className="w-5 h-5 text-warning-500" />
              <h3 className="font-semibold text-white">Profile</h3>
            </div>
            <p className="text-dark-300 text-sm mb-3">
              No active profile. Create a profile to save your calibration settings.
            </p>
            <div className="text-xs text-dark-400">
              Profiles: 0
            </div>
          </div>
        </motion.div>
      </div>

      {/* Calibration Chart Placeholder */}
      <div className="card">
        <div className="card-header">
          <h3 className="font-semibold text-white">Live Pedal Input</h3>
          <p className="text-sm text-dark-400">Real-time pedal position and curve visualization</p>
        </div>
        <div className="card-content">
          <div className="h-64 bg-dark-900 rounded-lg flex items-center justify-center border border-dark-600">
            <div className="text-center">
              <Gamepad2 className="w-12 h-12 text-dark-600 mx-auto mb-3" />
              <p className="text-dark-400">Connect pedals to view live input</p>
              <p className="text-sm text-dark-500 mt-1">
                Pedal curves and real-time data will appear here
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-4">
        <button className="btn btn-primary btn-md disabled:opacity-50" disabled>
          Start Calibration
        </button>
        <button className="btn btn-secondary btn-md disabled:opacity-50" disabled>
          Load Profile
        </button>
        <button className="btn btn-ghost btn-md disabled:opacity-50" disabled>
          Test Pedals
        </button>
      </div>
    </div>
  );
};

export default PedalsPage;