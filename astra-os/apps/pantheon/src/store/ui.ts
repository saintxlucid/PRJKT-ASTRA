/**
 * ASTRA OS UI Store
 * Global UI state management using Zustand
 * - Layout controls (Spine collapse, Pulse visibility)
 * - Theme management (dark/light)
 * - Keyboard shortcuts
 * - View preferences
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'dark' | 'light';

export interface UIState {
  // Layout state
  collapseSpine: boolean;
  showPulse: boolean;
  spineWidth: number;
  pulseWidth: number;

  // Theme
  theme: Theme;

  // Oracle (command palette)
  oracleOpen: boolean;

  // Active view
  currentPath: string;

  // Pane layout (split view)
  splitView: boolean;
  splitRatio: number; // 0-1, percentage of primary pane

  // Preferences
  animationsEnabled: boolean;
  soundEnabled: boolean;
  compactMode: boolean;

  // Actions
  toggleSpine: () => void;
  togglePulse: () => void;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  openOracle: () => void;
  closeOracle: () => void;
  toggleOracle: () => void;
  setCurrentPath: (path: string) => void;
  toggleSplitView: () => void;
  setSplitRatio: (ratio: number) => void;
  toggleAnimations: () => void;
  toggleSound: () => void;
  toggleCompactMode: () => void;
  reset: () => void;
}

const DEFAULT_STATE = {
  collapseSpine: false,
  showPulse: true,
  spineWidth: 260,
  pulseWidth: 360,
  theme: 'dark' as Theme,
  oracleOpen: false,
  currentPath: '/aeon',
  splitView: false,
  splitRatio: 0.6,
  animationsEnabled: true,
  soundEnabled: false,
  compactMode: false,
};

export const useUI = create<UIState>()(
  persist(
    (set, get) => ({
      ...DEFAULT_STATE,

      // Toggle Spine visibility (Alt+S)
      toggleSpine: () => set((state) => ({
        collapseSpine: !state.collapseSpine,
        spineWidth: !state.collapseSpine ? 72 : 260,
      })),

      // Toggle Pulse visibility (Alt+P)
      togglePulse: () => set((state) => ({ showPulse: !state.showPulse })),

      // Set theme explicitly
      setTheme: (theme: Theme) => {
        set({ theme });
        // Apply theme to document root
        if (typeof document !== 'undefined') {
          document.documentElement.setAttribute('data-theme', theme);
        }
      },

      // Toggle between dark/light themes
      toggleTheme: () => {
        const newTheme = get().theme === 'dark' ? 'light' : 'dark';
        get().setTheme(newTheme);
      },

      // Oracle (command palette) controls (Cmd/Ctrl+K)
      openOracle: () => set({ oracleOpen: true }),
      closeOracle: () => set({ oracleOpen: false }),
      toggleOracle: () => set((state) => ({ oracleOpen: !state.oracleOpen })),

      // Navigation
      setCurrentPath: (path: string) => {
        set({ currentPath: path });
        // Close Oracle after navigation
        if (get().oracleOpen) {
          set({ oracleOpen: false });
        }
      },

      // Split view controls
      toggleSplitView: () => set((state) => ({ splitView: !state.splitView })),
      setSplitRatio: (ratio: number) => {
        // Clamp between 0.2 and 0.8
        const clampedRatio = Math.max(0.2, Math.min(0.8, ratio));
        set({ splitRatio: clampedRatio });
      },

      // Preferences
      toggleAnimations: () => set((state) => ({ animationsEnabled: !state.animationsEnabled })),
      toggleSound: () => set((state) => ({ soundEnabled: !state.soundEnabled })),
      toggleCompactMode: () => set((state) => ({ compactMode: !state.compactMode })),

      // Reset to defaults
      reset: () => set(DEFAULT_STATE),
    }),
    {
      name: 'astra-ui-store', // localStorage key
      partialize: (state) => ({
        // Only persist these fields
        collapseSpine: state.collapseSpine,
        showPulse: state.showPulse,
        theme: state.theme,
        currentPath: state.currentPath,
        splitView: state.splitView,
        splitRatio: state.splitRatio,
        animationsEnabled: state.animationsEnabled,
        soundEnabled: state.soundEnabled,
        compactMode: state.compactMode,
      }),
    }
  )
);

// Keyboard shortcut handler (to be called in App.tsx)
export function setupKeyboardShortcuts() {
  const handleKeyDown = (e: KeyboardEvent) => {
    const { toggleOracle, togglePulse, toggleSpine } = useUI.getState();

    // Cmd+K or Ctrl+K: Open Oracle
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      toggleOracle();
    }

    // Alt+P: Toggle Pulse
    if (e.altKey && e.key.toLowerCase() === 'p') {
      e.preventDefault();
      togglePulse();
    }

    // Alt+S: Toggle Spine
    if (e.altKey && e.key.toLowerCase() === 's') {
      e.preventDefault();
      toggleSpine();
    }

    // Alt+T: Toggle Theme
    if (e.altKey && e.key.toLowerCase() === 't') {
      e.preventDefault();
      useUI.getState().toggleTheme();
    }

    // Escape: Close Oracle
    if (e.key === 'Escape' && useUI.getState().oracleOpen) {
      e.preventDefault();
      useUI.getState().closeOracle();
    }
  };

  window.addEventListener('keydown', handleKeyDown);

  // Return cleanup function
  return () => window.removeEventListener('keydown', handleKeyDown);
}

// Selectors for optimized re-renders
export const selectLayout = (state: UIState) => ({
  collapseSpine: state.collapseSpine,
  showPulse: state.showPulse,
  spineWidth: state.spineWidth,
  pulseWidth: state.pulseWidth,
});

export const selectTheme = (state: UIState) => state.theme;
export const selectOracle = (state: UIState) => state.oracleOpen;
export const selectCurrentPath = (state: UIState) => state.currentPath;
export const selectSplitView = (state: UIState) => ({
  splitView: state.splitView,
  splitRatio: state.splitRatio,
});
