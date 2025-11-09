/**
 * AgentPanel - Real-time agent activity monitoring
 * Part 1 of Deep Agent & Observability spec
 */

import { useEffect, useState } from 'react';
import { AgentBus, type AgentEvent } from '../lib/agentBus';

interface JobDisplay {
  id: string;
  state: 'pending' | 'running' | 'paused' | 'done' | 'failed';
  ts: number;
  age: string;
}

interface ConsentRequest {
  planDigest: string;
  scopes: string[];
  ts: number;
}

interface RollbackNotification {
  tokenId: number;
  reason?: string;
  ts: number;
}

function formatAge(ts: number): string {
  const seconds = Math.floor((Date.now() - ts) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

function getStateColor(state: JobDisplay['state']): string {
  switch (state) {
    case 'pending': return 'text-yellow-400';
    case 'running': return 'text-blue-400';
    case 'paused': return 'text-orange-400';
    case 'done': return 'text-green-400';
    case 'failed': return 'text-red-400';
  }
}

export function AgentPanel() {
  const [jobs, setJobs] = useState<Map<string, JobDisplay>>(new Map());
  const [consents, setConsents] = useState<ConsentRequest[]>([]);
  const [rollbacks, setRollbacks] = useState<RollbackNotification[]>([]);

  useEffect(() => {
    const unsubscribe = AgentBus.on((event: AgentEvent) => {
      if (event.t === 'JOB_STATE') {
        setJobs((prev) => {
          const next = new Map(prev);
          next.set(event.id, {
            id: event.id,
            state: event.state,
            ts: event.ts,
            age: formatAge(event.ts),
          });
          return next;
        });
      } else if (event.t === 'CONSENT_REQUIRED') {
        setConsents((prev) => [
          ...prev.slice(-9), // Keep last 10
          { planDigest: event.planDigest, scopes: event.scopes, ts: event.ts },
        ]);
      } else if (event.t === 'ROLLBACK_READY') {
        setRollbacks((prev) => [
          ...prev.slice(-9), // Keep last 10
          { tokenId: event.tokenId, reason: event.reason, ts: event.ts },
        ]);
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  // Update job ages every second
  useEffect(() => {
    const interval = setInterval(() => {
      setJobs((prev) => {
        const next = new Map(prev);
        next.forEach((job) => {
          job.age = formatAge(job.ts);
        });
        return new Map(next);
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const jobList = Array.from(jobs.values()).sort((a, b) => b.ts - a.ts);

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div className="border-b border-astra-border pb-4">
        <h1 className="text-2xl font-bold text-astra-text-primary">Agent Panel</h1>
        <p className="text-sm text-astra-text-secondary mt-1">
          Real-time monitoring of agent activities and job states
        </p>
      </div>

      {/* Job States Section */}
      <section aria-label="Job States">
        <h2 className="text-lg font-semibold text-astra-text-primary mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          Job States
          <span className="text-xs font-normal text-astra-text-secondary ml-auto">
            {jobList.length} active
          </span>
        </h2>
        
        {jobList.length === 0 ? (
          <div 
            className="bg-astra-card border border-astra-border rounded-lg p-4 text-center text-astra-text-secondary"
            role="status"
          >
            No active jobs. Waiting for supervisor events...
          </div>
        ) : (
          <ul className="space-y-2" role="list">
            {jobList.map((job) => (
              <li
                key={job.id}
                className="bg-astra-card border border-astra-border rounded-lg p-3 hover:border-astra-hover transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className={`font-mono text-sm ${getStateColor(job.state)} font-semibold uppercase`}>
                      {job.state}
                    </span>
                    <code className="text-xs text-astra-text-secondary truncate">
                      {job.id}
                    </code>
                  </div>
                  <span className="text-xs text-astra-text-muted ml-3">
                    {job.age}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Consent Requests Section */}
      <section aria-label="Consent Requests">
        <h2 className="text-lg font-semibold text-astra-text-primary mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-400" />
          Recent Consent Requests
          <span className="text-xs font-normal text-astra-text-secondary ml-auto">
            {consents.length}
          </span>
        </h2>
        
        {consents.length === 0 ? (
          <div 
            className="bg-astra-card border border-astra-border rounded-lg p-4 text-center text-astra-text-secondary"
            role="status"
          >
            No consent requests logged
          </div>
        ) : (
          <ul className="space-y-2" role="list">
            {consents.slice().reverse().map((consent, idx) => (
              <li
                key={`${consent.ts}-${idx}`}
                className="bg-astra-card border border-astra-border rounded-lg p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <code className="text-xs text-amber-400 block truncate">
                      {consent.planDigest.slice(0, 16)}...
                    </code>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {consent.scopes.map((scope) => (
                        <span
                          key={scope}
                          className="text-xs px-2 py-0.5 bg-astra-elevated text-astra-text-secondary rounded"
                        >
                          {scope}
                        </span>
                      ))}
                    </div>
                  </div>
                  <span className="text-xs text-astra-text-muted whitespace-nowrap">
                    {formatAge(consent.ts)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Rollback Notifications Section */}
      <section aria-label="Rollback Notifications">
        <h2 className="text-lg font-semibold text-astra-text-primary mb-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-400" />
          Recent Rollbacks
          <span className="text-xs font-normal text-astra-text-secondary ml-auto">
            {rollbacks.length}
          </span>
        </h2>
        
        {rollbacks.length === 0 ? (
          <div 
            className="bg-astra-card border border-astra-border rounded-lg p-4 text-center text-astra-text-secondary"
            role="status"
          >
            No rollbacks logged
          </div>
        ) : (
          <ul className="space-y-2" role="list">
            {rollbacks.slice().reverse().map((rollback, idx) => (
              <li
                key={`${rollback.ts}-${idx}`}
                className="bg-astra-card border border-astra-border rounded-lg p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-red-400">
                        Token #{rollback.tokenId}
                      </span>
                      {rollback.reason && (
                        <span className="text-xs text-astra-text-secondary">
                          {rollback.reason}
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs text-astra-text-muted whitespace-nowrap">
                    {formatAge(rollback.ts)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}