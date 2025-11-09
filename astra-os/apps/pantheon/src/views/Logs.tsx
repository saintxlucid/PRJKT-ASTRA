/**
 * System Logs View
 * View system events, API calls, and errors
 */

import { useState, useEffect } from 'react';
import { getCurrentTraceId } from '../services/client';

interface LogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  traceId?: string;
}

export default function Logs() {
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      timestamp: new Date().toISOString(),
      level: 'info',
      message: 'System initialized',
    },
    {
      timestamp: new Date(Date.now() - 60000).toISOString(),
      level: 'info',
      message: 'Services connected: Memory (7007), Sigil Gate (7701), Supervisor (7703)',
    },
    {
      timestamp: new Date(Date.now() - 120000).toISOString(),
      level: 'info',
      message: 'UI state loaded from localStorage',
    },
  ]);

  const [currentTrace, setCurrentTrace] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    // Update current trace ID every 500ms
    const interval = setInterval(() => {
      const traceId = getCurrentTraceId();
      if (traceId !== currentTrace) {
        setCurrentTrace(traceId);
      }
    }, 500);

    return () => clearInterval(interval);
  }, [currentTrace]);

  const levelColors = {
    info: 'text-status-info',
    warn: 'text-status-warn',
    error: 'text-status-danger',
    debug: 'text-white/50',
  };

  const levelIcons = {
    info: 'ℹ️',
    warn: '⚠️',
    error: '❌',
    debug: '🔍',
  };

  const filteredLogs =
    filter === 'all' ? logs : logs.filter((log) => log.level === filter);

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">System Logs 📋</h1>
          <p className="text-white/60">Monitor events and trace requests</p>
        </div>
        {currentTrace && (
          <div className="px-4 py-2 bg-accent-teal/20 border border-accent-teal rounded-lg">
            <div className="text-xs text-white/60 mb-1">Active Trace</div>
            <div className="font-mono text-sm text-accent-teal">{currentTrace}</div>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded-lg text-sm transition-colors ${
            filter === 'all'
              ? 'bg-white/20 text-white'
              : 'bg-white/5 text-white/60 hover:bg-white/10'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setFilter('info')}
          className={`px-3 py-1 rounded-lg text-sm transition-colors ${
            filter === 'info'
              ? 'bg-status-info/20 text-status-info'
              : 'bg-white/5 text-white/60 hover:bg-white/10'
          }`}
        >
          Info
        </button>
        <button
          onClick={() => setFilter('warn')}
          className={`px-3 py-1 rounded-lg text-sm transition-colors ${
            filter === 'warn'
              ? 'bg-status-warn/20 text-status-warn'
              : 'bg-white/5 text-white/60 hover:bg-white/10'
          }`}
        >
          Warnings
        </button>
        <button
          onClick={() => setFilter('error')}
          className={`px-3 py-1 rounded-lg text-sm transition-colors ${
            filter === 'error'
              ? 'bg-status-danger/20 text-status-danger'
              : 'bg-white/5 text-white/60 hover:bg-white/10'
          }`}
        >
          Errors
        </button>
      </div>

      {/* Log entries */}
      <div className="flex-1 bg-astra-panel rounded-xl border border-white/10 p-4 overflow-y-auto font-mono text-sm">
        {filteredLogs.length === 0 ? (
          <div className="text-center text-white/40 py-8">
            No {filter !== 'all' ? filter : ''} logs
          </div>
        ) : (
          <div className="space-y-2">
            {filteredLogs.map((log, i) => (
              <div
                key={i}
                className="flex gap-3 py-2 border-b border-white/5 last:border-0"
              >
                <span className="text-white/40 shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className="shrink-0">{levelIcons[log.level]}</span>
                <span className={`shrink-0 uppercase text-xs pt-0.5 ${levelColors[log.level]}`}>
                  {log.level}
                </span>
                <span className="text-white/80">{log.message}</span>
                {log.traceId && (
                  <span className="ml-auto text-accent-teal text-xs">
                    trace:{log.traceId.substring(0, 8)}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer stats */}
      <div className="mt-4 flex gap-4 text-sm text-white/60">
        <div>
          Total logs: <span className="text-white font-medium">{logs.length}</span>
        </div>
        <div>
          Info: <span className="text-status-info font-medium">
            {logs.filter((l) => l.level === 'info').length}
          </span>
        </div>
        <div>
          Warnings: <span className="text-status-warn font-medium">
            {logs.filter((l) => l.level === 'warn').length}
          </span>
        </div>
        <div>
          Errors: <span className="text-status-danger font-medium">
            {logs.filter((l) => l.level === 'error').length}
          </span>
        </div>
      </div>
    </div>
  );
}
