import { useState, useEffect } from 'react'
import { astraAPI, Memory, MemoryLayer, TemporalDecayStats } from '@/lib/api/client'
import { Database, Layers, Search, Zap, TrendingDown, GitMerge, Clock } from 'lucide-react'

export function DreamGrove() {
  const [layers, setLayers] = useState<MemoryLayer[]>([])
  const [memories, setMemories] = useState<Memory[]>([])
  const [selectedLayer, setSelectedLayer] = useState<number | null>(null)
  const [decayStats, setDecayStats] = useState<TemporalDecayStats | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load initial data
  useEffect(() => {
    loadLayers()
    loadDecayStats()
    loadMemories()
  }, [])

  // Reload memories when layer selection changes
  useEffect(() => {
    if (selectedLayer !== null || selectedLayer === 0) {
      loadMemories()
    }
  }, [selectedLayer])

  const loadLayers = async () => {
    try {
      const data = await astraAPI.getMemoryLayers()
      setLayers(data)
    } catch (err) {
      console.error('Failed to load layers:', err)
      setError('Failed to load memory layers')
    }
  }

  const loadMemories = async () => {
    try {
      setLoading(true)
      const data = await astraAPI.getAllMemories(
        selectedLayer !== null ? selectedLayer : undefined,
        50
      )
      setMemories(data)
      setError(null)
    } catch (err) {
      console.error('Failed to load memories:', err)
      setError('Failed to load memories')
    } finally {
      setLoading(false)
    }
  }

  const loadDecayStats = async () => {
    try {
      const stats = await astraAPI.getTemporalDecayStats()
      setDecayStats(stats)
    } catch (err) {
      console.error('Failed to load decay stats:', err)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadMemories()
      return
    }

    try {
      setLoading(true)
      const results = await astraAPI.searchMemories(
        searchQuery,
        selectedLayer !== null ? selectedLayer : undefined,
        20
      )
      setMemories(results.map(r => r.memory))
      setError(null)
    } catch (err) {
      console.error('Search failed:', err)
      setError('Search failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRunDecay = async () => {
    try {
      setLoading(true)
      const stats = await astraAPI.runTemporalDecay(0.01)
      setDecayStats(stats)
      await loadLayers()
      await loadMemories()
      setError(null)
    } catch (err) {
      console.error('Decay run failed:', err)
      setError('Decay run failed')
    } finally {
      setLoading(false)
    }
  }

  const handleCompress = async (source: number, target: number) => {
    try {
      setLoading(true)
      await astraAPI.compressMemories(source, target)
      await loadLayers()
      await loadMemories()
      setError(null)
    } catch (err) {
      console.error('Compression failed:', err)
      setError('Compression failed')
    } finally {
      setLoading(false)
    }
  }

  const getLayerColor = (layer: number): string => {
    const colors = [
      'from-blue-500/20 to-blue-600/10', // L0
      'from-purple-500/20 to-purple-600/10', // L1
      'from-pink-500/20 to-pink-600/10', // L2
      'from-amber-500/20 to-amber-600/10', // L3
    ]
    return colors[layer] || colors[0]
  }

  const getLayerIcon = (layer: number) => {
    const icons = [Database, Layers, Zap, GitMerge]
    const Icon = icons[layer] || Database
    return <Icon className="w-6 h-6" />
  }

  return (
    <div className="h-full flex flex-col bg-bg-primary">
      {/* Header */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-4 mb-3">
          <div className="text-5xl sigil animate-breathe">ღ</div>
          <div>
            <h1 className="text-3xl font-semibold text-text-primary mb-1">
              Dream Grove
            </h1>
            <p className="text-text-secondary">Memory L0–L3 + Temporal Decay</p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="mt-4 flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="Search memories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full pl-10 pr-4 py-2 bg-bg-secondary border border-white/10 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary/50"
            />
          </div>
          <button
            onClick={handleSearch}
            className="px-4 py-2 bg-accent-primary/20 hover:bg-accent-primary/30 border border-accent-primary/30 rounded-lg text-text-primary transition-colors"
          >
            Search
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mx-6 mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center justify-between">
          <span className="text-red-400">{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-300"
          >
            ×
          </button>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Left Sidebar - Memory Layers */}
        <div className="w-80 border-r border-white/10 overflow-y-auto scroll-smooth-obsidian p-4">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2">
              <Layers className="w-5 h-5" />
              Memory Layers
            </h2>
            <div className="space-y-2">
              {layers.map((layer) => (
                <button
                  key={layer.layer}
                  onClick={() => setSelectedLayer(layer.layer)}
                  className={`w-full p-4 rounded-lg border transition-all ${
                    selectedLayer === layer.layer
                      ? 'border-accent-primary/50 bg-accent-primary/10'
                      : 'border-white/10 bg-bg-secondary hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    {getLayerIcon(layer.layer)}
                    <div className="flex-1 text-left">
                      <div className="text-sm font-semibold text-text-primary">
                        {layer.label}
                      </div>
                      <div className="text-xs text-text-muted">
                        {layer.memory_count} memories
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-text-muted">
                    <div className="flex-1 bg-white/5 rounded-full h-1.5">
                      <div
                        className={`h-full rounded-full bg-gradient-to-r ${getLayerColor(
                          layer.layer
                        )}`}
                        style={{
                          width: `${Math.min(
                            (layer.memory_count / Math.max(...layers.map((l) => l.memory_count))) *
                              100,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                    <span>{(layer.compression_ratio * 100).toFixed(0)}%</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Layer Operations */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Compression</h3>
            <div className="space-y-2">
              <button
                onClick={() => handleCompress(0, 1)}
                disabled={loading}
                className="w-full p-3 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg text-sm text-text-primary transition-colors disabled:opacity-50"
              >
                L0 → L1 Compress
              </button>
              <button
                onClick={() => handleCompress(1, 2)}
                disabled={loading}
                className="w-full p-3 bg-pink-500/10 hover:bg-pink-500/20 border border-pink-500/30 rounded-lg text-sm text-text-primary transition-colors disabled:opacity-50"
              >
                L1 → L2 Compress
              </button>
              <button
                onClick={() => handleCompress(2, 3)}
                disabled={loading}
                className="w-full p-3 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg text-sm text-text-primary transition-colors disabled:opacity-50"
              >
                L2 → L3 Compress
              </button>
            </div>
          </div>

          {/* Temporal Decay */}
          {decayStats && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <TrendingDown className="w-4 h-4" />
                Temporal Decay
              </h3>
              <div className="p-3 bg-bg-secondary border border-white/10 rounded-lg space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-text-muted">Total Memories:</span>
                  <span className="text-text-primary font-semibold">
                    {decayStats.total_memories}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Avg Importance:</span>
                  <span className="text-text-primary font-semibold">
                    {decayStats.avg_importance.toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Decay Rate:</span>
                  <span className="text-text-primary font-semibold">
                    {decayStats.decay_rate}
                  </span>
                </div>
                <button
                  onClick={handleRunDecay}
                  disabled={loading}
                  className="w-full mt-2 p-2 bg-orange-500/10 hover:bg-orange-500/20 border border-orange-500/30 rounded text-text-primary transition-colors disabled:opacity-50"
                >
                  Run Decay Now
                </button>
              </div>
            </div>
          )}

          {/* Filter Controls */}
          <button
            onClick={() => {
              setSelectedLayer(null)
              setSearchQuery('')
              loadMemories()
            }}
            className="w-full p-3 bg-bg-secondary hover:bg-bg-elevated border border-white/10 rounded-lg text-sm text-text-primary transition-colors"
          >
            Show All Layers
          </button>
        </div>

        {/* Right Panel - Memory List */}
        <div className="flex-1 overflow-y-auto scroll-smooth-obsidian p-6">
          {loading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-accent-primary" />
              <p className="text-text-muted mt-4">Loading memories...</p>
            </div>
          )}

          {!loading && memories.length === 0 && (
            <div className="text-center py-12">
              <Database className="w-12 h-12 text-text-muted mx-auto mb-4" />
              <p className="text-text-muted">
                {selectedLayer !== null
                  ? `No memories in L${selectedLayer}`
                  : 'No memories stored yet'}
              </p>
            </div>
          )}

          {!loading && memories.length > 0 && (
            <div className="space-y-4">
              {memories.map((memory) => (
                <div
                  key={memory.id}
                  className={`p-4 rounded-lg border bg-gradient-to-br ${getLayerColor(
                    memory.layer
                  )} border-white/10 hover:border-white/20 transition-colors`}
                >
                  <div className="flex items-start gap-3 mb-2">
                    {getLayerIcon(memory.layer)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-accent-primary">
                          L{memory.layer}
                        </span>
                        <span className="text-xs text-text-muted">•</span>
                        <span className="text-xs text-text-muted">{memory.source}</span>
                        <span className="text-xs text-text-muted">•</span>
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          <span className="text-xs text-text-muted">
                            {memory.access_count} accesses
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-text-primary leading-relaxed">
                        {memory.content}
                      </p>
                      {memory.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {memory.tags.map((tag, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 bg-white/5 border border-white/10 rounded text-xs text-text-muted"
                            >
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-semibold text-text-primary mb-1">
                        {(memory.importance * 100).toFixed(0)}%
                      </div>
                      <div className="text-xs text-text-muted">importance</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
