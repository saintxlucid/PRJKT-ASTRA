/**
 * ASTRA OS App Shell
 * Top-grade UI with grid layout, typed routing, and reactive state
 */

import { Suspense, useEffect } from 'react';
import NeuralAmbient from './components/NeuralAmbient';
import { Outlet, useRouterState } from '@tanstack/react-router';
import Halo from './components/Halo';
import Spine from './components/Spine';
import Oracle from './components/Oracle';
import Pulse from './components/Pulse';
import { useUI } from './store/ui';
import { getRealmIdFromPath } from './routes.tsx';
import { watchJobs } from './services/supervisor';
import { initWebVitals } from './lib/metrics';

function App() {
  const router = useRouterState();
  const { collapseSpine, showPulse, oracleOpen, closeOracle, setCurrentPath } = useUI();

  // Get current realm from router location
  const currentPath = router.location.pathname;
  const currentRealm = getRealmIdFromPath(currentPath);

  // Initialize observability on mount
  useEffect(() => {
    // Start supervisor job watcher
    const stopWatcher = watchJobs();
    
    // Initialize Web Vitals tracking (optional)
    initWebVitals().catch(() => {
      // Silently fail if web-vitals not installed
    });
    
    return () => {
      stopWatcher();
    };
  }, []);

  // Handle navigation from Spine/Oracle
  const handleNavigate = (path: string) => {
    setCurrentPath(path);
    // Router will handle the actual navigation via <Link> or router.navigate
  };

  // Grid layout classes (CSS utilities instead of inline styles)
  const gridColsClass = collapseSpine
    ? (showPulse ? 'grid-cols-collapsed-pulse' : 'grid-cols-collapsed-no-pulse')
    : (showPulse ? 'grid-cols-expanded-pulse' : 'grid-cols-expanded-no-pulse');

  return (
  <div className="h-screen grid app-grid bg-astra text-white overflow-hidden relative">
      <NeuralAmbient />
      {/* Halo - Top bar */}
      <Halo />

      {/* Main layout grid */}
  <div className={`grid overflow-hidden ${gridColsClass}`}>
        {/* Spine - Left sidebar */}
        <Spine currentRealm={currentRealm} onNavigate={handleNavigate} />

        {/* Main content area */}
        <main className="overflow-y-auto">
          <Suspense
            fallback={
              <div className="flex items-center justify-center h-full">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-12 h-12 border-4 border-accent-teal border-t-transparent rounded-full animate-spin" />
                  <div className="text-white/60 text-sm">Loading realm...</div>
                </div>
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </main>

        {/* Pulse - Right sidebar (conditionally rendered) */}
        {showPulse && <Pulse />}
      </div>

      {/* Oracle - Command palette overlay */}
      <Oracle isOpen={oracleOpen} onClose={closeOracle} onNavigate={handleNavigate} />
    </div>
  );
}

export default App;
