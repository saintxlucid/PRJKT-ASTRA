import { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sigilAPI, queryKeys } from '../services/client';
import Button from '../components/ui/Button';
import ConsentCard from '../components/ConsentCard';
import { Dialog, DialogContent, DialogFooter, DialogHeader } from '../components/ui/Dialog';
import { sha256Hex } from '../lib/crypto';

interface Plan {
  summary: string;
  diffs: Array<{ path: string; change: 'create' | 'write' | 'delete' | 'move' }>;
  scopes: string[];
}

export default function SigilGate() {
  const [showRollbackDialog, setShowRollbackDialog] = useState(false);
  const [lastSealId, setLastSealId] = useState<number | null>(null);
  const [sealStatus, setSealStatus] = useState<'idle' | 'approved' | 'rejected'>('idle');
  const [rollbackReason, setRollbackReason] = useState<string>('user_request');
  const [customReason, setCustomReason] = useState<string>('');
  const [planDigest, setPlanDigest] = useState<string>('');
  const queryClient = useQueryClient();

  // Demo plan for showcasing ConsentCard
  const [plan] = useState<Plan>({
    summary: "Delete 10 files in X:/Sandbox/demo",
    diffs: Array.from({ length: 10 }, (_, i) => ({
      path: `X:/Sandbox/demo/${i}.txt`,
      change: 'delete' as const,
    })),
    scopes: ['filesystem', 'sandbox'],
  });

  // Fetch health/stats
  const { data: healthData } = useQuery({
    queryKey: queryKeys.sigil.health(),
    queryFn: () => sigilAPI.health(),
    refetchInterval: 5000,
  });

  // Journal entries (defensive; backend may not yet support endpoint)
  const {
    data: journalData,
    isLoading: journalLoading,
    isError: journalError,
    refetch: refetchJournal,
  } = useQuery({
    queryKey: queryKeys.sigil.journal(10),
    queryFn: () => sigilAPI.journalRecent(10),
    refetchInterval: 8000,
    staleTime: 5000,
    retry: 1,
  });

  // Seal plan mutation
  const sealMutation = useMutation({
    mutationFn: () => sigilAPI.seal('user', plan, 600),
    onSuccess: async (data) => {
      console.log('✓ Plan sealed:', data);
      setLastSealId(data.seal_id);
      
      // Verify the seal
      try {
        const verification = await sigilAPI.verify(plan);
        if (verification.valid) {
          setSealStatus('approved');
          console.log('✓ Seal verified');
        } else {
          setSealStatus('rejected');
          console.error('✗ Verification failed');
        }
      } catch (error) {
        console.error('Verification error:', error);
        setSealStatus('rejected');
      }
      
      queryClient.invalidateQueries({ queryKey: queryKeys.sigil.health() });
    },
    onError: (error) => {
      console.error('Failed to seal plan:', error);
      setSealStatus('rejected');
    },
  });

  // Rollback mutation
  const rollbackMutation = useMutation({
    mutationFn: () => sigilAPI.rollbackLastWithReason(
      rollbackReason === 'custom' ? customReason || 'custom_reason' : rollbackReason
    ),
    onSuccess: () => {
      console.log('✓ Rolled back last operation');
      setSealStatus('idle');
      setLastSealId(null);
      setShowRollbackDialog(false);
      queryClient.invalidateQueries({ queryKey: queryKeys.sigil.health() });
      refetchJournal();
    },
    onError: (error) => {
      console.error('Rollback failed:', error);
    },
  });

  const handleApprove = () => {
    sealMutation.mutate();
  };

  const handleReject = () => {
    setSealStatus('rejected');
    console.log('✗ Plan rejected by user');
  };

  const handleRollback = () => {
    rollbackMutation.mutate();
  };

  // Compute a digest (SHA-256) of the plan for reference transparency using lib/crypto
  useEffect(() => {
    async function hashPlan() {
      try {
        const text = JSON.stringify(plan);
        const hash = await sha256Hex(text);
        // Shorten for UI display
        setPlanDigest(hash.slice(0, 16));
      } catch (e) {
        console.warn('Digest computation failed', e);
      }
    }
    hashPlan();
  }, [plan]);

  const rollbackReasonIsCustom = rollbackReason === 'custom';

  const journalEntries: Array<Record<string, any>> = useMemo(() => {
    if (!journalData?.entries) return [];
    return journalData.entries.slice(0, 10);
  }, [journalData]);

  return (
  <div className="p-6 max-w-5xl mx-auto" aria-live="polite">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Sigil Gate ✠ — Consent & Verification</h1>
        <p className="text-white/60 text-sm">
          Token-gated operations require explicit approval. All actions are logged to an immutable journal.
        </p>
        {planDigest && (
          <div className="mt-2 text-[10px] font-mono text-white/40 select-all">plan digest: {planDigest}</div>
        )}
      </div>

      {/* Service Status */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 rounded-xl bg-astra-panel border border-white/10">
          <div className="text-xs text-white/50 mb-1">Service Status</div>
          <div className={`text-lg font-semibold ${
            healthData?.status === 'healthy' ? 'text-status-success' : 'text-status-warn'
          }`}>
            {healthData?.status || 'Checking...'}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-astra-panel border border-white/10">
          <div className="text-xs text-white/50 mb-1">Service</div>
          <div className="text-lg font-semibold text-white/80">
            {healthData?.service || 'Sigil Gate'}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-astra-panel border border-white/10">
          <div className="text-xs text-white/50 mb-1">Endpoint</div>
          <div className="text-xs font-mono text-accent-teal truncate">
            {sigilAPI.baseURL}
          </div>
        </div>
      </div>

      {/* ConsentCard Showcase */}
      {sealStatus === 'idle' && (
        <div className="mb-6">
          <ConsentCard
            plan={plan}
            onApprove={handleApprove}
            onReject={handleReject}
            loading={sealMutation.isPending}
          />

          {sealMutation.isError && (
            <div className="mt-4 p-4 rounded-lg bg-status-danger/10 border border-status-danger/30 text-status-danger text-sm">
              ❌ Failed to seal plan. Is the Sigil Gate service running?
            </div>
          )}
        </div>
      )}

      {/* Approved Status */}
      {sealStatus === 'approved' && (
        <div className="mb-6">
          <div className="p-6 rounded-xl bg-status-success/10 border border-status-success/30">
            <div className="flex items-start gap-4">
              <div className="text-3xl">✓</div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-status-success mb-1">
                  Plan Sealed & Verified
                </h3>
                <p className="text-sm text-white/70 mb-3">
                  Operation approved and logged to immutable journal.
                </p>
                {lastSealId && (
                  <div className="text-xs font-mono text-white/50">
                    Seal ID: #{lastSealId}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <Button
              onClick={() => setShowRollbackDialog(true)}
              variant="danger"
              disabled={rollbackMutation.isPending}
            >
              Rollback Last Operation
            </Button>
            <Button
              onClick={() => setSealStatus('idle')}
              variant="ghost"
            >
              Review New Plan
            </Button>
          </div>
        </div>
      )}

      {/* Rejected Status */}
      {sealStatus === 'rejected' && (
        <div className="mb-6">
          <div className="p-6 rounded-xl bg-status-danger/10 border border-status-danger/30">
            <div className="flex items-start gap-4">
              <div className="text-3xl">✗</div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-status-danger mb-1">
                  Operation Rejected
                </h3>
                <p className="text-sm text-white/70">
                  Plan was not approved. No changes were made.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4">
            <Button
              onClick={() => setSealStatus('idle')}
              variant="primary"
            >
              Review Plan Again
            </Button>
          </div>
        </div>
      )}

      {/* Rollback Confirmation Dialog */}
      <Dialog open={showRollbackDialog} onOpenChange={setShowRollbackDialog}>
        <DialogContent>
          <DialogHeader>
            <h3 className="text-lg font-semibold text-status-warn">Confirm Rollback</h3>
            <p className="text-sm text-white/60">
              This will undo the last sealed operation. This action is logged to the journal.
            </p>
          </DialogHeader>

          {/* Reason selection */}
          <div className="mb-4 space-y-2">
            <label htmlFor="rollback-reason" className="block text-xs font-semibold uppercase tracking-wide text-white/50">Reason</label>
            <select
              id="rollback-reason"
              className="w-full rounded-lg bg-astra-bg border border-white/10 px-3 py-2 text-sm outline-none focus:border-accent-gold/60"
              value={rollbackReason}
              onChange={(e) => setRollbackReason(e.target.value)}
              disabled={rollbackMutation.isPending}
            >
              <option value="user_request">User Request</option>
              <option value="consistency_check">Consistency Check</option>
              <option value="safety_violation">Safety Violation</option>
              <option value="diagnostic_test">Diagnostic Test</option>
              <option value="custom">Custom…</option>
            </select>
            {rollbackReasonIsCustom && (
              <input
                type="text"
                className="w-full rounded-lg bg-astra-bg border border-white/10 px-3 py-2 text-sm outline-none focus:border-accent-gold/60"
                placeholder="Enter custom reason"
                value={customReason}
                onChange={(e) => setCustomReason(e.target.value)}
                disabled={rollbackMutation.isPending}
              />
            )}
          </div>

          {rollbackMutation.isError && (
            <div className="p-3 rounded-lg bg-status-danger/10 border border-status-danger/30 text-status-danger text-sm">
              Failed to rollback. Please try again.
            </div>
          )}

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setShowRollbackDialog(false)}
              disabled={rollbackMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleRollback}
              loading={rollbackMutation.isPending}
            >
              Rollback
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Journal Preview */}
      <div className="pt-6 border-t border-white/10">
        <h2 className="text-sm font-semibold text-white/70 mb-3 flex items-center gap-3">
          <span>Recent Journal Entries</span>
          <Button variant="ghost" size="sm" onClick={() => refetchJournal()} disabled={journalLoading}>
            Refresh
          </Button>
        </h2>
        <div className="bg-astra-panel rounded-xl border border-white/10 p-4 min-h-[120px]">
          {journalLoading && (
            <div className="animate-pulse text-xs text-white/40">Loading journal…</div>
          )}
          {journalError && !journalLoading && (
            <div className="text-xs text-status-warn">
              Unable to load journal entries (endpoint unavailable). Showing none.
            </div>
          )}
          {!journalLoading && !journalError && journalEntries.length === 0 && (
            <div className="text-xs text-white/40">No entries yet.</div>
          )}
          <div className="space-y-2 text-xs font-mono">
            {journalEntries.map((entry, i) => {
              const ts = (entry.timestamp as string) || entry.time || '';
              const type = (entry.type as string) || 'event';
              const sealId = (entry.seal_id as number) || (entry.id as number);
              const digest = (entry.digest as string)?.slice(0, 12);
              const status = (entry.status as string) || (entry.valid ? 'verified' : '');
              const ops = entry.ops || entry.operations || entry.count;
              const reason = entry.reason as string | undefined;
              const isRollback = type.toLowerCase().includes('rollback');
              return (
                <div
                  key={i}
                  className="p-3 rounded-lg bg-astra-bg text-white/70 hover:bg-white/5 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-white/90">[{ts}]</span>
                    <span className={isRollback ? 'text-status-warn' : 'text-accent-gold'}>
                      {isRollback ? 'ROLLBACK' : 'SEAL'} {sealId !== undefined ? `#${sealId}` : ''}
                    </span>
                  </div>
                  <div className="text-white/50 flex flex-wrap gap-x-3 gap-y-1">
                    {digest && <span>digest: {digest}…</span>}
                    {typeof ops === 'number' && <span>ops: {ops}</span>}
                    {status && <span>status: {status}</span>}
                    {reason && <span>reason: {reason}</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
