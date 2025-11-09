import { useEffect, useState, useRef } from 'react'
import { Search, Command } from 'lucide-react'
import { usePantheonStore } from '@/store/pantheon-store'
import { ALL_MODULES, ModuleMeta } from '@/lib/pantheon-names'
import clsx from 'clsx'

interface OracleProps {
  open: boolean
  onClose: () => void
}

export function Oracle({ open, onClose }: OracleProps) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const { setCurrentRealm } = usePantheonStore()

  const filtered = ALL_MODULES.filter(
    (mod) =>
      mod.label.toLowerCase().includes(query.toLowerCase()) ||
      mod.description.toLowerCase().includes(query.toLowerCase()) ||
      mod.sigil.includes(query)
  )

  useEffect(() => {
    if (open) {
      setQuery('')
      setSelected(0)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelected((s) => Math.min(filtered.length - 1, s + 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelected((s) => Math.max(0, s - 1))
      } else if (e.key === 'Enter' && filtered[selected]) {
        e.preventDefault()
        handleSelect(filtered[selected])
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, filtered, selected, onClose])

  const handleSelect = (module: ModuleMeta) => {
    setCurrentRealm(module.id)
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-32 bg-black/60 backdrop-blur-sm animate-spring-in">
      <div className="w-full max-w-2xl card-elevated shadow-2xl">
        {/* Search Input */}
        <div className="flex items-center gap-3 p-4 border-b border-white/10">
          <Search className="w-5 h-5 text-text-muted" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelected(0)
            }}
            placeholder="Search realms, instruments, systems..."
            className="flex-1 bg-transparent text-text-primary placeholder:text-text-muted outline-none text-lg"
          />
          <div className="flex items-center gap-2">
            <kbd className="px-2 py-1 bg-white/5 rounded text-xs font-mono text-text-muted">ESC</kbd>
          </div>
        </div>

        {/* Results */}
        <div className="max-h-96 overflow-y-auto scroll-smooth-obsidian">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-text-muted">
              <Command className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No results found</p>
            </div>
          ) : (
            <div className="p-2">
              {filtered.map((module, idx) => (
                <button
                  key={module.id}
                  onClick={() => handleSelect(module)}
                  className={clsx(
                    'w-full flex items-center gap-4 p-3 rounded-lg transition-all duration-120 text-left',
                    idx === selected
                      ? 'bg-limestone/10 border border-limestone/30'
                      : 'hover:bg-white/5'
                  )}
                >
                  <span className="text-2xl sigil">{module.sigil}</span>
                  <div className="flex-1">
                    <div className="font-medium text-text-primary mb-1">
                      {module.label}
                    </div>
                    <div className="text-sm text-text-muted line-clamp-1">
                      {module.description}
                    </div>
                  </div>
                  <div className="text-xs px-2 py-1 bg-white/5 rounded text-text-muted">
                    {module.category}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-white/10 bg-obsidian-elevated">
          <div className="flex items-center gap-4 text-xs text-text-muted">
            <div className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white/5 rounded font-mono">↑</kbd>
              <kbd className="px-1.5 py-0.5 bg-white/5 rounded font-mono">↓</kbd>
              <span>Navigate</span>
            </div>
            <div className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-white/5 rounded font-mono">↵</kbd>
              <span>Select</span>
            </div>
          </div>
          <span className="text-xs text-text-muted">
            {filtered.length} realm{filtered.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>
    </div>
  )
}
