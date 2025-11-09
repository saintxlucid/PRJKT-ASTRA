import { Activity, HardDrive, Network, ListTodo } from 'lucide-react'

interface MetricCardProps {
  label: string
  value: number
  max: number
  unit: string
  icon: React.ReactNode
}

function MetricCard({ label, value, max, unit, icon }: MetricCardProps) {
  const percentage = Math.min(100, (value / max) * 100)
  
  return (
    <div className="card-obsidian p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="text-text-muted">{icon}</div>
          <span className="text-sm font-medium text-text-secondary">{label}</span>
        </div>
        <span className="text-xs text-text-muted">{unit}</span>
      </div>
      
      <div className="mb-2">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold text-text-primary">{value}</span>
          <span className="text-sm text-text-muted">/ {max}</span>
        </div>
      </div>
      
      <div className="h-2 bg-obsidian-elevated rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-lucid-teal to-lucid-mint transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

export function Pulse() {
  // Mock data - in production, these would come from system APIs
  const metrics = {
    cpu: { value: 34, max: 100, unit: '%' },
    memory: { value: 12.4, max: 32, unit: 'GB' },
    network: { value: 2.3, max: 10, unit: 'MB/s' },
    tasks: { value: 3, max: 10, unit: 'active' },
  }

  return (
    <div className="w-80 bg-obsidian-panel border-l border-white/10 flex flex-col">
      <div className="h-14 flex items-center px-4 border-b border-white/10">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-text-muted">
          Pulse ◴
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto scroll-smooth-obsidian p-4 space-y-4">
        <MetricCard
          label="CPU"
          value={metrics.cpu.value}
          max={metrics.cpu.max}
          unit={metrics.cpu.unit}
          icon={<Activity className="w-4 h-4" />}
        />
        
        <MetricCard
          label="Memory"
          value={metrics.memory.value}
          max={metrics.memory.max}
          unit={metrics.memory.unit}
          icon={<HardDrive className="w-4 h-4" />}
        />
        
        <MetricCard
          label="Network"
          value={metrics.network.value}
          max={metrics.network.max}
          unit={metrics.network.unit}
          icon={<Network className="w-4 h-4" />}
        />
        
        <MetricCard
          label="Tasks"
          value={metrics.tasks.value}
          max={metrics.tasks.max}
          unit={metrics.tasks.unit}
          icon={<ListTodo className="w-4 h-4" />}
        />

        {/* Jobs Section */}
        <div className="card-obsidian p-4">
          <h3 className="text-sm font-medium text-text-secondary mb-3">Active Jobs</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-primary">Dream compression L0→L1</span>
              <span className="text-xs px-2 py-1 bg-status-info/10 text-status-info rounded">Running</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-primary">BGE-M3 embedding batch</span>
              <span className="text-xs px-2 py-1 bg-status-warning/10 text-status-warning rounded">Paused</span>
            </div>
          </div>
        </div>

        {/* Beacons Section */}
        <div className="card-obsidian p-4">
          <h3 className="text-sm font-medium text-text-secondary mb-3">Beacons ⌁</h3>
          <div className="space-y-2 text-sm text-text-muted">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-status-success" />
              <span>Next ultradian break in 42 min</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-status-info" />
              <span>Calendar sync at 15:00</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
