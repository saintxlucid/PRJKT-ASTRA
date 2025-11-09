import { useEffect, useState, useCallback } from 'react';
import { astraAPI, AgentStatus } from '../lib/api/client';

interface WebSocketState {
  connected: boolean;
  agents: AgentStatus[];
  error: string | null;
}

/**
 * React hook for managing WebSocket connection to ASTRA backend
 * Provides real-time agent status updates
 */
export function useAstraWebSocket() {
  const [state, setState] = useState<WebSocketState>({
    connected: false,
    agents: [],
    error: null,
  });

  useEffect(() => {
    const handleMessage = (data: any) => {
      if (data.type === 'connected') {
        setState((prev) => ({
          ...prev,
          connected: true,
          agents: data.agents || [],
          error: null,
        }));
      } else if (data.type === 'agent_update') {
        setState((prev) => ({
          ...prev,
          agents: data.agents || [],
        }));
      }
    };

    const handleError = (error: Event) => {
      console.error('WebSocket error:', error);
      setState((prev) => ({
        ...prev,
        connected: false,
        error: 'WebSocket connection failed',
      }));
    };

    // Connect WebSocket
    astraAPI.connectWebSocket(handleMessage, handleError);

    // Cleanup on unmount
    return () => {
      astraAPI.disconnectWebSocket();
    };
  }, []);

  const reconnect = useCallback(() => {
    setState((prev) => ({ ...prev, error: null }));
    astraAPI.connectWebSocket(
      (data) => {
        if (data.type === 'connected') {
          setState({
            connected: true,
            agents: data.agents || [],
            error: null,
          });
        } else if (data.type === 'agent_update') {
          setState((prev) => ({
            ...prev,
            agents: data.agents || [],
          }));
        }
      },
      (error) => {
        console.error('WebSocket error:', error);
        setState((prev) => ({
          ...prev,
          connected: false,
          error: 'WebSocket connection failed',
        }));
      }
    );
  }, []);

  return {
    ...state,
    reconnect,
  };
}
