import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, Download, Copy, Trash2, Settings, Zap } from 'lucide-react';
import { astraAPI, type ChatMessage as APIChatMessage } from '@/lib/api/client';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  agent?: string;
  tokens?: number;
}

interface Agent {
  id: string;
  name: string;
  sigil: string;
  description: string;
  status: 'online' | 'offline' | 'busy';
  color: string;
}

export function LumenChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Welcome to Lumen Chat. I am your multi-agent interface. How can I assist you today?',
      timestamp: new Date(),
      agent: 'Cognitive Core',
      tokens: 24
    }
  ]);
  
  const [inputValue, setInputValue] = useState('');
  const [selectedAgent, setSelectedAgent] = useState<string>('cognitive-core');
  const [isStreaming, setIsStreaming] = useState(false);
  const [totalTokens, setTotalTokens] = useState(24);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const agents: Agent[] = [
    {
      id: 'cognitive-core',
      name: 'Cognitive Core',
      sigil: '◈',
      description: 'General reasoning and planning',
      status: 'online',
      color: 'lucid-teal'
    },
    {
      id: 'memory-weaver',
      name: 'Memory Weaver',
      sigil: '⟡',
      description: 'Context and memory management',
      status: 'online',
      color: 'lucid-violet'
    },
    {
      id: 'research-specialist',
      name: 'Research Specialist',
      sigil: '✦',
      description: 'Deep research and analysis',
      status: 'busy',
      color: 'lucid-mint'
    },
    {
      id: 'code-architect',
      name: 'Code Architect',
      sigil: '⚡',
      description: 'Software engineering',
      status: 'online',
      color: 'limestone'
    }
  ];

  const currentAgent = agents.find(a => a.id === selectedAgent);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [inputValue]);

  const handleSend = async () => {
    if (!inputValue.trim() || isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsStreaming(true);

    try {
      // Call real ASTRA API
      const response = await astraAPI.sendChatMessage({
        messages: messages.concat(userMessage).map(m => ({
          role: m.role,
          content: m.content,
          agent: m.agent,
          tokens: m.tokens
        })),
        agent_id: selectedAgent,
        stream: false
      });

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message,
        timestamp: new Date(response.timestamp),
        agent: response.agent,
        tokens: response.tokens
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      setTotalTokens(prev => prev + userMessage.content.split(' ').length + response.tokens);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: Failed to connect to ASTRA backend. ${error}`,
        timestamp: new Date(),
        agent: 'System',
        tokens: 0
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const exportConversation = () => {
    const content = messages
      .map(m => `[${m.timestamp.toLocaleTimeString()}] ${m.role === 'user' ? 'You' : m.agent}: ${m.content}`)
      .join('\n\n');
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lumen-chat-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearConversation = () => {
    setMessages([]);
    setTotalTokens(0);
  };

  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'bg-status-success';
      case 'busy': return 'bg-status-warning';
      case 'offline': return 'bg-status-error';
      default: return 'bg-text-muted';
    }
  };

  return (
    <div className="h-full flex flex-col bg-obsidian-900">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-white/10 bg-obsidian-800/50 backdrop-blur-sm">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="text-4xl sigil animate-breathe">✧</div>
              <div>
                <h1 className="text-2xl font-semibold text-text-primary">Lumen Chat</h1>
                <p className="text-sm text-text-secondary">Multi-agent conversation interface</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Token Counter */}
              <div className="px-4 py-2 bg-obsidian-700/50 rounded-lg border border-white/10">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-lucid-mint" />
                  <span className="text-sm font-mono text-text-primary">{totalTokens.toLocaleString()}</span>
                  <span className="text-xs text-text-muted">tokens</span>
                </div>
              </div>

              {/* Actions */}
              <button
                onClick={exportConversation}
                className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                title="Export conversation"
              >
                <Download className="w-5 h-5 text-text-secondary" />
              </button>
              <button
                onClick={clearConversation}
                className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                title="Clear conversation"
              >
                <Trash2 className="w-5 h-5 text-text-secondary" />
              </button>
              <button className="p-2 hover:bg-white/5 rounded-lg transition-colors" title="Settings">
                <Settings className="w-5 h-5 text-text-secondary" />
              </button>
            </div>
          </div>

          {/* Agent Selector */}
          <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
            {agents.map(agent => (
              <button
                key={agent.id}
                onClick={() => setSelectedAgent(agent.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all whitespace-nowrap ${
                  selectedAgent === agent.id
                    ? `bg-${agent.color}/10 border-${agent.color} text-text-primary`
                    : 'bg-obsidian-700/30 border-white/10 text-text-secondary hover:bg-white/5'
                }`}
              >
                <span className="text-xl sigil">{agent.sigil}</span>
                <div className="text-left">
                  <div className="text-sm font-medium">{agent.name}</div>
                  <div className="text-xs text-text-muted">{agent.description}</div>
                </div>
                <div className={`w-2 h-2 rounded-full ${getStatusColor(agent.status)}`} />
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto scroll-smooth-obsidian px-6 py-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map(message => (
            <div
              key={message.id}
              className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.role === 'assistant' && (
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-lucid-teal to-lucid-violet flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
              )}

              <div className={`flex-1 max-w-2xl ${message.role === 'user' ? 'text-right' : ''}`}>
                {/* Message Header */}
                <div className="flex items-center gap-2 mb-1">
                  {message.role === 'assistant' && (
                    <>
                      <span className="text-sm font-medium text-text-primary">{message.agent}</span>
                      {message.tokens && (
                        <span className="text-xs text-text-muted font-mono">
                          {message.tokens} tokens
                        </span>
                      )}
                    </>
                  )}
                  {message.role === 'user' && (
                    <span className="text-sm font-medium text-text-primary">You</span>
                  )}
                  <span className="text-xs text-text-muted">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>

                {/* Message Content */}
                <div
                  className={`group relative px-4 py-3 rounded-lg ${
                    message.role === 'user'
                      ? 'bg-limestone/20 border border-limestone/30'
                      : 'bg-obsidian-700/50 border border-white/10'
                  }`}
                >
                  <p className="text-text-primary whitespace-pre-wrap leading-relaxed">
                    {message.content}
                  </p>

                  {/* Message Actions */}
                  <button
                    onClick={() => copyMessage(message.content)}
                    className="absolute top-2 right-2 p-1.5 bg-obsidian-900/80 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Copy message"
                  >
                    <Copy className="w-3.5 h-3.5 text-text-muted" />
                  </button>
                </div>
              </div>

              {message.role === 'user' && (
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-limestone to-lucid-mint flex items-center justify-center">
                  <User className="w-5 h-5 text-obsidian-900" />
                </div>
              )}
            </div>
          ))}

          {isStreaming && (
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-lucid-teal to-lucid-violet flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white animate-pulse" />
              </div>
              <div className="flex-1 max-w-2xl">
                <div className="px-4 py-3 rounded-lg bg-obsidian-700/50 border border-white/10">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-lucid-teal rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-lucid-teal rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-lucid-teal rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="flex-shrink-0 border-t border-white/10 bg-obsidian-800/50 backdrop-blur-sm">
        <div className="px-6 py-4">
          <div className="max-w-4xl mx-auto">
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={`Message ${currentAgent?.name}...`}
                className="w-full px-4 py-3 pr-12 bg-obsidian-700 border border-white/10 rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:border-lucid-teal/50 focus:ring-2 focus:ring-lucid-teal/20 resize-none transition-all"
                rows={1}
                disabled={isStreaming}
              />
              <button
                onClick={handleSend}
                disabled={!inputValue.trim() || isStreaming}
                className="absolute right-3 bottom-3 p-2 bg-gradient-to-br from-lucid-teal to-lucid-violet rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:scale-105 transition-transform"
                title="Send message (Enter)"
              >
                <Send className="w-4 h-4 text-white" />
              </button>
            </div>
            <div className="mt-2 text-xs text-text-muted text-center">
              Press <kbd className="px-1.5 py-0.5 bg-obsidian-700 border border-white/10 rounded">Enter</kbd> to send, 
              <kbd className="px-1.5 py-0.5 bg-obsidian-700 border border-white/10 rounded ml-1">Shift+Enter</kbd> for new line
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
