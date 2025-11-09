/**
 * ASTRA OS Data Layer
 * TanStack Query client configuration and API helpers
 * - Centralized fetch with trace IDs
 * - Retry logic and error handling
 * - Request/response interceptors
 * - Type-safe API calls
 */

import { QueryClient, DefaultOptions } from '@tanstack/react-query';

// Query client configuration
const queryConfig: DefaultOptions = {
  queries: {
    // Stale time: Data considered fresh for 30 seconds
    staleTime: 30_000,
    
    // Cache time: Keep unused data in cache for 5 minutes
    gcTime: 5 * 60 * 1000,
    
    // Retry failed requests twice with exponential backoff
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    
    // Don't refetch on window focus in development
    refetchOnWindowFocus: import.meta.env.PROD,
    
    // Don't refetch on reconnect
    refetchOnReconnect: false,
    
    // Don't refetch on mount
    refetchOnMount: false,
  },
  mutations: {
    // Retry mutations once
    retry: 1,
    retryDelay: 1000,
  },
};

export const queryClient = new QueryClient({ defaultOptions: queryConfig });

// API Error class
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string,
    public body?: unknown
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Generate trace ID for request tracking
export function generateTraceId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older browsers
  return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
}

// Store active trace ID in a global (for Halo display)
let currentTraceId: string | null = null;

export function getCurrentTraceId(): string | null {
  return currentTraceId;
}

export function setCurrentTraceId(traceId: string | null): void {
  currentTraceId = traceId;
}

// Type-safe API client
export interface APIOptions extends RequestInit {
  traceId?: string;
  timeout?: number;
}

/**
 * Generic API fetch wrapper with trace IDs, retries, and error handling
 * @param url - API endpoint URL
 * @param options - Fetch options with trace ID support
 * @returns Typed response data
 */
export async function api<T = unknown>(
  url: string,
  options: APIOptions = {}
): Promise<T> {
  const { traceId = generateTraceId(), timeout = 30000, ...fetchOptions } = options;

  // Store trace ID for Halo display
  setCurrentTraceId(traceId);

  // Merge headers with trace ID
  const headers = new Headers(fetchOptions.headers);
  headers.set('x-trace-id', traceId);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Parse response body
    let body: unknown;
    const contentType = response.headers.get('Content-Type');
    if (contentType?.includes('application/json')) {
      body = await response.json();
    } else {
      body = await response.text();
    }

    // Handle non-2xx responses
    if (!response.ok) {
      const errorMessage =
        typeof body === 'object' && body !== null && 'error' in body
          ? String((body as { error: unknown }).error)
          : `API Error: ${response.status} ${response.statusText}`;

      throw new APIError(errorMessage, response.status, response.statusText, body);
    }

    return body as T;
  } catch (error) {
    clearTimeout(timeoutId);

    // Handle abort (timeout)
    if (error instanceof Error && error.name === 'AbortError') {
      throw new APIError(
        `Request timeout after ${timeout}ms`,
        408,
        'Request Timeout'
      );
    }

    // Handle network errors
    if (error instanceof Error && error.message === 'Failed to fetch') {
      throw new APIError(
        'Network error: Unable to reach server',
        0,
        'Network Error'
      );
    }

    // Re-throw APIError or wrap unknown errors
    if (error instanceof APIError) {
      throw error;
    }

    throw new APIError(
      error instanceof Error ? error.message : 'Unknown error',
      500,
      'Internal Error'
    );
  } finally {
    // Clear trace ID after a delay
    setTimeout(() => {
      if (currentTraceId === traceId) {
        setCurrentTraceId(null);
      }
    }, 1000);
  }
}

// Service-specific API helpers

/**
 * Memory Service API (Port 7007)
 */
export const memoryAPI = {
  baseURL: import.meta.env.VITE_MEMORY_API || 'http://127.0.0.1:7007',

  async search(query: string, limit = 5) {
    return api<{ fragments: Array<{ text: string; score: number }> }>(
      `${this.baseURL}/memory/search`,
      {
        method: 'POST',
        body: JSON.stringify({ query, limit }),
      }
    );
  },

  async add(text: string) {
    return api<{ status: string; id: string }>(
      `${this.baseURL}/memory/add`,
      {
        method: 'POST',
        body: JSON.stringify({ text }),
      }
    );
  },

  async health() {
    return api<{ status: string; model: string; index_size: number }>(
      `${this.baseURL}/health`
    );
  },
};

