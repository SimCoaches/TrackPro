import React from 'react';
import { motion } from 'framer-motion';
import { Wifi, WifiOff, Loader2, AlertCircle } from 'lucide-react';
import { clsx } from 'clsx';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface ConnectionStatusProps {
  status: ConnectionStatus;
  className?: string;
}

const statusConfig = {
  connected: {
    icon: Wifi,
    label: 'Connected',
    color: 'text-success-500',
    bgColor: 'bg-success-500/10 border-success-500/20',
    pulseColor: 'bg-success-500'
  },
  connecting: {
    icon: Loader2,
    label: 'Connecting...',
    color: 'text-warning-500',
    bgColor: 'bg-warning-500/10 border-warning-500/20',
    pulseColor: 'bg-warning-500'
  },
  disconnected: {
    icon: WifiOff,
    label: 'Disconnected',
    color: 'text-dark-400',
    bgColor: 'bg-dark-400/10 border-dark-400/20',
    pulseColor: 'bg-dark-400'
  },
  error: {
    icon: AlertCircle,
    label: 'Connection Error',
    color: 'text-error-500',
    bgColor: 'bg-error-500/10 border-error-500/20',
    pulseColor: 'bg-error-500'
  }
};

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ status, className }) => {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'flex items-center gap-2 px-3 py-2 rounded-lg border backdrop-blur-sm',
        config.bgColor,
        className
      )}
    >
      {/* Status indicator with pulse animation */}
      <div className="relative">
        <div className={clsx('w-2 h-2 rounded-full', config.pulseColor)} />
        {status === 'connected' && (
          <div className={clsx(
            'absolute inset-0 w-2 h-2 rounded-full animate-ping',
            config.pulseColor,
            'opacity-75'
          )} />
        )}
      </div>

      {/* Icon */}
      <Icon 
        className={clsx(
          'w-4 h-4',
          config.color,
          status === 'connecting' && 'animate-spin'
        )} 
      />

      {/* Label */}
      <span className={clsx('text-sm font-medium', config.color)}>
        {config.label}
      </span>
    </motion.div>
  );
};

export default ConnectionStatus;