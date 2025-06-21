import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

const LoadingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="text-center"
      >
        {/* Logo */}
        <div className="mb-8">
          <div className="w-24 h-24 bg-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="text-white font-bold text-3xl">TP</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">TrackPro</h1>
          <p className="text-dark-400">Racing Coach & Pedal Calibration</p>
        </div>

        {/* Loading Spinner */}
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
          <span className="text-dark-300">Initializing...</span>
        </div>

        {/* Progress Dots */}
        <div className="flex justify-center gap-2 mt-6">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 bg-primary-600 rounded-full"
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.5, 1, 0.5]
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                delay: i * 0.2
              }}
            />
          ))}
        </div>
      </motion.div>
    </div>
  );
};

export default LoadingPage;