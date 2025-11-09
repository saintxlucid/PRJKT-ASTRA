import { useState, useEffect } from 'react';

interface Scope {
  name: string;
  ttl: number; // seconds
  startTime: number;
}

export default function Halo() {
  const [time, setTime] = useState(new Date());
  const [scope] = useState<Scope>({ name: "read-only", ttl: 300, startTime: Date.now() });

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const remaining = Math.max(0, Math.floor((scope.startTime + scope.ttl * 1000 - Date.now()) / 1000));
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;

  return (
    <header className="h-14 bg-white/5 backdrop-blur-sm border-b border-white/10 flex items-center justify-between px-6">
      {/* Left: Logo & Time */}
      <div className="flex items-center gap-6">
        <div className="text-xl font-bold tracking-wider">
          <span className="text-astra-accent">ASTRA</span>
          <span className="text-white/50 ml-2 text-sm">OS</span>
        </div>
        <div className="text-sm text-white/70 font-mono">
          {time.toLocaleTimeString('en-US', { hour12: false })}
        </div>
      </div>

      {/* Center: Scope Pill */}
      <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30">
        <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wide">{scope.name}</span>
        <span className="text-xs text-emerald-300 font-mono">
          {minutes}:{seconds.toString().padStart(2, '0')}
        </span>
      </div>

      {/* Right: Quick Actions */}
      <div className="flex items-center gap-3">
        <button 
          className="px-3 py-1.5 text-xs rounded bg-white/5 hover:bg-white/10 transition-colors border border-white/10"
          title="Ctrl+K"
        >
          ⌘ Oracle
        </button>
        <button className="px-3 py-1.5 text-xs rounded bg-white/5 hover:bg-white/10 transition-colors border border-white/10">
          ⚙ Settings
        </button>
      </div>
    </header>
  );
}
