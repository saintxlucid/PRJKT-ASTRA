import { useState, useEffect } from 'react';
import { useNeuralSim, selectNeuralMetrics, selectSimDrive } from '../store/sim';
import Button from './ui/Button';
import { startMicDrive, stopMicDrive } from '../services/audio/micDrive';
import { Meter } from '../lib/metrics';

interface Metric {
  label: string;
  value: string;
  unit: string;
  status: 'good' | 'warning' | 'critical';
}

export default function Pulse() {
  const [metrics, setMetrics] = useState<Metric[]>([
    { label: 'CPU', value: '0', unit: '%', status: 'good' },
    { label: 'Memory', value: '0', unit: 'MB', status: 'good' },
    { label: 'Req/s', value: '0', unit: '', status: 'good' },
    { label: 'Latency', value: '0', unit: 'ms', status: 'good' },
  ]);

  // Subscribe to neural simulation metrics
  const neuralMetrics = useNeuralSim(selectNeuralMetrics);
  const drive = useNeuralSim(selectSimDrive);
  const setDrive = useNeuralSim((s) => s.setDrive);
  const [micOn, setMicOn] = useState(false);

  useEffect(() => {
    // Replace random metrics with evolving simulated neural network indicators
    const interval = setInterval(() => {
      const cpuLoad = neuralMetrics ? (neuralMetrics.avgFiring * 70 + 20) : Math.random() * 60 + 20;
      const reqRate = neuralMetrics ? (neuralMetrics.synchrony * 40 + 10) : Math.random() * 50 + 10;
      const latency = neuralMetrics ? (800 - neuralMetrics.synchrony * 600) : Math.random() * 800 + 200;
      setMetrics([
        {
          label: 'CPU',
          value: cpuLoad.toFixed(1),
          unit: '%',
          status: cpuLoad > 75 ? 'warning' : 'good'
        },
        {
          label: 'Memory',
          value: (Math.random() * 2048 + 1024).toFixed(0),
          unit: 'MB',
          status: 'good'
        },
        {
          label: 'Req/s',
          value: reqRate.toFixed(0),
          unit: '',
          status: 'good'
        },
        {
          label: 'Latency',
          value: latency.toFixed(0),
          unit: 'ms',
          status: latency > 900 ? 'warning' : 'good'
        }
      ]);
    }, 1000);
    return () => clearInterval(interval);
  }, [neuralMetrics]);

  const statusColors = {
    good: 'border-emerald-500/30 bg-emerald-500/10',
    warning: 'border-yellow-500/30 bg-yellow-500/10',
    critical: 'border-rose-500/30 bg-rose-500/10',
  };

  const valueColors = {
    good: 'text-emerald-400',
    warning: 'text-yellow-400',
    critical: 'text-rose-400',
  };

  const bucketClass = (v: number) => {
    const b = Math.max(0, Math.min(10, Math.round(Math.min(1, Math.abs(v) * 3) * 10)));
    return `neural-scale-${b}`;
  };

  const toggleMic = async () => {
    if (!micOn) {
      try {
        await startMicDrive(setDrive);
        setMicOn(true);
      } catch (e) {
        console.warn('Mic permission failed:', e);
      }
    } else {
      stopMicDrive();
      setMicOn(false);
      setDrive(0);
    }
  };

  return (
    <aside className="w-64 bg-white/5 backdrop-blur-sm border-l border-white/10 p-4">
      <h2 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-4">System Pulse</h2>
      
      <div className="space-y-3">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className={`p-3 rounded border ${statusColors[metric.status]} transition-colors`}
          >
            <div className="text-xs text-white/60 mb-1">{metric.label}</div>
            <div className="flex items-baseline gap-1">
              <span className={`text-2xl font-bold ${valueColors[metric.status]}`}>
                {metric.value}
              </span>
              <span className="text-sm text-white/40">{metric.unit}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 pt-6 border-t border-white/10">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">API Latency</h3>
        <div className="space-y-2 text-xs" role="status" aria-live="polite" aria-label="API latency metrics">
          <div className="flex justify-between">
            <span className="text-white/60">Memory</span>
            <span className="text-emerald-400 font-mono">
              {Meter.apiLatencyMs.memory > 0 ? `${Math.round(Meter.apiLatencyMs.memory)}ms` : '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/60">Sigil</span>
            <span className="text-emerald-400 font-mono">
              {Meter.apiLatencyMs.sigil > 0 ? `${Math.round(Meter.apiLatencyMs.sigil)}ms` : '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/60">Supervisor</span>
            <span className="text-emerald-400 font-mono">
              {Meter.apiLatencyMs.supervisor > 0 ? `${Math.round(Meter.apiLatencyMs.supervisor)}ms` : '—'}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-6 pt-6 border-t border-white/10">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">Web Vitals</h3>
        <div className="space-y-2 text-xs" role="status" aria-live="polite" aria-label="Web vitals metrics">
          <div className="flex justify-between">
            <span className="text-white/60">LCP</span>
            <span className="text-cyan-400 font-mono">
              {Meter.vitals.LCP > 0 ? `${Math.round(Meter.vitals.LCP)}ms` : '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/60">FID</span>
            <span className="text-cyan-400 font-mono">
              {Meter.vitals.FID > 0 ? `${Math.round(Meter.vitals.FID)}ms` : '—'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-white/60">CLS</span>
            <span className="text-cyan-400 font-mono">
              {Meter.vitals.CLS > 0 ? Meter.vitals.CLS.toFixed(3) : '—'}
            </span>
          </div>
        </div>
      </div>

      {neuralMetrics && (
        <div className="mt-6 pt-6 border-t border-white/10">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider">Neural Simulation</h3>
            <div className="flex items-center gap-2">
              <span className="text-xs text-white/50">Drive</span>
              <span className="text-xs font-mono text-white/70 w-10 text-right">{drive.toFixed(2)}</span>
              <Button size="sm" variant={micOn ? 'primary' : 'ghost'} onClick={toggleMic}>{micOn ? 'Mic On' : 'Use Mic'}</Button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
            <div className="flex justify-between"><span className="text-white/60">Tick</span><span className="text-white/80">{neuralMetrics.tick}</span></div>
            <div className="flex justify-between"><span className="text-white/60">Avg Firing</span><span className="text-emerald-400">{neuralMetrics.avgFiring.toFixed(3)}</span></div>
            <div className="flex justify-between"><span className="text-white/60">Synchrony</span><span className="text-cyan-400">{neuralMetrics.synchrony.toFixed(3)}</span></div>
          </div>
          <div className="mt-3 grid grid-cols-6 gap-1">
            {neuralMetrics.sample.map((v, i) => (
              <div key={i} className="h-4 rounded bg-gradient-to-br from-indigo-500/40 to-fuchsia-500/40 relative overflow-hidden">
                <div className={`absolute inset-0 bg-indigo-400/60 ${bucketClass(v)}`} />
              </div>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
