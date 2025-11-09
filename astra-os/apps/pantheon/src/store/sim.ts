import { create } from 'zustand';

export interface NeuralMetrics {
  tick: number;
  avgFiring: number;
  synchrony: number;
  sample: number[];
}

interface SimState {
  running: boolean;
  metrics?: NeuralMetrics;
  drive: number; // last applied external drive (0..1)
  start: () => void;
  stop: () => void;
  setDrive: (v: number) => void;
}

let worker: Worker | null = null;
let visibilityHandler: ((this: Document, ev: Event) => any) | null = null;

export const useNeuralSim = create<SimState>((set) => ({
  running: false,
  drive: 0,
  start: () => {
    if (worker) return;
    worker = new Worker(new URL('../workers/neuralSim.worker.ts', import.meta.url), { type: 'module' });
    worker.onmessage = (ev: MessageEvent) => {
      const { type, payload } = ev.data || {};
      if (type === 'metrics') set({ metrics: payload });
    };
    // throttle node count based on device memory if available
    // @ts-ignore
    const devMem = (navigator as any).deviceMemory || 4;
    worker.postMessage({ type: 'init', nodes: devMem >= 8 ? 384 : 256, dtMs: 33 });
    visibilityHandler = () => {
      if (!worker) return;
      if (document.hidden) {
        // pause loop by stopping worker
        worker.postMessage({ type: 'stop' });
      } else {
        worker.postMessage({ type: 'init' });
      }
    };
    document.addEventListener('visibilitychange', visibilityHandler);
    set({ running: true });
  },
  stop: () => {
    if (worker) {
      worker.postMessage({ type: 'stop' });
      worker.terminate();
      worker = null;
    }
    if (visibilityHandler) {
      document.removeEventListener('visibilitychange', visibilityHandler);
      visibilityHandler = null;
    }
    set({ running: false });
  },
  setDrive: (v: number) => {
    if (worker) worker.postMessage({ type: 'input', drive: v });
    set({ drive: v });
  },
}));

export const selectNeuralMetrics = (s: SimState) => s.metrics;
export const selectSimRunning = (s: SimState) => s.running;
export const selectSimDrive = (s: SimState) => s.drive;
