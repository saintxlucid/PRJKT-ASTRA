import { useState, useEffect, useRef } from 'react';
import { createCommands } from '../core/commands';

interface OracleProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
}

export default function Oracle({ isOpen, onClose, onNavigate }: OracleProps) {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = createCommands(onNavigate);
  const filtered = query
    ? commands.filter(cmd => 
        cmd.label.toLowerCase().includes(query.toLowerCase()) ||
        cmd.id.toLowerCase().includes(query.toLowerCase())
      )
    : commands;

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setQuery('');
      setSelected(0);
    }
  }, [isOpen]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!isOpen) return;
      
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelected(s => Math.min(filtered.length - 1, s + 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelected(s => Math.max(0, s - 1));
      } else if (e.key === 'Enter' && filtered[selected]) {
        e.preventDefault();
        filtered[selected].action();
        onClose();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, filtered, selected, onClose]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-32 z-50"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-astra-dark border border-white/20 rounded-lg shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="p-4 border-b border-white/10">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0); }}
            placeholder="Type a command or search..."
            className="w-full bg-transparent text-white text-lg outline-none placeholder:text-white/40"
          />
        </div>

        {/* Results */}
        <div className="max-h-96 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-white/40">No commands found</div>
          ) : (
            filtered.map((cmd, i) => (
              <button
                key={cmd.id}
                onClick={() => { cmd.action(); onClose(); }}
                className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors ${
                  i === selected ? 'bg-astra-accent text-white' : 'text-white/70 hover:bg-white/5'
                }`}
              >
                <span className="font-medium">{cmd.label}</span>
                {cmd.shortcut && (
                  <span className="text-xs text-white/40 font-mono">{cmd.shortcut}</span>
                )}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
