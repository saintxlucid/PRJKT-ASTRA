// A lightweight background neural network simulation running off the main thread.
// Model: simple rate-based recurrent network with tanh activation.
// Posts aggregate metrics at ~30Hz to reduce UI load.

export interface NeuralMetrics {
  tick: number;
  avgFiring: number; // mean |state|
  synchrony: number; // mean correlation proxy
  sample: number[];  // small sample of node states
}

interface InitMsg { type: 'init'; nodes?: number; dtMs?: number; }
interface StopMsg { type: 'stop'; }
interface InputMsg { type: 'input'; drive: number; } // external drive [0,1]
type InMsg = InitMsg | StopMsg | InputMsg;

const randn = () => {
  // Box–Muller
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
};

let N = 256;
let W: Float32Array; // row-major NxN (sparse-like sampled)
let X: Float32Array; // state
let tmp: Float32Array;
let running = false;
let tick = 0;
let drive = 0; // external input [0,1]
let timer: number | null = null;
let dtMs = 33; // ~30Hz

function initWeights() {
  W = new Float32Array(N * N);
  const sparsity = 0.05;
  const gain = 0.9; // below 1 for stability
  for (let i = 0; i < N; i++) {
    for (let j = 0; j < N; j++) {
      const idx = i * N + j;
      if (Math.random() < sparsity) {
        W[idx] = (randn() * 0.5) * gain;
      } else {
        W[idx] = 0;
      }
    }
  }
}

function initState() {
  X = new Float32Array(N);
  tmp = new Float32Array(N);
  for (let i = 0; i < N; i++) X[i] = Math.random() * 0.2 - 0.1;
}

function stepOnce() {
  // x_{t+1} = tanh(W x_t + u)
  // naive mat-vec; N kept modest (<=512) to keep worker light.
  for (let i = 0; i < N; i++) {
    let s = 0;
    const row = i * N;
    for (let j = 0; j < N; j++) {
      const w = W[row + j];
      if (w !== 0) s += w * X[j];
    }
    // external drive targets a small subset for interest
    s += drive * (i % 7 === 0 ? 1.0 : 0.1);
    // tanh approx
    tmp[i] = Math.tanh(s);
  }
  // swap
  const t = X; X = tmp; tmp = t;
}

function computeMetrics(): NeuralMetrics {
  let meanAbs = 0;
  for (let i = 0; i < N; i++) meanAbs += Math.abs(X[i]);
  meanAbs /= N;
  // synchrony: std of X as proxy for coherence (lower std ~ more synchrony for mean-zero)
  let mean = 0; for (let i = 0; i < N; i++) mean += X[i]; mean /= N;
  let varSum = 0; for (let i = 0; i < N; i++) { const d = X[i] - mean; varSum += d * d; }
  const std = Math.sqrt(varSum / N);
  const synchrony = Math.max(0, 1 - Math.min(1, std));

  const sampleCount = Math.min(24, N);
  const sample: number[] = [];
  const stride = Math.floor(N / sampleCount);
  for (let i = 0; i < sampleCount; i++) sample.push(X[i * stride]);
  return { tick, avgFiring: meanAbs, synchrony, sample };
}

function loop() {
  if (!running) return;
  stepOnce();
  tick++;
  if (tick % 2 === 0) {
    // ~15Hz metrics
    const metrics = computeMetrics();
    // @ts-ignore
    postMessage({ type: 'metrics', payload: metrics });
  }
  timer = setTimeout(loop, dtMs) as unknown as number;
}

function start() {
  if (running) return;
  running = true;
  loop();
}

function stop() {
  running = false;
  if (timer) { clearTimeout(timer); timer = null; }
}

self.onmessage = (ev: MessageEvent<InMsg>) => {
  const msg = ev.data;
  if (msg.type === 'init') {
    if (typeof msg.nodes === 'number') N = Math.max(32, Math.min(512, msg.nodes));
    if (typeof msg.dtMs === 'number') dtMs = Math.max(16, msg.dtMs);
    initWeights();
    initState();
    start();
    return;
  }
  if (msg.type === 'stop') {
    stop();
    return;
  }
  if (msg.type === 'input') {
    drive = Math.max(0, Math.min(1, msg.drive));
    return;
  }
};

// Auto-init with defaults
initWeights();
initState();
start();
