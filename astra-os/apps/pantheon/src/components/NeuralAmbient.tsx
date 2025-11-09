import { useEffect, useMemo, useState } from 'react';
import { useNeuralSim, selectNeuralMetrics } from '../store/sim';

export default function NeuralAmbient() {
  const metrics = useNeuralSim(selectNeuralMetrics);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000 / 12);
    return () => clearInterval(id);
  }, []);

  const bars = useMemo(() => {
    const n = 48;
    const sample = metrics?.sample ?? Array.from({ length: n }, () => 0);
    const stride = Math.max(1, Math.floor(sample.length / n));
    return Array.from({ length: n }, (_, i) => sample[Math.min(sample.length - 1, i * stride)] ?? 0);
  }, [metrics, tick]);

  const bucket = (v: number) => Math.max(0, Math.min(10, Math.round(Math.min(1, Math.abs(v) * 3) * 10)));

  return (
    <div className="pointer-events-none absolute inset-0 opacity-20">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(18,18,36,0.8),rgba(0,0,0,0))]" />
      <div className="absolute bottom-6 left-[calc(var(--layout-spine-width-expanded))] right-[calc(var(--layout-pulse-width))] px-8">
        <div className="grid grid-cols-12 gap-1">
          {bars.map((v, i) => (
            <div key={i} className="h-2 rounded bg-gradient-to-r from-indigo-400/30 to-fuchsia-400/30 overflow-hidden">
              <div className={`h-full bg-indigo-400/50 neural-scale-${bucket(v)}`} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
