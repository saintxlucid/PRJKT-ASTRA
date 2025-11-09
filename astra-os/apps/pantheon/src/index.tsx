import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from '@tanstack/react-router';
import { QueryClientProvider } from '@tanstack/react-query';
import { router } from './routes.tsx';
import { queryClient } from './services/client';
import { setupKeyboardShortcuts } from './store/ui';
import { useNeuralSim } from './store/sim';
import './index.css';

// Set up global keyboard shortcuts
setupKeyboardShortcuts();

const root = document.getElementById('root');
if (!root) throw new Error('Root element not found');

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>
);

// Start background neural simulation as soon as app script runs
// We avoid React context to ensure it runs regardless of route.
const startSim = () => {
  try {
    // initialize store and start worker
    // Note: Zustand stores can be used outside React by accessing getState()
    const api = (useNeuralSim as any);
    if (api?.getState && api?.getState().running === false) {
      api.getState().start();
    }
  } catch (err) {
    console.warn('Neural sim failed to start:', err);
  }
};

startSim();
