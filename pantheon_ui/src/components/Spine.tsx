import { usePantheonStore } from '@/store/pantheon-store'
import { REALMS, INSTRUMENTS, SYSTEM, DEV, ModuleMeta } from '@/lib/pantheon-names'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'

interface SpineProps {
  collapsed?: boolean
}

function SpineSection({ title, modules }: { title: string; modules: ModuleMeta[] }) {
  const { currentRealm, setCurrentRealm } = usePantheonStore()

  return (
    <div className="mb-6">
      <div className="px-3 mb-2">
        <span className="text-xs uppercase tracking-wider text-text-muted font-semibold">
          {title}
        </span>
      </div>
      <div className="space-y-1">
        {modules.map((module) => {
          const isActive = currentRealm === module.id
          return (
            <button
              key={module.id}
              onClick={() => setCurrentRealm(module.id)}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-120 group',
                isActive
                  ? 'bg-limestone/10 border border-limestone/30 text-limestone'
                  : 'hover:bg-white/5 text-text-secondary hover:text-text-primary'
              )}
              title={module.description}
            >
              <span className={clsx(
                'text-lg sigil transition-all',
                isActive && 'scale-110'
              )}>
                {module.sigil}
              </span>
              <span className="text-sm font-medium">{module.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function Spine({ collapsed }: SpineProps) {
  const { spineCollapsed, setSpineCollapsed } = usePantheonStore()
  const isCollapsed = collapsed ?? spineCollapsed

  return (
    <div
      className={clsx(
        'bg-obsidian-panel border-r border-white/10 transition-all duration-300 flex flex-col',
        isCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Toggle Button */}
      <div className="h-14 flex items-center justify-end px-3 border-b border-white/10">
        <button
          onClick={() => setSpineCollapsed(!isCollapsed)}
          className="p-2 hover:bg-white/5 rounded-lg transition-colors"
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4 text-text-muted" />
          ) : (
            <ChevronLeft className="w-4 h-4 text-text-muted" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto scroll-smooth-obsidian p-3">
        {!isCollapsed ? (
          <>
            <SpineSection title="Realms" modules={REALMS} />
            <SpineSection title="Instruments" modules={INSTRUMENTS} />
            <SpineSection title="System" modules={SYSTEM} />
            <SpineSection title="Dev & Evolution" modules={DEV} />
          </>
        ) : (
          <div className="space-y-2">
            {[...REALMS, ...INSTRUMENTS, ...SYSTEM, ...DEV].map((module) => {
              const { currentRealm, setCurrentRealm } = usePantheonStore.getState()
              const isActive = currentRealm === module.id
              return (
                <button
                  key={module.id}
                  onClick={() => setCurrentRealm(module.id)}
                  className={clsx(
                    'w-full flex items-center justify-center p-3 rounded-lg transition-all duration-120',
                    isActive
                      ? 'bg-limestone/10 border border-limestone/30 text-limestone scale-110'
                      : 'hover:bg-white/5 text-text-muted hover:text-text-secondary'
                  )}
                  title={module.label}
                >
                  <span className="text-xl">{module.sigil}</span>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
