export default function AEON() {
  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">ÆON Deck ∞</h1>
        <p className="text-white/60 text-sm">
          Temporal awareness and task orchestration across infinite contexts.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Active Context */}
        <div className="bg-white/5 rounded-lg p-6 border border-white/10">
          <h2 className="text-sm font-semibold text-white/70 mb-4">Active Context</h2>
          <div className="space-y-3">
            <div>
              <div className="text-xs text-white/50 mb-1">Current Realm</div>
              <div className="text-white/90 font-medium">ÆON Deck</div>
            </div>
            <div>
              <div className="text-xs text-white/50 mb-1">Session Duration</div>
              <div className="text-white/90 font-medium font-mono">00:12:34</div>
            </div>
            <div>
              <div className="text-xs text-white/50 mb-1">Operations</div>
              <div className="text-white/90 font-medium">0 pending</div>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="bg-white/5 rounded-lg p-6 border border-white/10">
          <h2 className="text-sm font-semibold text-white/70 mb-4">System Status</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/60">Memory Index</span>
              <span className="text-emerald-400 font-mono text-sm">Ready</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/60">Consent Gate</span>
              <span className="text-emerald-400 font-mono text-sm">Armed</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/60">Research Tools</span>
              <span className="text-emerald-400 font-mono text-sm">Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="mt-6 bg-white/5 rounded-lg p-6 border border-white/10">
        <h2 className="text-sm font-semibold text-white/70 mb-4">Recent Activity</h2>
        <div className="space-y-2 text-sm">
          <div className="p-3 rounded bg-white/5 flex items-center gap-3">
            <span className="text-white/40 font-mono text-xs">14:23:01</span>
            <span className="text-white/70">Consent sealed for 10 operations</span>
          </div>
          <div className="p-3 rounded bg-white/5 flex items-center gap-3">
            <span className="text-white/40 font-mono text-xs">14:18:33</span>
            <span className="text-white/70">Memory indexed: 5 new fragments</span>
          </div>
          <div className="p-3 rounded bg-white/5 flex items-center gap-3">
            <span className="text-white/40 font-mono text-xs">14:12:15</span>
            <span className="text-white/70">Research cite captured</span>
          </div>
        </div>
      </div>
    </div>
  );
}
