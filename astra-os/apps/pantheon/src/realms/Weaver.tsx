import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supervisorAPI, queryKeys } from '../services/client';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import { Dialog, DialogContent, DialogFooter, DialogHeader } from '../components/ui/Dialog';

interface SLO {
  name: string;
  value: number;
  threshold: number;
  unit: string;
  status: 'good' | 'warning' | 'critical';
}

export default function Weaver() {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newJobType, setNewJobType] = useState('');
  const [simulateMode, setSimulateMode] = useState(false);
  const queryClient = useQueryClient();

  // Mock SLOs for now (could be from health endpoint later)
  const [slos] = useState<SLO[]>([
    { name: 'Verify p95', value: 42, threshold: 100, unit: 'ms', status: 'good' },
    { name: 'Consent p95', value: 85, threshold: 150, unit: 'ms', status: 'good' },
    { name: 'Denial Count', value: 0, threshold: 10, unit: '', status: 'good' },
    { name: 'Job Success Rate', value: 98.5, threshold: 95, unit: '%', status: 'good' },
  ]);

  // Fetch health/stats
  const { data: healthData } = useQuery({
    queryKey: queryKeys.supervisor.health(),
    queryFn: () => supervisorAPI.health(),
    refetchInterval: 5000,
  });

  // Fetch jobs list
  const { data: jobsData, isLoading: isLoadingJobs, isError: isJobsError } = useQuery({
    queryKey: queryKeys.supervisor.jobs(),
    queryFn: () => supervisorAPI.listJobs(),
    refetchInterval: 3000, // Refresh every 3s
  });

  // Create job mutation
  const createJobMutation = useMutation({
    mutationFn: (type: string) => 
      supervisorAPI.createJob(type, { created_from: 'weaver-ui' }),
    onSuccess: (data) => {
      console.log('✓ Job created:', data.job_id);
      queryClient.invalidateQueries({ queryKey: queryKeys.supervisor.jobs() });
      queryClient.invalidateQueries({ queryKey: queryKeys.supervisor.health() });
      setNewJobType('');
      setShowCreateDialog(false);
    },
    onError: (error) => {
      console.error('Failed to create job:', error);
    },
  });

  const handleCreateJob = () => {
    if (newJobType.trim()) {
      createJobMutation.mutate(newJobType.trim());
    }
  };

  const toggleSimulateMode = () => {
    console.log('🎭 Simulate mode:', !simulateMode ? 'ON' : 'OFF');
    setSimulateMode(!simulateMode);
  };

  const jobs = jobsData?.jobs || [];
  const jobCount = healthData?.jobs || jobs.length;

  const statusColors: Record<string, string> = {
    running: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
    paused: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400',
    completed: 'border-blue-500/30 bg-blue-500/10 text-blue-400',
    failed: 'border-rose-500/30 bg-rose-500/10 text-rose-400',
    pending: 'border-blue-400/30 bg-blue-400/10 text-blue-400',
  };

  const sloColors = {
    good: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
    warning: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400',
    critical: 'border-rose-500/30 bg-rose-500/10 text-rose-400',
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Weaver ⚡ — Job Supervisor</h1>
        <p className="text-white/60 text-sm">
          Long-running task orchestration with heartbeat monitoring and SLO tracking.
        </p>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3 mb-6">
        <Button
          onClick={() => setShowCreateDialog(true)}
          disabled={createJobMutation.isPending}
        >
          + Create Job
        </Button>
        <Button
          onClick={toggleSimulateMode}
          variant={simulateMode ? 'primary' : 'ghost'}
        >
          {simulateMode ? '🎭 Simulate: ON' : 'Simulate Mode'}
        </Button>
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
          <div className="text-xs text-white/50 mb-1">Active Jobs</div>
          <div className="text-2xl font-bold text-accent-teal">{jobCount}</div>
        </div>
        <div className="p-4 rounded-xl bg-astra-panel border border-white/10">
          <div className="text-xs text-white/50 mb-1">Endpoint</div>
          <div className="text-xs font-mono text-accent-teal truncate">
            {supervisorAPI.baseURL}
          </div>
        </div>
      </div>

      {/* SLO Dashboard */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {slos.map(slo => (
          <div key={slo.name} className={`p-4 rounded-xl border ${sloColors[slo.status]}`}>
            <div className="text-xs text-white/60 mb-1">{slo.name}</div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold">{slo.value.toFixed(1)}</span>
              <span className="text-sm text-white/60">{slo.unit}</span>
            </div>
            <div className="mt-1 text-xs text-white/40">
              threshold: {slo.threshold}{slo.unit}
            </div>
          </div>
        ))}
      </div>

      {/* Jobs List */}
      <div className="bg-astra-panel rounded-xl border border-white/10 overflow-hidden">
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white/70">Jobs</h2>
          <div className="text-xs text-white/50">{jobs.length} total</div>
        </div>

        {isLoadingJobs && (
          <div className="p-8 text-center text-white/40">Loading jobs...</div>
        )}

        {isJobsError && (
          <div className="p-6 m-4 rounded-lg bg-status-danger/10 border border-status-danger/30 text-status-danger text-sm">
            ❌ Failed to load jobs. Is the supervisor service running?
          </div>
        )}

        {!isLoadingJobs && !isJobsError && jobs.length === 0 && (
          <div className="p-8 text-center text-white/40">No jobs</div>
        )}

        {!isLoadingJobs && !isJobsError && jobs.length > 0 && (
          <div className="divide-y divide-white/10">
            {jobs.map(job => {
              const statusColor = statusColors[job.status] || statusColors.pending;

              return (
                <div key={job.id} className="p-4 hover:bg-white/5 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-semibold text-white/90">{job.type}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded border ${statusColor}`}>
                          {job.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="text-xs text-white/50 font-mono">
                        ID: {job.id}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Job Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <h3 className="text-lg font-semibold">Create New Job</h3>
            <p className="text-sm text-white/60">Enter job type to create</p>
          </DialogHeader>
          
          <div className="py-4">
            <Input
              label="Job Type"
              value={newJobType}
              onChange={(e) => setNewJobType(e.target.value)}
              placeholder="e.g., data-sync, batch-process..."
              required
            />
          </div>

          {createJobMutation.isError && (
            <div className="p-3 rounded-lg bg-status-danger/10 border border-status-danger/30 text-status-danger text-sm mb-4">
              Failed to create job. Please try again.
            </div>
          )}

          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setShowCreateDialog(false)}
              disabled={createJobMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateJob}
              disabled={!newJobType.trim()}
              loading={createJobMutation.isPending}
            >
              Create Job
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Simulate Mode Info */}
      {simulateMode && (
        <div className="mt-4 p-4 rounded-lg bg-yellow-500/20 border border-yellow-500/30 text-yellow-400 text-sm">
          🎭 Simulate mode active: Operations will generate diffs for approval without executing.
        </div>
      )}
    </div>
  );
}
