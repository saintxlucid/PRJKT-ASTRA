import { useState } from 'react';
import { Search, FileText, Edit3, Download, ExternalLink, BookOpen, Layers } from 'lucide-react';

interface Source {
  id: string;
  title: string;
  url: string;
  type: 'web' | 'file' | 'note';
  excerpt: string;
  relevance: number;
}

interface ResearchProject {
  id: string;
  title: string;
  query: string;
  status: 'active' | 'completed';
  sources: Source[];
  notes: string;
  output: string;
}

export function AetherLoom() {
  const [project] = useState<ResearchProject>({
    id: '1',
    title: 'Quantum Computing Applications',
    query: 'practical applications of quantum computing in 2025',
    status: 'active',
    sources: [
      {
        id: '1',
        title: 'Quantum Computing: A Gentle Introduction',
        url: 'https://example.com/quantum-intro',
        type: 'web',
        excerpt: 'Quantum computing leverages quantum mechanical phenomena such as superposition and entanglement...',
        relevance: 95
      },
      {
        id: '2',
        title: 'Recent Advances in Quantum Algorithms',
        url: 'https://example.com/quantum-algorithms',
        type: 'web',
        excerpt: 'New quantum algorithms have shown promise in optimization problems, cryptography, and drug discovery...',
        relevance: 88
      },
      {
        id: '3',
        title: 'Personal Notes: Quantum Research',
        url: '',
        type: 'note',
        excerpt: 'Key areas to explore: quantum error correction, topological qubits, quantum machine learning...',
        relevance: 92
      }
    ],
    notes: '## Research Notes\n\n- Quantum computing shows promise in:\n  - Cryptography\n  - Drug discovery\n  - Optimization problems\n  - Machine learning\n\n- Key challenges:\n  - Error correction\n  - Scalability\n  - Decoherence',
    output: '# Quantum Computing Applications in 2025\n\n## Executive Summary\n\nQuantum computing has evolved from theoretical research to practical applications...\n\n## Key Applications\n\n### 1. Cryptography\nQuantum computers pose both threats and opportunities...\n\n### 2. Drug Discovery\nSimulating molecular interactions at quantum level...\n\n### 3. Optimization\nSolving complex optimization problems...'
  });

  const [activePane, setActivePane] = useState<'sources' | 'notes' | 'output'>('sources');
  const [notesContent, setNotesContent] = useState(project.notes);
  const [outputContent, setOutputContent] = useState(project.output);

  const exportOutput = () => {
    const blob = new Blob([outputContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${project.title.replace(/\s+/g, '-').toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col bg-obsidian-900">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-white/10 bg-obsidian-800/50 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-3xl sigil animate-breathe">∞</div>
            <div>
              <h1 className="text-xl font-semibold text-text-primary">{project.title}</h1>
              <p className="text-sm text-text-secondary">{project.query}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="px-3 py-1.5 bg-lucid-mint/10 border border-lucid-mint/20 rounded-full text-sm text-lucid-mint">
              {project.status === 'active' ? 'In Progress' : 'Completed'}
            </div>
            <button className="p-2 hover:bg-white/5 rounded-lg transition-colors">
              <Search className="w-5 h-5 text-text-secondary" />
            </button>
          </div>
        </div>
      </div>

      {/* 3-Pane Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Sources */}
        <div className="w-80 flex-shrink-0 border-r border-white/10 bg-obsidian-800/30 flex flex-col">
          <div className="p-4 border-b border-white/10">
            <h2 className="text-sm font-medium text-text-secondary flex items-center gap-2">
              <Layers className="w-4 h-4" />
              Sources ({project.sources.length})
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto scroll-smooth-obsidian p-3 space-y-2">
            {project.sources.map(source => (
              <div
                key={source.id}
                className="p-3 bg-obsidian-700/30 hover:bg-obsidian-700/50 border border-white/5 rounded-lg transition-colors cursor-pointer group"
              >
                <div className="flex items-start gap-2 mb-2">
                  {source.type === 'web' && <ExternalLink className="w-4 h-4 text-lucid-teal flex-shrink-0 mt-0.5" />}
                  {source.type === 'file' && <FileText className="w-4 h-4 text-lucid-violet flex-shrink-0 mt-0.5" />}
                  {source.type === 'note' && <BookOpen className="w-4 h-4 text-lucid-mint flex-shrink-0 mt-0.5" />}
                  <h3 className="text-sm font-medium text-text-primary line-clamp-2">{source.title}</h3>
                </div>

                <p className="text-xs text-text-secondary line-clamp-2 mb-2">
                  {source.excerpt}
                </p>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <div className="w-16 h-1.5 bg-obsidian-600 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-lucid-mint to-status-success"
                        style={{ width: `${source.relevance}%` }}
                      />
                    </div>
                    <span className="text-xs text-text-muted">{source.relevance}%</span>
                  </div>

                  {source.url && (
                    <button
                      onClick={() => window.open(source.url, '_blank')}
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <ExternalLink className="w-3.5 h-3.5 text-text-muted hover:text-lucid-teal" />
                    </button>
                  )}
                </div>
              </div>
            ))}

            <button className="w-full px-4 py-2 border border-dashed border-white/20 rounded-lg text-sm text-text-secondary hover:border-white/40 hover:text-text-primary transition-colors">
              + Add Source
            </button>
          </div>
        </div>

        {/* Center: Workspace (Notes/Output Toggle) */}
        <div className="flex-1 flex flex-col">
          {/* Tabs */}
          <div className="flex-shrink-0 border-b border-white/10 bg-obsidian-800/20">
            <div className="flex">
              <button
                onClick={() => setActivePane('notes')}
                className={`px-6 py-3 text-sm font-medium transition-colors ${
                  activePane === 'notes'
                    ? 'text-text-primary border-b-2 border-lucid-teal bg-obsidian-700/30'
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
                }`}
              >
                <Edit3 className="w-4 h-4 inline mr-2" />
                Research Notes
              </button>
              <button
                onClick={() => setActivePane('output')}
                className={`px-6 py-3 text-sm font-medium transition-colors ${
                  activePane === 'output'
                    ? 'text-text-primary border-b-2 border-lucid-teal bg-obsidian-700/30'
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
                }`}
              >
                <FileText className="w-4 h-4 inline mr-2" />
                Output Document
              </button>
            </div>
          </div>

          {/* Editor */}
          <div className="flex-1 overflow-y-auto scroll-smooth-obsidian">
            {activePane === 'notes' && (
              <textarea
                value={notesContent}
                onChange={(e) => setNotesContent(e.target.value)}
                className="w-full h-full px-6 py-4 bg-transparent text-text-primary placeholder-text-muted focus:outline-none resize-none font-mono text-sm leading-relaxed"
                placeholder="Take research notes here..."
              />
            )}

            {activePane === 'output' && (
              <textarea
                value={outputContent}
                onChange={(e) => setOutputContent(e.target.value)}
                className="w-full h-full px-6 py-4 bg-transparent text-text-primary placeholder-text-muted focus:outline-none resize-none font-mono text-sm leading-relaxed"
                placeholder="Write your final output here..."
              />
            )}
          </div>

          {/* Footer Actions */}
          <div className="flex-shrink-0 border-t border-white/10 bg-obsidian-800/20 px-6 py-3">
            <div className="flex items-center justify-between">
              <div className="text-xs text-text-muted">
                {activePane === 'notes' ? 'Markdown supported' : 'Ready to export'}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={exportOutput}
                  className="px-4 py-2 bg-lucid-teal/20 border border-lucid-teal/30 rounded-lg text-sm text-lucid-teal hover:bg-lucid-teal/30 transition-colors"
                >
                  <Download className="w-4 h-4 inline mr-2" />
                  Export
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Preview (Optional) */}
        <div className="w-96 flex-shrink-0 border-l border-white/10 bg-obsidian-800/20 overflow-y-auto scroll-smooth-obsidian p-6">
          <h2 className="text-sm font-medium text-text-secondary mb-4">Preview</h2>
          <div className="prose prose-invert prose-sm max-w-none">
            <div className="text-text-primary whitespace-pre-wrap leading-relaxed">
              {activePane === 'notes' ? notesContent : outputContent}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
