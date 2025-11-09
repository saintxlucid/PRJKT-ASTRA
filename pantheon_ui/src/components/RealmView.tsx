import { usePantheonStore } from '@/store/pantheon-store'
import { getModuleMeta } from '@/lib/pantheon-names'
import { Sparkles } from 'lucide-react'
import { AeonDeck } from '@/realms/aeon/AeonDeck'
import { LumenChat } from '@/realms/lumen/LumenChat'
import { SeraphVoice } from '@/realms/seraph/SeraphVoice'
import { Obelisk } from '@/realms/obelisk/Obelisk'
import { AetherLoom } from '@/realms/aether-loom/AetherLoom'
import { Aetherglass } from '@/realms/aetherglass/Aetherglass'
import { DreamGrove } from '@/realms/dream-grove/DreamGrove'

export function RealmView() {
  const { currentRealm } = usePantheonStore()
  const meta = getModuleMeta(currentRealm)

  if (!meta) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <p className="text-text-muted">Realm not found</p>
        </div>
      </div>
    )
  }

  // Route to dedicated realm modules
  if (currentRealm === 'aeon') {
    return <AeonDeck />
  }
  
  if (currentRealm === 'lumen') {
    return <LumenChat />
  }
  
  if (currentRealm === 'seraph') {
    return <SeraphVoice />
  }
  
  if (currentRealm === 'obelisk') {
    return <Obelisk />
  }
  
  if (currentRealm === 'aether-loom') {
    return <AetherLoom />
  }
  
  if (currentRealm === 'aetherglass') {
    return <Aetherglass />
  }

  if (currentRealm === 'dream-grove') {
    return <DreamGrove />
  }

  return (
    <div className="h-full flex flex-col">
      {/* Realm Header */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-4 mb-3">
          <div className="text-5xl sigil animate-breathe">{meta.sigil}</div>
          <div>
            <h1 className="text-3xl font-semibold text-text-primary mb-1">
              {meta.label}
            </h1>
            <p className="text-text-secondary">{meta.description}</p>
          </div>
        </div>
      </div>

      {/* Realm Content */}
      <div className="flex-1 overflow-y-auto scroll-smooth-obsidian p-6">
        <div className="max-w-4xl mx-auto">
          {/* Sanctum Card */}
          <div className="card-elevated p-8 mb-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-lucid-teal to-lucid-violet flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-text-primary mb-2">
                  Sanctum
                </h2>
                <p className="text-text-secondary mb-4">
                  This realm will house the full experience of <span className="font-medium text-limestone">{meta.label}</span>.
                </p>
                <p className="text-text-muted text-sm">
                  Today you are in the Pantheon Shell. Routing, metrics, command palette, and theming are live.
                  <br />
                  Next step: mount this realm's module and tools into the canvas.
                </p>
              </div>
            </div>
          </div>

          {/* Coming Soon Features */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="card-obsidian p-6">
              <div className="w-10 h-10 rounded-lg bg-status-info/10 flex items-center justify-center mb-3">
                <span className="text-2xl">✧</span>
              </div>
              <h3 className="text-lg font-medium text-text-primary mb-2">
                Interactive Workspace
              </h3>
              <p className="text-sm text-text-muted">
                Full realm implementation with modular panes, split views, and context-aware tools.
              </p>
            </div>

            <div className="card-obsidian p-6">
              <div className="w-10 h-10 rounded-lg bg-status-success/10 flex items-center justify-center mb-3">
                <span className="text-2xl">⚡</span>
              </div>
              <h3 className="text-lg font-medium text-text-primary mb-2">
                Real-time Integration
              </h3>
              <p className="text-sm text-text-muted">
                Live connection to ASTRA Core backend services, memory systems, and agent kernel.
              </p>
            </div>

            <div className="card-obsidian p-6">
              <div className="w-10 h-10 rounded-lg bg-status-warning/10 flex items-center justify-center mb-3">
                <span className="text-2xl">✠</span>
              </div>
              <h3 className="text-lg font-medium text-text-primary mb-2">
                Sigil Gate Integration
              </h3>
              <p className="text-sm text-text-muted">
                Token-gated operations with consent modals, diff previews, and undo journaling.
              </p>
            </div>

            <div className="card-obsidian p-6">
              <div className="w-10 h-10 rounded-lg bg-lucid-violet/10 flex items-center justify-center mb-3">
                <span className="text-2xl">ღ</span>
              </div>
              <h3 className="text-lg font-medium text-text-primary mb-2">
                Dream Grove Memory
              </h3>
              <p className="text-sm text-text-muted">
                Semantic memory with BGE-M3 embeddings, temporal decay, and L0-L3 compression.
              </p>
            </div>
          </div>

          {/* 333 Signature */}
          <div className="mt-8 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-lucid-mint/5 border border-lucid-mint/20 rounded-full">
              <span className="glyph-333 text-sm font-mono font-semibold">333</span>
              <span className="text-xs text-text-muted">Saint Lucid Edition</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
