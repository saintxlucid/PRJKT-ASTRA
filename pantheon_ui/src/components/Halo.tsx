import { useEffect, useState } from 'react'
import { Clock, Command, Sparkles, HelpCircle } from 'lucide-react'
import { usePantheonStore } from '@/store/pantheon-store'
import { getModuleMeta } from '@/lib/pantheon-names'

interface HaloProps {
  onOpenOracle: () => void
  onTogglePulse: () => void
  onToggleSpine: () => void
}

export function Halo({ onOpenOracle, onTogglePulse, onToggleSpine }: HaloProps) {
  const [time, setTime] = useState(new Date())
  const { currentRealm } = usePantheonStore()
  const currentMeta = getModuleMeta(currentRealm)

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  }

  return (
    <div className="h-14 bg-obsidian-panel border-b border-white/10 flex items-center justify-between px-4 backdrop-pantheon">
      {/* Left: Brand + Current Realm */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-limestone to-limestone-dark flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-obsidian" />
          </div>
          <span className="font-semibold text-lg tracking-tight">ASTRA</span>
        </div>
        
        <div className="h-6 w-px bg-white/10" />
        
        {currentMeta && (
          <div className="flex items-center gap-2 text-sm">
            <span className="sigil text-lg">{currentMeta.sigil}</span>
            <span className="text-text-secondary">{currentMeta.label}</span>
          </div>
        )}
      </div>

      {/* Center: Oracle Search */}
      <div 
        className="flex-1 max-w-xl mx-8 cursor-pointer"
        onClick={onOpenOracle}
      >
        <div className="bg-obsidian-elevated hover:bg-white/5 border border-white/10 rounded-lg px-4 py-2 flex items-center gap-3 transition-all duration-120">
          <Command className="w-4 h-4 text-text-muted" />
          <span className="text-text-muted text-sm">Summon Oracle...</span>
          <div className="ml-auto flex items-center gap-1">
            <kbd className="px-2 py-1 bg-white/5 rounded text-xs font-mono">⌘K</kbd>
          </div>
        </div>
      </div>

      {/* Right: Clock + Quick Actions */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 font-mono text-sm text-text-secondary">
          <Clock className="w-4 h-4" />
          <span>{formatTime(time)}</span>
        </div>

        <div className="h-6 w-px bg-white/10" />

        <button
          onClick={onOpenOracle}
          className="p-2 hover:bg-white/5 rounded-lg transition-colors"
          title="Help (Ctrl+K)"
        >
          <HelpCircle className="w-5 h-5 text-text-muted" />
        </button>

        {/* Status Pill (Token Scope) */}
        <div className="flex items-center gap-2 px-3 py-1 bg-status-success/10 border border-status-success/30 rounded-full">
          <div className="w-2 h-2 rounded-full bg-status-success animate-pulse" />
          <span className="text-xs text-status-success font-medium">Guardian</span>
        </div>
      </div>
    </div>
  )
}
