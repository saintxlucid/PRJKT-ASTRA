/**
 * ASTRA OS Router Configuration
 * TanStack Router with typed routes and code-splitting
 * - Lazy loaded realms for optimal bundle size
 * - Type-safe navigation
 * - Nested layouts
 * - Route guards (future)
 */

import {
  createRouter,
  createRoute,
  createRootRoute,
  lazyRouteComponent,
  redirect,
} from '@tanstack/react-router';
import App from './App';

// Root route (App shell with Halo/Spine/Pulse)
const rootRoute = createRootRoute({
  component: App,
});

// Index route - redirect to AEON
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/aeon' });
  },
});

// Realm routes with lazy loading
const aeonRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/aeon',
  component: lazyRouteComponent(() => import('./realms/AEON')),
});

const aetherLoomRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/loom',
  component: lazyRouteComponent(() => import('./realms/AetherLoom')),
});

const sigilGateRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/sigil',
  component: lazyRouteComponent(() => import('./realms/SigilGate')),
});

const dreamGroveRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/grove',
  component: lazyRouteComponent(() => import('./realms/DreamGrove')),
});

const weaverRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/weaver',
  component: lazyRouteComponent(() => import('./realms/Weaver')),
});

const agentPanelRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/agent',
  component: lazyRouteComponent(() => import('./realms/AgentPanel')),
});

// System routes
const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/settings',
  component: lazyRouteComponent(() => import('./views/Settings')),
});

const logsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/logs',
  component: lazyRouteComponent(() => import('./views/Logs')),
});

// Catch-all 404 route
const notFoundRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '*',
  component: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-4">404</h1>
        <p className="text-white/60 mb-6">Realm not found</p>
        <a
          href="/aeon"
          className="px-4 py-2 bg-accent-gold hover:bg-accent-gold/80 rounded-lg transition-colors"
        >
          Return to AEON
        </a>
      </div>
    </div>
  ),
});

// Route tree
const routeTree = rootRoute.addChildren([
  indexRoute,
  aeonRoute,
  aetherLoomRoute,
  sigilGateRoute,
  dreamGroveRoute,
  weaverRoute,
  agentPanelRoute,
  settingsRoute,
  logsRoute,
  notFoundRoute,
]);

// Create router instance
export const router = createRouter({
  routeTree,
  defaultPreload: 'intent', // Preload on hover
  defaultPreloadDelay: 100, // 100ms delay before preload
  defaultStaleTime: 5000, // 5s stale time for route data
});

// Register router for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

// Route helper functions
export const routes = {
  aeon: () => '/aeon' as const,
  loom: () => '/loom' as const,
  sigil: () => '/sigil' as const,
  grove: () => '/grove' as const,
  weaver: () => '/weaver' as const,
  agent: () => '/agent' as const,
  settings: () => '/settings' as const,
  logs: () => '/logs' as const,
};

// Realm metadata
export const realmMeta = {
  aeon: {
    name: 'AEON',
    icon: '⚡',
    description: 'System pulse and metrics',
    color: 'teal',
  },
  loom: {
    name: 'Aether Loom',
    icon: '📚',
    description: 'Research and citations',
    color: 'violet',
  },
  sigil: {
    name: 'Sigil Gate',
    icon: '🔐',
    description: 'Consent and permissions',
    color: 'gold',
  },
  grove: {
    name: 'Dream Grove',
    icon: '🌳',
    description: 'Memory and knowledge',
    color: 'success',
  },
  weaver: {
    name: 'Weaver',
    icon: '🕸️',
    description: 'Job orchestration',
    color: 'amber',
  },
  agent: {
    name: 'Agent Panel',
    icon: '🤖',
    description: 'Real-time agent activity',
    color: 'blue',
  },
} as const;

export type RealmId = keyof typeof realmMeta;

// Get realm ID from path
export function getRealmIdFromPath(path: string): RealmId | null {
  if (path.startsWith('/aeon')) return 'aeon';
  if (path.startsWith('/loom')) return 'loom';
  if (path.startsWith('/sigil')) return 'sigil';
  if (path.startsWith('/grove')) return 'grove';
  if (path.startsWith('/weaver')) return 'weaver';
  if (path.startsWith('/agent')) return 'agent';
  return null;
}

export default router;
