/**
 * Settings View
 * User preferences and configuration
 */

import { useUI } from '../store/ui';

export default function Settings() {
  const {
    theme,
    animationsEnabled,
    soundEnabled,
    compactMode,
    toggleTheme,
    toggleAnimations,
    toggleSound,
    toggleCompactMode,
  } = useUI();

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="text-3xl font-bold mb-2">Settings ⚙️</h1>
      <p className="text-white/60 mb-8">Configure your ASTRA OS experience</p>

      {/* Appearance */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Appearance</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-astra-panel rounded-xl border border-white/10">
            <div>
              <div className="font-medium">Theme</div>
              <div className="text-sm text-white/60">
                Current: {theme === 'dark' ? 'Dark (Obsidian)' : 'Light'}
              </div>
            </div>
            <button
              onClick={toggleTheme}
              className="px-4 py-2 bg-accent-violet hover:bg-accent-violet/80 rounded-lg transition-colors"
            >
              Toggle Theme
            </button>
          </div>

          <div className="flex items-center justify-between p-4 bg-astra-panel rounded-xl border border-white/10">
            <div>
              <div className="font-medium">Compact Mode</div>
              <div className="text-sm text-white/60">Reduce spacing and padding</div>
            </div>
            <button
              onClick={toggleCompactMode}
              className={`px-4 py-2 rounded-lg transition-colors ${
                compactMode
                  ? 'bg-status-success hover:bg-status-success/80'
                  : 'bg-white/10 hover:bg-white/20'
              }`}
            >
              {compactMode ? 'Enabled' : 'Disabled'}
            </button>
          </div>
        </div>
      </section>

      {/* Behavior */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold mb-4">Behavior</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-astra-panel rounded-xl border border-white/10">
            <div>
              <div className="font-medium">Animations</div>
              <div className="text-sm text-white/60">
                Enable smooth transitions and effects
              </div>
            </div>
            <button
              onClick={toggleAnimations}
              className={`px-4 py-2 rounded-lg transition-colors ${
                animationsEnabled
                  ? 'bg-status-success hover:bg-status-success/80'
                  : 'bg-white/10 hover:bg-white/20'
              }`}
            >
              {animationsEnabled ? 'Enabled' : 'Disabled'}
            </button>
          </div>

          <div className="flex items-center justify-between p-4 bg-astra-panel rounded-xl border border-white/10">
            <div>
              <div className="font-medium">Sound Effects</div>
              <div className="text-sm text-white/60">
                Play audio feedback for actions
              </div>
            </div>
            <button
              onClick={toggleSound}
              className={`px-4 py-2 rounded-lg transition-colors ${
                soundEnabled
                  ? 'bg-status-success hover:bg-status-success/80'
                  : 'bg-white/10 hover:bg-white/20'
              }`}
            >
              {soundEnabled ? 'Enabled' : 'Disabled'}
            </button>
          </div>
        </div>
      </section>

      {/* Keyboard Shortcuts */}
      <section>
        <h2 className="text-xl font-semibold mb-4">Keyboard Shortcuts</h2>
        <div className="bg-astra-panel rounded-xl border border-white/10 p-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex justify-between">
              <span className="text-white/60">Command Palette</span>
              <kbd className="px-2 py-1 bg-white/10 rounded">Cmd+K</kbd>
            </div>
            <div className="flex justify-between">
              <span className="text-white/60">Toggle Pulse</span>
              <kbd className="px-2 py-1 bg-white/10 rounded">Alt+P</kbd>
            </div>
            <div className="flex justify-between">
              <span className="text-white/60">Toggle Spine</span>
              <kbd className="px-2 py-1 bg-white/10 rounded">Alt+S</kbd>
            </div>
            <div className="flex justify-between">
              <span className="text-white/60">Toggle Theme</span>
              <kbd className="px-2 py-1 bg-white/10 rounded">Alt+T</kbd>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
