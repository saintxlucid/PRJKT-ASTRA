/**
 * Supervisor service - job orchestration and monitoring
 * Part 5 of Deep Agent & Observability spec
 */

import { fx } from '../lib/fetcher';
import { AgentBus } from '../lib/agentBus';

const SUPERVISOR_BASE = 'http://localhost:7703';
const POLL_INTERVAL = 1500; // 1.5s polling interval

export interface Job {
  id: string;
  state: 'queued' | 'running' | 'complete' | 'failed';
  created: number;
  updated: number;
  result?: unknown;
  error?: string;
}

interface JobsResponse {
  jobs: Job[];
  total: number;
}

let watcherIntervalId: number | null = null;

/**
 * Fetch current jobs from supervisor
 */
export async function getJobs(): Promise<Job[]> {
  const response = await fx(`${SUPERVISOR_BASE}/jobs`);
  if (!response.ok) {
    throw new Error(`Supervisor getJobs failed: ${response.status}`);
  }
  const data: JobsResponse = await response.json();
  return data.jobs;
}

/**
 * Start polling supervisor jobs and emit state changes via AgentBus
 * 
 * @param interval - Polling interval in ms (default 1500ms)
 * @returns Stop function to cancel polling
 * 
 * Emits JOB_STATE events on AgentBus with updated job list
 */
export function watchJobs(interval = POLL_INTERVAL): () => void {
  // Cancel existing watcher if any
  if (watcherIntervalId !== null) {
    clearInterval(watcherIntervalId);
  }
  
  let previousJobStates = new Map<string, string>();
  
  async function poll() {
    try {
      const jobs = await getJobs();
      
      // Check for state changes
      const currentJobStates = new Map(jobs.map(j => [j.id, j.state]));
      let hasChanges = false;
      
      // Detect new or changed jobs
      for (const [id, state] of currentJobStates) {
        if (!previousJobStates.has(id) || previousJobStates.get(id) !== state) {
          hasChanges = true;
          break;
        }
      }
      
      // Detect removed jobs
      if (!hasChanges && previousJobStates.size !== currentJobStates.size) {
        hasChanges = true;
      }
      
      if (hasChanges) {
        // Emit event for each job state change
        jobs.forEach((job) => {
          AgentBus.emit({
            t: 'JOB_STATE',
            id: job.id,
            state: job.state === 'queued' ? 'pending' : 
                   job.state === 'complete' ? 'done' : 
                   job.state as 'running' | 'failed',
            ts: job.updated,
          });
        });
        previousJobStates = currentJobStates;
      }
      
    } catch (error) {
      console.error('[supervisor] Poll failed:', error);
      // Don't emit error events - circuit breaker will handle backoff
    }
  }
  
  // Initial poll
  poll();
  
  // Start interval
  watcherIntervalId = window.setInterval(poll, interval);
  
  // Return stop function
  return () => {
    if (watcherIntervalId !== null) {
      clearInterval(watcherIntervalId);
      watcherIntervalId = null;
    }
  };
}

/**
 * Submit a new job to supervisor
 * 
 * @param jobType - Type of job to submit
 * @param params - Job parameters
 * @returns Job ID
 */
export async function submitJob(jobType: string, params: Record<string, unknown>): Promise<string> {
  const response = await fx(`${SUPERVISOR_BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: jobType, params }),
  });
  
  if (!response.ok) {
    throw new Error(`Supervisor submitJob failed: ${response.status}`);
  }
  
  const data: { id: string } = await response.json();
  return data.id;
}