import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { memoryAPI, queryKeys } from '../services/client';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import { Dialog, DialogContent, DialogFooter, DialogHeader } from '../components/ui/Dialog';

interface SearchResult {
  text: string;
  score: number;
}

export default function DreamGrove() {
  const [searchQuery, setSearchQuery] = useState('');
  const [newMemoryText, setNewMemoryText] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const queryClient = useQueryClient();

  // Fetch health/stats
  const { data: healthData } = useQuery({
    queryKey: queryKeys.memory.health(),
    queryFn: () => memoryAPI.health(),
    refetchInterval: 5000, // Refresh every 5s
  });

  // Search mutation
  const searchMutation = useMutation({
    mutationFn: (query: string) => memoryAPI.search(query, 10),
    onSuccess: (data) => {
      console.log(`✓ Search completed, ${data.fragments?.length || 0} results`);
    },
    onError: (error) => {
      console.error('Search failed:', error);
    },
  });

  // Add memory mutation
  const addMemoryMutation = useMutation({
    mutationFn: (text: string) => memoryAPI.add(text),
    onSuccess: (data) => {
      console.log('✓ Memory indexed:', data);
      // Invalidate health query to refresh stats
      queryClient.invalidateQueries({ queryKey: queryKeys.memory.health() });
      setNewMemoryText('');
      setShowAddDialog(false);
    },
    onError: (error) => {
      console.error('Failed to add memory:', error);
    },
  });

  const handleSearch = () => {
    if (searchQuery.trim()) {
      searchMutation.mutate(searchQuery.trim());
    }
  };

  const handleAddMemory = () => {
    if (newMemoryText.trim()) {
      addMemoryMutation.mutate(newMemoryText.trim());
    }
  };

  const searchResults = searchMutation.data?.fragments || [];
  const indexSize = healthData?.index_size || 0;
  const isLoading = searchMutation.isPending || addMemoryMutation.isPending;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Dream Grove 🌳 — Memory L0→L1</h1>
        <p className="text-white/60 text-sm">
          Local vector store with decay-based value scoring. Query context in &lt;120ms p95.
        </p>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="p-4 rounded-xl bg-astra-panel border border-white/10">
          <div className="text-xs text-white/50 mb-1">Index Size</div>
          <div className="text-2xl font-bold text-accent-teal">{indexSize}</div>
          <div className="text-xs text-white/40">fragments</div>
        </div>
        <div className="p-4 rounded-xl bg-astra-panel border border-white/10">
          <div className="text-xs text-white/50 mb-1">Model</div>
          <div className="text-lg font-semibold text-white/80">
            {healthData?.model || 'Loading...'}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-astra-panel border border-white/10">
          <div className="text-xs text-white/50 mb-1">Status</div>
          <div className={`text-lg font-semibold ${
            healthData?.status === 'healthy' ? 'text-status-success' : 'text-status-warn'
          }`}>
            {healthData?.status || 'Checking...'}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-astra-panel border border-white/10">
          <div className="text-xs text-white/50 mb-1">Results</div>
          <div className="text-2xl font-bold text-accent-amber">
            {searchResults.length}
          </div>
          <div className="text-xs text-white/40">matches</div>
        </div>
      </div>

      {/* Search Interface */}
      <div className="bg-astra-panel rounded-xl p-6 border border-white/10 mb-6">
        <h2 className="text-sm font-semibold text-white/70 mb-4">Search Memories</h2>
        <div className="flex gap-3 mb-4">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Enter search query..."
            className="flex-1"
          />
          <Button
            onClick={handleSearch}
            disabled={!searchQuery.trim() || isLoading}
            loading={searchMutation.isPending}
          >
            Search
          </Button>
        </div>

        {/* Search Results */}
        {searchMutation.isError && (
          <div className="p-4 rounded-lg bg-status-danger/10 border border-status-danger/30 text-status-danger text-sm">
            ❌ Search failed. Is the memory service running?
          </div>
        )}

        {searchResults.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-white/50 uppercase tracking-wide mb-2">
              Results ({searchResults.length})
            </div>
            {searchResults.map((result: SearchResult, idx: number) => (
              <div
                key={idx}
                className="p-4 rounded-lg bg-astra-bg border border-white/10 hover:border-accent-teal/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="text-white/90 text-sm flex-1">{result.text}</span>
                  <span className="text-xs text-accent-teal font-mono ml-3 bg-accent-teal/10 px-2 py-1 rounded">
                    {(result.score * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {searchMutation.isSuccess && searchResults.length === 0 && (
          <div className="text-sm text-white/40 italic text-center py-4">
            No memories found matching your query
          </div>
        )}
      </div>

      {/* Memory Management */}
      <div className="flex items-center gap-3 mb-6">
        <Button
          onClick={() => setShowAddDialog(true)}
          variant="success"
          disabled={isLoading}
        >
          + Add Memory
        </Button>
        <div className="text-xs text-white/40">
          Use semantic search to find similar memories
        </div>
      </div>

      {/* Add Memory Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent>
          <DialogHeader>
            <h3 className="text-lg font-semibold">Add New Memory</h3>
            <p className="text-sm text-white/60">Enter memory content to be indexed</p>
          </DialogHeader>
          
          <div className="py-4">
            <Input
              label="Memory Content"
              value={newMemoryText}
              onChange={(e) => setNewMemoryText(e.target.value)}
              placeholder="Enter memory fragment..."
              required
            />
          </div>

          {addMemoryMutation.isError && (
            <div className="p-3 rounded-lg bg-status-danger/10 border border-status-danger/30 text-status-danger text-sm mb-4">
              Failed to add memory. Please try again.
            </div>
          )}

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setShowAddDialog(false)}
              disabled={addMemoryMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleAddMemory}
              disabled={!newMemoryText.trim()}
              loading={addMemoryMutation.isPending}
            >
              Add Memory
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Service Status */}
      <div className="bg-astra-panel rounded-xl p-4 border border-white/10">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-white/80 mb-1">Memory Service</div>
            <div className="text-xs text-white/50">
              {healthData?.status === 'healthy' ? (
                <span className="text-status-success">✓ Connected</span>
              ) : (
                <span className="text-status-warn">⚠ Checking connection...</span>
              )}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-white/50 mb-1">Endpoint</div>
            <div className="text-xs font-mono text-accent-teal">
              {import.meta.env.VITE_MEMORY_API || 'http://127.0.0.1:7007'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
