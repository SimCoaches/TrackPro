import React from 'react';
import { motion } from 'framer-motion';
import { Trophy, Zap, Clock, TrendingUp } from 'lucide-react';

const RaceCoachPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Race Coach</h1>
          <p className="text-dark-400">AI-powered coaching and telemetry analysis</p>
        </div>
        <button className="btn btn-primary btn-md flex items-center gap-2">
          <Zap className="w-4 h-4" />
          Start Session
        </button>
      </div>

      {/* Connection Status */}
      <div className="card">
        <div className="card-content">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-3 h-3 bg-error-500 rounded-full"></div>
            <h3 className="font-semibold text-white">iRacing Connection</h3>
          </div>
          <p className="text-dark-300 text-sm">
            Not connected to iRacing. Launch iRacing and enter a session to begin coaching.
          </p>
        </div>
      </div>

      {/* Session Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-2">
              <Clock className="w-5 h-5 text-primary-500" />
              <span className="text-sm text-dark-400">Best Lap</span>
            </div>
            <div className="text-2xl font-bold text-white">--:--</div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-2">
              <Trophy className="w-5 h-5 text-success-500" />
              <span className="text-sm text-dark-400">Position</span>
            </div>
            <div className="text-2xl font-bold text-white">--</div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="w-5 h-5 text-warning-500" />
              <span className="text-sm text-dark-400">Improvement</span>
            </div>
            <div className="text-2xl font-bold text-white">--</div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <div className="card-content">
            <div className="flex items-center gap-3 mb-2">
              <Zap className="w-5 h-5 text-secondary-500" />
              <span className="text-sm text-dark-400">AI Coach</span>
            </div>
            <div className="text-sm text-white">Inactive</div>
          </div>
        </motion.div>
      </div>

      {/* Telemetry Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-white">Speed & Throttle</h3>
          </div>
          <div className="card-content">
            <div className="h-48 bg-dark-900 rounded-lg flex items-center justify-center border border-dark-600">
              <p className="text-dark-400">Connect to iRacing to view telemetry</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="font-semibold text-white">Brake & Steering</h3>
          </div>
          <div className="card-content">
            <div className="h-48 bg-dark-900 rounded-lg flex items-center justify-center border border-dark-600">
              <p className="text-dark-400">Connect to iRacing to view telemetry</p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Coach Panel */}
      <div className="card">
        <div className="card-header">
          <h3 className="font-semibold text-white">AI Coach Feedback</h3>
          <p className="text-sm text-dark-400">Real-time coaching suggestions and analysis</p>
        </div>
        <div className="card-content">
          <div className="bg-dark-900 rounded-lg p-4 border border-dark-600">
            <p className="text-dark-400 text-center">
              AI Coach will provide feedback once you're connected to iRacing
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RaceCoachPage;