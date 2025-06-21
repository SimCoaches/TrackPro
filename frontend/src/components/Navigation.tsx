import React from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Gamepad2, 
  Trophy, 
  Users, 
  Settings,
  Home
} from 'lucide-react';

interface NavigationProps {
  collapsed: boolean;
}

const navItems = [
  {
    path: '/pedals',
    icon: Gamepad2,
    label: 'Pedals',
    description: 'Calibrate your pedals'
  },
  {
    path: '/race-coach',
    icon: Trophy,
    label: 'Race Coach',
    description: 'AI coaching & telemetry'
  },
  {
    path: '/community',
    icon: Users,
    label: 'Community',
    description: 'Social features'
  },
  {
    path: '/settings',
    icon: Settings,
    label: 'Settings',
    description: 'App preferences'
  }
];

const Navigation: React.FC<NavigationProps> = ({ collapsed }) => {
  return (
    <nav className="flex-1 p-4">
      <ul className="space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          
          return (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `nav-item ${isActive ? 'active' : ''} group relative`
                }
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                
                {!collapsed && (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="flex flex-col"
                  >
                    <span className="font-medium">{item.label}</span>
                    <span className="text-xs text-dark-400 group-hover:text-dark-300 transition-colors">
                      {item.description}
                    </span>
                  </motion.div>
                )}
                
                {/* Tooltip for collapsed state */}
                {collapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-dark-700 text-white text-sm rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                    {item.label}
                  </div>
                )}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
};

export default Navigation;