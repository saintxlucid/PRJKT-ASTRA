let audioCtx: AudioContext | null = null;
let source: MediaStreamAudioSourceNode | null = null;
let analyser: AnalyserNode | null = null;
let rafId: number | null = null;

export async function startMicDrive(onRms: (value01: number) => void): Promise<void> {
  if (audioCtx) return;
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
  source = audioCtx.createMediaStreamSource(stream);
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 1024;
  analyser.smoothingTimeConstant = 0.8;
  source.connect(analyser);
  const data = new Uint8Array(analyser.frequencyBinCount);

  const loop = () => {
    if (!analyser) return;
    analyser.getByteTimeDomainData(data);
    // compute RMS from time-domain
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
      const v = (data[i] - 128) / 128; // [-1,1]
      sum += v * v;
    }
    const rms = Math.sqrt(sum / data.length);
    // Normalize softly and clamp
    const driven = Math.max(0, Math.min(1, rms * 2));
    onRms(driven);
    rafId = requestAnimationFrame(loop);
  };
  loop();
}

export function stopMicDrive(): void {
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null;
  if (analyser) analyser.disconnect();
  if (source) {
    try { (source as any).mediaStream.getTracks().forEach((t: MediaStreamTrack) => t.stop()); } catch { /* noop */ }
    source.disconnect();
  }
  if (audioCtx) audioCtx.close();
  analyser = null; source = null; audioCtx = null;
}