/**
 * Sigil Gate API (Port 7701)
 */
export const sigilAPI = {
  baseURL: import.meta.env.VITE_SIGIL_API || 'http://127.0.0.1:7701',

  async seal(operator: string, plan: unknown, ttl_secs = 600) {
    return api<{ seal_id: number; expires_at: string }>(
      `${this.baseURL}/seal`,
      {
        method: 'POST',
        body: JSON.stringify({ operator, plan, ttl_secs }),
      }
    );
  },

  async verify(plan: unknown) {
    return api<{ valid: boolean; seal?: unknown }>(
      `${this.baseURL}/verify`,
      {
        method: 'POST',
        body: JSON.stringify({ plan }),
      }
    );
  },

  async journalDelete(seal_id: number, path: string) {
    return api<{ status: string }>(
      `${this.baseURL}/journal/fs/delete`,
      {
        method: 'POST',
        body: JSON.stringify({ seal_id, path }),
      }
    );
  },

  async rollbackLast() {
    return api<{ status: string; rolled_back?: unknown }>(
      `${this.baseURL}/rollback/last`,
      {
        method: 'POST',
      }
    );
  },

  /**
   * Fetch recent journal entries (most recent first)
   * Shape is intentionally flexible; UI will defensively render.
   */
  async journalRecent(limit = 10) {
    return api<{ entries: Array<Record<string, unknown>> }>(
      `${this.baseURL}/journal/recent?limit=${limit}`
    );
  },

  /**
   * Rollback last operation with optional reason.
   * If backend ignores body it remains compatible.
   */
  async rollbackLastWithReason(reason?: string) {
    return api<{ status: string; rolled_back?: unknown }>(
      `${this.baseURL}/rollback/last`,
      {
        method: 'POST',
        body: reason ? JSON.stringify({ reason }) : undefined,
      }
    );
  },

  async health() {
    return api<{ status: string; service: string }>(
      `${this.baseURL}/health`
    );
  },
};

/**
 * Supervisor (Weaver) API (Port 7703)
 */
export const supervisorAPI = {
  baseURL: import.meta.env.VITE_SUPERVISOR_API || 'http://127.0.0.1:7703',

  async createJob(
    type: string,
    payload: Record<string, unknown>,
    priority = 5
  ) {
    return api<{ job_id: string; created_at: string }>(
      `${this.baseURL}/jobs`,
      {
        method: 'POST',
        body: JSON.stringify({ type, payload, priority }),
      }
    );
  },

  async listJobs() {
    return api<{ jobs: Array<{ id: string; type: string; status: string }> }>(
      `${this.baseURL}/jobs`
    );
  },

  async heartbeat(job_id: string) {
    return api<{ status: string }>(
      `${this.baseURL}/jobs/${job_id}/heartbeat`,
      {
        method: 'POST',
      }
    );
  },

  async health() {
    return api<{ status: string; service: string; jobs: number }>(
      `${this.baseURL}/health`
    );
  },
};

// Query key factories (for cache management)
export const queryKeys = {
  // Memory
  memory: {
    all: ['memory'] as const,
    search: (query: string) => [...queryKeys.memory.all, 'search', query] as const,
    health: () => [...queryKeys.memory.all, 'health'] as const,
  },
  // Sigil Gate
  sigil: {
    all: ['sigil'] as const,
    verify: (plan: unknown) => [...queryKeys.sigil.all, 'verify', plan] as const,
    health: () => [...queryKeys.sigil.all, 'health'] as const,
    journal: (limit = 10) => [...queryKeys.sigil.all, 'journal', limit] as const,
  },
  // Supervisor
  supervisor: {
    all: ['supervisor'] as const,
    jobs: () => [...queryKeys.supervisor.all, 'jobs'] as const,
    job: (id: string) => [...queryKeys.supervisor.all, 'job', id] as const,
    health: () => [...queryKeys.supervisor.all, 'health'] as const,
  },
} as const;

// Export everything
export default queryClient;
