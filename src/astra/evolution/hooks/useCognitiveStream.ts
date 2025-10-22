import { useEffect, useRef, useState } from 'react';

interface CognitiveMetrics {
  heads: Array<{
    index: number;
    values: number[];  // -1 to 1, length = tokenCount
  }>;
  memoryWeights: Array<{
    key: string;
    weight: number;  // 0 to 1
  }>;
  moduleActivations: Array<{
    t: number;  // timestep
    planner: number;  // 0 to 1
    memory: number;  // 0 to 1
    tools: number;   // 0 to 1
  }>;
}

interface UseCognitiveStreamOptions {
  onMetrics?: (metrics: CognitiveMetrics) => void;
  onError?: (error: Error) => void;
}

/**
 * Hook for streaming cognitive metrics via WebSocket
 */
export function useCognitiveStream(options: UseCognitiveStreamOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/api/cognitive/stream`);

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt to reconnect after delay
        setTimeout(connect, 3000);
      };

      ws.onerror = (event) => {
        const error = new Error('WebSocket error');
        setError(error);
        options.onError?.(error);
      };

      ws.onmessage = (event) => {
        try {
          const metrics: CognitiveMetrics = JSON.parse(event.data);
          options.onMetrics?.(metrics);
        } catch (err) {
          console.error('Failed to parse cognitive metrics:', err);
          setError(err instanceof Error ? err : new Error('Failed to parse metrics'));
        }
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      wsRef.current?.close();
    };
  }, [options.onMetrics, options.onError]);

  return {
    isConnected,
    error,
    send: (data: any) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(data));
      }
    }
  };
}

/**
 * Hook for streaming cognitive metrics via Server-Sent Events (SSE)
 */
export function useCognitiveSSE(options: UseCognitiveStreamOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const connect = () => {
      const eventSource = new EventSource('/api/cognitive/stream');

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      eventSource.onerror = (event) => {
        setIsConnected(false);
        const error = new Error('EventSource error');
        setError(error);
        options.onError?.(error);
        
        // Attempt to reconnect after delay
        eventSource.close();
        setTimeout(connect, 3000);
      };

      eventSource.addEventListener('metrics', (event) => {
        try {
          const metrics: CognitiveMetrics = JSON.parse(event.data);
          options.onMetrics?.(metrics);
        } catch (err) {
          console.error('Failed to parse cognitive metrics:', err);
          setError(err instanceof Error ? err : new Error('Failed to parse metrics'));
        }
      });

      eventSourceRef.current = eventSource;
    };

    connect();

    return () => {
      eventSourceRef.current?.close();
    };
  }, [options.onMetrics, options.onError]);

  return {
    isConnected,
    error
  };
}

/**
 * Create a mock stream of cognitive metrics for testing
 */
export function createMockCognitiveStream(
  intervalMs: number = 1000,
  tokenCount: number = 64
): () => CognitiveMetrics {
  let t = 0;
  
  return () => {
    // Generate mock metrics
    const metrics: CognitiveMetrics = {
      heads: Array.from({ length: 8 }, (_, i) => ({
        index: i,
        values: Array.from(
          { length: tokenCount },
          () => (Math.random() * 2 - 1) * 0.5 // -0.5 to 0.5
        )
      })),
      memoryWeights: [
        { key: 'recent', weight: 0.8 + Math.sin(t * 0.1) * 0.2 },
        { key: 'episodic', weight: 0.6 + Math.cos(t * 0.15) * 0.2 },
        { key: 'semantic', weight: 0.7 + Math.sin(t * 0.12) * 0.15 }
      ],
      moduleActivations: Array.from(
        { length: Math.min(20, t + 1) },
        (_, i) => ({
          t: i,
          planner: 0.5 + Math.sin(i * 0.3) * 0.3,
          memory: 0.6 + Math.cos(i * 0.25) * 0.25,
          tools: 0.4 + Math.sin(i * 0.35) * 0.35
        })
      )
    };

    t++;
    return metrics;
  };
}