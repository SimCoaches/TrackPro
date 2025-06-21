# TrackPro Frontend

## Phase 4: Core Frontend Shell - COMPLETED ✅

This is the Electron + React frontend for TrackPro, implementing Phase 4 of the hybrid migration plan.

### Architecture

- **Electron**: Desktop application framework
- **React 18**: UI library with TypeScript
- **Zustand**: State management
- **Tailwind CSS**: Styling framework
- **Framer Motion**: Animations
- **Chart.js**: Telemetry visualization
- **Vite**: Build tool and dev server

### Features Implemented

#### 4.1 Electron Application Foundation ✅
- ✅ Electron main process with window management
- ✅ System tray integration with context menu
- ✅ Backend process spawning capability
- ✅ Auto-updater framework (placeholder)
- ✅ IPC communication between main and renderer

#### 4.2 React Component Architecture ✅
- ✅ React + TypeScript project structure
- ✅ Main application shell component
- ✅ React Router for navigation
- ✅ Zustand state management stores
- ✅ Shared component library foundation

#### 4.3 UI Framework & Styling ✅
- ✅ Dark theme with TrackPro branding
- ✅ Responsive design system
- ✅ Chart.js integration for telemetry
- ✅ Framer Motion animations
- ✅ Loading states and error boundaries

### Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Layout.tsx       # Main layout with sidebar
│   │   ├── Navigation.tsx   # Sidebar navigation
│   │   ├── ConnectionStatus.tsx  # Backend connection status
│   │   └── ErrorBoundary.tsx     # Error handling
│   ├── pages/              # Route-based page components
│   │   ├── PedalsPage.tsx
│   │   ├── RaceCoachPage.tsx
│   │   ├── CommunityPage.tsx
│   │   ├── SettingsPage.tsx
│   │   └── LoadingPage.tsx
│   ├── store/              # Zustand state stores
│   │   ├── appStore.ts     # Global app state
│   │   └── websocketStore.ts    # WebSocket communication
│   ├── types/              # TypeScript type definitions
│   │   └── global.d.ts     # Global types and Electron APIs
│   ├── App.tsx             # Main React application
│   ├── main.tsx            # React entry point
│   └── index.css           # Global styles
├── assets/                 # Static assets
│   └── tray-icon.png       # System tray icon
├── main.js                 # Electron main process
├── preload.js              # Electron preload script
├── package.json            # Dependencies and scripts
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind CSS configuration
├── tsconfig.json           # TypeScript configuration
└── jest.config.js          # Jest testing configuration
```

### Development

```bash
# Install dependencies
npm install

# Start development server (React only)
npm run dev:vite

# Start Electron app in development mode
npm run dev

# Start Electron app
npm start

# Build for production
npm run build

# Run tests
npm test

# Lint code
npm run lint
```

### WebSocket Integration

The frontend is configured to connect to the Python backend via WebSocket:
- Default connection: `ws://localhost:8000/ws`
- Automatic reconnection with exponential backoff
- Real-time message handling and subscriptions
- Connection status monitoring

### State Management

#### App Store (`appStore.ts`)
- Application initialization
- User preferences
- Theme and UI state
- Error handling

#### WebSocket Store (`websocketStore.ts`)
- Backend connection management
- Real-time message handling
- Message history and subscriptions
- Automatic reconnection logic

### Routing

- `/pedals` - Pedal calibration interface
- `/race-coach` - AI coaching and telemetry
- `/community` - Social features
- `/settings` - Application preferences

### Testing

Jest configuration with:
- React Testing Library
- TypeScript support
- Electron API mocks
- WebSocket mocks
- Framer Motion mocks

### Next Steps (Phase 5)

1. Implement actual pedal calibration functionality
2. Add real telemetry charts and AI coaching
3. Build community features
4. Connect to Python backend APIs
5. Add comprehensive testing

### Notes

- All components are placeholder implementations for Phase 4
- Real functionality will be added in Phase 5 (Feature Migration)
- Backend integration points are ready for Phase 2/3 completion
- UI/UX follows TrackPro design system with dark theme
- Responsive design works on various screen sizes