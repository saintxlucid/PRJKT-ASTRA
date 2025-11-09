import { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Settings, Download, Radio, AlertCircle } from 'lucide-react';
import { astraAPI } from '@/lib/api/client';

interface VoiceSession {
  id: string;
  transcript: string;
  response: string;
  timestamp: Date;
  duration: number;
  confidence?: number;
}

interface AudioLevel {
  input: number;
  output: number;
}

export function SeraphVoice() {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [audioLevels, setAudioLevels] = useState<AudioLevel>({ input: 0, output: 0 });
  const [sessions, setSessions] = useState<VoiceSession[]>([]);
  const [settings, setSettings] = useState({
    language: 'en-US',
    voiceSpeed: 1.0,
    autoListen: false,
    pushToTalk: true
  });
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);

  // Simulated audio visualization
  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const width = canvas.width;
      const height = canvas.height;
      
      ctx.clearRect(0, 0, width, height);
      
      // Background gradient
      const gradient = ctx.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, 'rgba(139, 92, 246, 0.1)');
      gradient.addColorStop(1, 'rgba(16, 185, 129, 0.1)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      if (isListening || isSpeaking) {
        // Draw waveform with real audio levels
        const level = isListening ? audioLevels.input : audioLevels.output;
        const bars = 50;
        const barWidth = width / bars;
        
        ctx.fillStyle = isListening ? '#10b981' : '#8b5cf6';
        
        for (let i = 0; i < bars; i++) {
          const amplitude = Math.sin(Date.now() * 0.005 + i * 0.3) * 0.5 + 0.5;
          const barHeight = (height * 0.8 * amplitude * (level / 100)) + 2;
          const x = i * barWidth;
          const y = (height - barHeight) / 2;
          
          const alpha = 0.6 + (amplitude * 0.4);
          ctx.globalAlpha = alpha;
          ctx.fillRect(x, y, barWidth - 2, barHeight);
        }
        
        ctx.globalAlpha = 1;
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isListening, isSpeaking, audioLevels]);

  // Update audio levels from analyser
  useEffect(() => {
    if (!analyserRef.current || !isListening) return;

    const updateLevels = () => {
      if (!analyserRef.current) return;

      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
      analyserRef.current.getByteFrequencyData(dataArray);
      
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      const level = (average / 255) * 100;
      
      setAudioLevels(prev => ({ ...prev, input: level }));
    };

    const intervalId = setInterval(updateLevels, 100);
    return () => clearInterval(intervalId);
  }, [isListening]);

  const startListening = async () => {
    try {
      setError(null);
      setIsRecording(true);
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      });
      
      audioStreamRef.current = stream;

      // Set up audio analysis
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      analyserRef.current.fftSize = 256;

      // Set up media recorder
      audioChunksRef.current = [];
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        await handleRecordingComplete();
      };

      mediaRecorderRef.current.start();
      setIsListening(true);
      setCurrentTranscript('');
      
    } catch (err) {
      console.error('Error accessing microphone:', err);
      setError('Failed to access microphone. Please check permissions.');
      setIsRecording(false);
    }
  };

  const stopListening = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => track.stop());
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    setIsListening(false);
    setIsRecording(false);
    setAudioLevels({ input: 0, output: 0 });
  };

  const handleRecordingComplete = async () => {
    try {
      setIsProcessing(true);
      
      // Create audio blob
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      
      // Send to backend for transcription
      const transcriptResult = await astraAPI.transcribeAudio(audioBlob);
      
      setCurrentTranscript(transcriptResult.text);
      
      // Process with ASTRA agent
      await handleProcessTranscript(transcriptResult.text, transcriptResult.confidence);
      
    } catch (err) {
      console.error('Error processing audio:', err);
      setError('Failed to transcribe audio. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleProcessTranscript = async (transcript: string, confidence?: number) => {
    const startTime = Date.now();
    
    try {
      setIsSpeaking(true);
      setError(null);
      
      // Send transcript to chat API for AI response
      const chatResponse = await astraAPI.sendChatMessage({
        messages: [
          { role: 'user', content: transcript }
        ],
        agent_id: 'cognitive-core',
        stream: false
      });
      
      const response = chatResponse.message;
      
      // Save session
      const session: VoiceSession = {
        id: Date.now().toString(),
        transcript,
        response,
        timestamp: new Date(),
        duration: (Date.now() - startTime) / 1000,
        confidence
      };
      
      setSessions(prev => [session, ...prev]);
      setCurrentTranscript('');
      
      // Synthesize speech (placeholder - audio playback would go here)
      await astraAPI.synthesizeSpeech(response);
      
      // Simulate speaking duration
      setTimeout(() => {
        setIsSpeaking(false);
      }, 2000);
      
    } catch (err) {
      console.error('Error processing transcript:', err);
      setError('Failed to get AI response. Please try again.');
      setIsSpeaking(false);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const exportSessions = () => {
    const content = sessions
      .map(s => `[${s.timestamp.toLocaleString()}]\nYou: ${s.transcript}\nASTRA: ${s.response}\n`)
      .join('\n---\n\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seraph-voice-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col bg-obsidian-900">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-white/10 bg-obsidian-800/50 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-4xl sigil animate-breathe">⚡</div>
            <div>
              <h1 className="text-2xl font-semibold text-text-primary">Seraph Voice</h1>
              <p className="text-sm text-text-secondary">Natural voice conversation with ASTRA</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="px-4 py-2 bg-obsidian-700/50 rounded-lg border border-white/10">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-lucid-violet" />
                <span className="text-sm text-text-primary">
                  {isProcessing ? 'Processing...' : isListening ? 'Listening...' : isSpeaking ? 'Speaking...' : 'Ready'}
                </span>
              </div>
            </div>
            
            <button
              onClick={exportSessions}
              className="p-2 hover:bg-white/5 rounded-lg transition-colors"
              title="Export sessions"
              disabled={sessions.length === 0}
            >
              <Download className="w-5 h-5 text-text-secondary" />
            </button>
            
            <button className="p-2 hover:bg-white/5 rounded-lg transition-colors" title="Settings">
              <Settings className="w-5 h-5 text-text-secondary" />
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mt-4 p-3 bg-status-error/10 border border-status-error/30 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-status-error flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-status-error">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-status-error hover:text-status-error/80 text-sm"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Main Voice Interface */}
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="w-full max-w-4xl">
          {/* Waveform Visualization */}
          <div className="mb-8">
            <canvas
              ref={canvasRef}
              width={800}
              height={200}
              className="w-full h-48 rounded-lg border border-white/10 bg-obsidian-800/50"
            />
          </div>

          {/* Current Transcript */}
          {(currentTranscript || isProcessing) && (
            <div className="mb-8 p-6 bg-obsidian-800/50 border border-white/10 rounded-lg">
              <div className="flex items-start gap-3">
                <Mic className="w-5 h-5 text-lucid-mint flex-shrink-0 mt-1" />
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-text-secondary mb-2">
                    {isProcessing ? 'Processing transcription...' : 'Transcription'}
                  </h3>
                  {currentTranscript ? (
                    <p className="text-lg text-text-primary leading-relaxed">{currentTranscript}</p>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-lucid-mint rounded-full animate-pulse" />
                      <span className="text-sm text-text-muted">Transcribing audio...</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Voice Controls */}
          <div className="flex items-center justify-center gap-6 mb-8">
            {/* Push-to-Talk Button */}
            <button
              onClick={toggleListening}
              disabled={isSpeaking || isProcessing}
              className={`relative w-24 h-24 rounded-full transition-all duration-300 ${
                isListening
                  ? 'bg-gradient-to-br from-lucid-mint to-status-success shadow-lg shadow-lucid-mint/50 scale-110'
                  : isProcessing || isSpeaking
                  ? 'bg-gradient-to-br from-lucid-violet/50 to-lucid-teal/50 opacity-50'
                  : 'bg-gradient-to-br from-lucid-violet to-lucid-teal hover:scale-105'
              } disabled:cursor-not-allowed`}
              title={
                isProcessing 
                  ? 'Processing...' 
                  : isSpeaking 
                  ? 'ASTRA is speaking...' 
                  : isListening 
                  ? 'Stop listening' 
                  : 'Start listening'
              }
            >
              {isListening && (
                <div className="absolute inset-0 rounded-full bg-white/20 animate-ping opacity-75" />
              )}
              {isListening ? (
                <MicOff className="w-10 h-10 text-white relative z-10 mx-auto" />
              ) : (
                <Mic className="w-10 h-10 text-white relative z-10 mx-auto" />
              )}
            </button>

            {/* Audio Level Meters */}
            <div className="flex flex-col gap-3">
              {/* Input Level */}
              <div className="flex items-center gap-3">
                <Volume2 className="w-5 h-5 text-text-secondary" />
                <div className="w-40 h-2 bg-obsidian-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-lucid-mint to-status-success transition-all duration-100"
                    style={{ width: `${audioLevels.input}%` }}
                  />
                </div>
                <span className="text-xs text-text-muted font-mono w-8">{Math.round(audioLevels.input)}%</span>
              </div>

              {/* Output Level */}
              <div className="flex items-center gap-3">
                <VolumeX className="w-5 h-5 text-text-secondary" />
                <div className="w-40 h-2 bg-obsidian-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-lucid-violet to-lucid-teal transition-all duration-100"
                    style={{ width: `${audioLevels.output}%` }}
                  />
                </div>
                <span className="text-xs text-text-muted font-mono w-8">{Math.round(audioLevels.output)}%</span>
              </div>
            </div>
          </div>

          {/* Instructions */}
          <div className="text-center">
            <p className="text-text-secondary text-sm mb-1">
              {settings.pushToTalk ? 'Click and hold to speak' : 'Click to toggle voice input'}
            </p>
            <p className="text-text-muted text-xs">
              Voice recognition powered by Whisper • Synthesis by TTS
            </p>
          </div>
        </div>
      </div>

      {/* Session History */}
      {sessions.length > 0 && (
        <div className="flex-shrink-0 border-t border-white/10 bg-obsidian-800/30 backdrop-blur-sm">
          <div className="px-6 py-4">
            <h3 className="text-sm font-medium text-text-secondary mb-3">
              Recent Sessions ({sessions.length})
            </h3>
            <div className="space-y-2 max-h-48 overflow-y-auto scroll-smooth-obsidian">
              {sessions.slice(0, 5).map(session => (
                <div
                  key={session.id}
                  className="p-3 bg-obsidian-700/30 border border-white/5 rounded-lg hover:bg-obsidian-700/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm text-text-primary truncate flex-1">
                          <span className="text-text-muted">You:</span> {session.transcript}
                        </p>
                        {session.confidence && (
                          <span className="text-xs text-lucid-mint font-mono flex-shrink-0">
                            {(session.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-text-secondary truncate">
                        <span className="text-text-muted">ASTRA:</span> {session.response}
                      </p>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <p className="text-xs text-text-muted">
                        {session.timestamp.toLocaleTimeString()}
                      </p>
                      <p className="text-xs text-text-muted">
                        {session.duration.toFixed(1)}s
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
