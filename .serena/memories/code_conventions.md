# Code Conventions and Style Guide

## TypeScript/React Frontend
- **Strict TypeScript**: Enabled with comprehensive typing and strict mode
- **ESLint Configuration**: Using @eslint/js, typescript-eslint, react-hooks, react-refresh
- **File Structure**: Custom hooks for business logic separation from UI components
- **Naming Conventions**: 
  - Components: PascalCase (e.g., `Call.tsx`, `WebRTCDebug.tsx`)
  - Hooks: camelCase with `use` prefix (e.g., `useWebRTC.ts`, `useTranslatedSpeech.ts`)
  - Types: Defined in dedicated `src/types/` directory
- **Component Structure**: 
  - Functional components with React 19 hooks
  - Custom hooks for complex state management
  - Glassmorphism design with backdrop-blur effects
  - Accessibility-first with ARIA labels and keyboard shortcuts

## Python Backend Services
- **Framework**: FastAPI for async WebSocket services
- **Validation**: Pydantic for request/response validation
- **Logging**: Structured logging with correlation IDs for tracing
- **Architecture**: Stateless services for horizontal scalability
- **Error Handling**: Comprehensive exception handling with proper HTTP status codes

## General Patterns
- **Performance-First**: All code optimized for low-latency requirements
- **Observability**: Built-in tracing and metrics collection
- **Docker**: All services containerized with optimization configurations
- **Network Co-location**: Services placed on same network for minimal routing latency