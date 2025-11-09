import React, { useState, useEffect } from 'react';
import { Activity, Zap, Clock, Target, Sparkles, ChevronRight } from 'lucide-react';
import { useAstraWebSocket } from '@/hooks/useAstraWebSocket';
import { astraAPI, type AgentStatus as APIAgentStatus, type FlowSession } from '@/lib/api/client';

interface AgentStatus {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'thinking' | 'error';
  currentTask?: string;
  progress?: number;
  lastActive: Date;
}

interface ActiveJob {
  id: string;
  title: string;
  agent: string;
  progress: number;
  eta: string;
  status: 'running' | 'paused' | 'queued';
}

interface FlowState {
  level: number; // 0-100
  duration: number; // minutes
  phase: 'warmup' | 'deep' | 'peak' | 'cooldown' | 'idle';
}

export function AeonDeck() {
  // Real-time WebSocket connection for agent updates
  const { agents: wsAgents, connected } = useAstraWebSocket();

  // Convert API agent status to local format
  const agents = wsAgents.map(agent => ({
    id: agent.id,
    name: agent.name,
    status: agent.status === 'online' ? 'active' as const : 
            agent.status === 'busy' ? 'thinking' as const : 'idle' as const,
    currentTask: agent.current_task,
    progress: agent.progress,
    lastActive: new Date(agent.last_active)
  }));

  const [activeJobs, setActiveJobs] = useState<ActiveJob[]>([
    {
      id: 'j1',
      title: 'Deep Research: Neural Architecture',
      agent: 'Cognitive Core',
      progress: 67,
      eta: '4m 23s',
      status: 'running'
    },
    {
      id: 'j2',
      title: 'Memory Consolidation Cycle',
      agent: 'Memory Weaver',
      progress: 42,
      eta: '8m 12s',
      status: 'running'
    }
  ]);

  const [flowState, setFlowState] = useState<FlowState>({
    level: 78,
    duration: 42,
    phase: 'deep'
  });

  const [currentTime, setCurrentTime] = useState(new Date());

  // Fetch flow state on mount
  useEffect(() => {
    astraAPI.getFlowStatus().then(flow => {
      setFlowState({
        level: flow.level,
        duration: flow.duration,
        phase: flow.phase
      });
    }).catch(err => console.error('Failed to fetch flow status:', err));
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const getStatusColor = (status: AgentStatus['status']) => {
    switch (status) {
      case 'active': return 'text-[#36C790]';
      case 'thinking': return 'text-[#77DDE8]';
      case 'idle': return 'text-[#7D8491]';
      case 'error': return 'text-[#E94B35]';
    }
  };

  const getStatusIcon = (status: AgentStatus['status']) => {
    switch (status) {
      case 'active': return <Zap className="w-4 h-4" />;
      case 'thinking': return <Activity className="w-4 h-4 animate-pulse" />;
      case 'idle': return <Clock className="w-4 h-4" />;
      case 'error': return <Target className="w-4 h-4" />;
    }
  };

  const getPhaseColor = (phase: FlowState['phase']) => {
    switch (phase) {
      case 'warmup': return 'from-[#EFB65B] to-[#77DDE8]';
      case 'deep': return 'from-[#77DDE8] to-[#36C790]';
      case 'peak': return 'from-[#36C790] to-[#C9B37E]';
      case 'cooldown': return 'from-[#A787FF] to-[#7D8491]';
      case 'idle': return 'from-[#7D8491] to-[#101113]';
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-[#EDEFF3] mb-2 flex items-center gap-4">
            ÆON Deck
            <span className="text-2xl opacity-60">∞</span>
            {/* Connection Status Indicator */}
            <span className={`text-xs px-3 py-1 rounded-full ${connected ? 'bg-[#36C790]/20 text-[#36C790]' : 'bg-[#E94B35]/20 text-[#E94B35]'}`}>
              {connected ? '● Live' : '○ Disconnected'}
            </span>
          </h1>
          <p className="text-[#B8BDC7] text-sm">
            {currentTime.toLocaleDateString('en-US', { 
              weekday: 'long', 
              year: 'numeric', 
              month: 'long', 
              day: 'numeric' 
            })}
            <span className="ml-4">{currentTime.toLocaleTimeString()}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 bg-gradient-to-br from-[#77DDE8] to-[#36C790] text-[#0A0A0B] rounded-md font-semibold hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5">
            <Sparkles className="w-4 h-4 inline mr-2" />
            New Flow Session
          </button>
        </div>
      </div>

      {/* Flow State Card */}
      <div className="card-base p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-[#EDEFF3]">Flow State</h2>
          <span className={`text-sm font-medium px-3 py-1 rounded-full bg-gradient-to-r ${getPhaseColor(flowState.phase)} text-[#0A0A0B]`}>
            {flowState.phase.toUpperCase()}
          </span>
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-[#B8BDC7]">Flow Depth</span>
              <span className="text-[#77DDE8] font-semibold">{flowState.level}%</span>
            </div>
            <div className="h-3 bg-[#101113] rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-[#77DDE8] to-[#36C790] transition-all duration-500 sigil"
                style={{ width: `${flowState.level}%` }}
              />
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-[#B8BDC7]">Active Duration</span>
            <span className="text-[#EDEFF3] font-medium">{flowState.duration} minutes</span>
          </div>

          <div className="grid grid-cols-4 gap-2 pt-2">
            <button className="btn-secondary text-xs py-2">
              <Clock className="w-3 h-3 inline mr-1" />
              25 min
            </button>
            <button className="btn-secondary text-xs py-2">
              <Clock className="w-3 h-3 inline mr-1" />
              50 min
            </button>
            <button className="btn-secondary text-xs py-2">
              <Clock className="w-3 h-3 inline mr-1" />
              90 min
            </button>
            <button className="btn-primary text-xs py-2">
              <Target className="w-3 h-3 inline mr-1" />
              Custom
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Agent Status */}
        <div className="card-base p-6">
          <h2 className="text-lg font-semibold text-[#EDEFF3] mb-4">Agent Status</h2>
          <div className="space-y-3">
            {agents.map(agent => (
              <div key={agent.id} className="card-elevated p-4 hover:bg-[#121416] transition-colors cursor-pointer">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={getStatusColor(agent.status)}>
                      {getStatusIcon(agent.status)}
                    </span>
                    <span className="text-[#EDEFF3] font-medium">{agent.name}</span>
                  </div>
                  <span className="text-xs text-[#7D8491]">
                    {Math.floor((Date.now() - agent.lastActive.getTime()) / 1000)}s ago
                  </span>
                </div>

                {agent.currentTask && (
                  <div className="mt-2">
                    <p className="text-sm text-[#B8BDC7] mb-2">{agent.currentTask}</p>
                    {agent.progress !== undefined && (
                      <div className="h-1.5 bg-[#0A0A0B] rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-[#77DDE8] to-[#36C790]"
                          style={{ width: `${agent.progress}%` }}
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          <button className="w-full mt-4 btn-secondary py-2 text-sm">
            View All Agents
            <ChevronRight className="w-4 h-4 inline ml-1" />
          </button>
        </div>

        {/* Active Jobs */}
        <div className="card-base p-6">
          <h2 className="text-lg font-semibold text-[#EDEFF3] mb-4">Active Jobs</h2>
          <div className="space-y-3">
            {activeJobs.map(job => (
              <div key={job.id} className="card-elevated p-4 hover:bg-[#121416] transition-colors cursor-pointer">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-[#EDEFF3] font-medium text-sm">{job.title}</h3>
                  <span className="text-xs text-[#77DDE8] font-medium">{job.eta}</span>
                </div>

                <p className="text-xs text-[#7D8491] mb-3">{job.agent}</p>

                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-[#B8BDC7]">Progress</span>
                    <span className="text-[#EDEFF3]">{job.progress}%</span>
                  </div>
                  <div className="h-1.5 bg-[#0A0A0B] rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-[#C9B37E] to-[#77DDE8]"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <button className="w-full mt-4 btn-secondary py-2 text-sm">
            View Job Queue
            <ChevronRight className="w-4 h-4 inline ml-1" />
          </button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card-base p-6">
        <h2 className="text-lg font-semibold text-[#EDEFF3] mb-4">Quick Actions</h2>
        <div className="grid grid-cols-4 gap-3">
          <button className="card-elevated p-4 hover:bg-[#121416] transition-all hover:-translate-y-0.5 flex flex-col items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#77DDE8] to-[#36C790] flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-[#0A0A0B]" />
            </div>
            <span className="text-xs text-[#EDEFF3] text-center">New Research</span>
          </button>

          <button className="card-elevated p-4 hover:bg-[#121416] transition-all hover:-translate-y-0.5 flex flex-col items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#C9B37E] to-[#EFB65B] flex items-center justify-center">
              <Activity className="w-5 h-5 text-[#0A0A0B]" />
            </div>
            <span className="text-xs text-[#EDEFF3] text-center">Chat Session</span>
          </button>

          <button className="card-elevated p-4 hover:bg-[#121416] transition-all hover:-translate-y-0.5 flex flex-col items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#A787FF] to-[#77DDE8] flex items-center justify-center">
              <Target className="w-5 h-5 text-[#0A0A0B]" />
            </div>
            <span className="text-xs text-[#EDEFF3] text-center">Voice Mode</span>
          </button>

          <button className="card-elevated p-4 hover:bg-[#121416] transition-all hover:-translate-y-0.5 flex flex-col items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#36C790] to-[#77E8D1] flex items-center justify-center">
              <Zap className="w-5 h-5 text-[#0A0A0B]" />
            </div>
            <span className="text-xs text-[#EDEFF3] text-center">Quick Note</span>
          </button>
        </div>
      </div>
    </div>
  );
}
