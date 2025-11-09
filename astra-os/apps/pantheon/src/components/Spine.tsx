import { REALMS, INSTRUMENTS, SYSTEM, RealmId } from '../core/routes';

interface SpineProps {
  currentRealm: RealmId | null;
  onNavigate: (path: string) => void;
}

export default function Spine({ currentRealm, onNavigate }: SpineProps) {
  return (
    <aside className="w-56 bg-white/5 backdrop-blur-sm border-r border-white/10 flex flex-col">
      {/* Realms */}
      <section className="p-4 border-b border-white/10">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">Realms</h3>
        <nav className="space-y-1">
          {REALMS.map((realm) => (
            <button
              key={realm.id}
              onClick={() => onNavigate(realm.path)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded transition-colors text-left ${
                currentRealm === realm.id
                  ? 'bg-astra-accent text-white'
                  : 'text-white/70 hover:bg-white/10 hover:text-white'
              }`}
            >
              <span className="text-xl">{realm.sigil}</span>
              <span className="text-sm font-medium">{realm.label}</span>
            </button>
          ))}
        </nav>
      </section>

      {/* Instruments */}
      <section className="p-4 border-b border-white/10">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">Instruments</h3>
        <nav className="space-y-1">
          {INSTRUMENTS.map((inst) => (
            <button
              key={inst.id}
              className="w-full flex items-center gap-3 px-3 py-2 rounded text-white/70 hover:bg-white/10 hover:text-white transition-colors text-left"
            >
              <span className="text-lg">{inst.icon}</span>
              <span className="text-sm font-medium">{inst.label}</span>
              {inst.shortcut && (
                <span className="ml-auto text-xs text-white/40 font-mono">{inst.shortcut}</span>
              )}
            </button>
          ))}
        </nav>
      </section>

      {/* System */}
      <section className="p-4 mt-auto">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">System</h3>
        <nav className="space-y-1">
          {SYSTEM.map((sys) => (
            <button
              key={sys.id}
              onClick={() => onNavigate(sys.path)}
              className="w-full flex items-center gap-3 px-3 py-2 rounded text-white/70 hover:bg-white/10 hover:text-white transition-colors text-left"
            >
              <span className="text-lg">{sys.icon}</span>
              <span className="text-sm font-medium">{sys.label}</span>
            </button>
          ))}
        </nav>
      </section>
    </aside>
  );
}
