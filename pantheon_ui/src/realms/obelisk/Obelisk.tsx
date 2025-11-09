import { useState, useEffect } from 'react';
import { Save, Download, FileText, Tag, Link2, Search, BookOpen, ChevronRight, AlertCircle } from 'lucide-react';
import { astraAPI, type Note as APINote } from '@/lib/api/client';

interface Note {
  id: string;
  title: string;
  content: string;
  tags: string[];
  links?: string[];
  created: Date;
  modified: Date;
}

export function Obelisk() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [editContent, setEditContent] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load notes from backend on mount
  useEffect(() => {
    loadNotes();
  }, []);

  // Update edit content when selected note changes
  useEffect(() => {
    if (selectedNote) {
      setEditContent(selectedNote.content);
      setEditTitle(selectedNote.title);
    }
  }, [selectedNote]);

  const loadNotes = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const fetchedNotes = await astraAPI.getNotes();
      const convertedNotes: Note[] = fetchedNotes.map(note => ({
        ...note,
        created: new Date(note.created),
        modified: new Date(note.modified)
      }));
      setNotes(convertedNotes);
      if (convertedNotes.length > 0 && !selectedNote) {
        setSelectedNote(convertedNotes[0]);
      }
    } catch (err) {
      setError(`Failed to load notes: ${err}`);
      console.error('Failed to load notes:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const saveNote = async () => {
    if (!selectedNote || isSaving) return;

    try {
      setIsSaving(true);
      setError(null);
      
      const updatedNote: APINote = {
        id: selectedNote.id,
        title: editTitle,
        content: editContent,
        tags: selectedNote.tags,
        created: selectedNote.created.toISOString(),
        modified: new Date().toISOString()
      };

      await astraAPI.updateNote(selectedNote.id, updatedNote);
      
      // Update local state
      setNotes(prev => prev.map(note => 
        note.id === selectedNote.id 
          ? { ...note, title: editTitle, content: editContent, modified: new Date() }
          : note
      ));
      setSelectedNote(prev => prev ? { ...prev, title: editTitle, content: editContent, modified: new Date() } : null);
    } catch (err) {
      setError(`Failed to save note: ${err}`);
      console.error('Failed to save note:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const createNewNote = async () => {
    try {
      setError(null);
      const newNote: APINote = {
        id: `note-${Date.now()}`,
        title: 'Untitled Note',
        content: '# New Note\n\nStart writing...',
        tags: [],
        created: new Date().toISOString(),
        modified: new Date().toISOString()
      };

      const createdNote = await astraAPI.createNote(newNote);
      const convertedNote: Note = {
        ...createdNote,
        created: new Date(createdNote.created),
        modified: new Date(createdNote.modified)
      };
      
      setNotes(prev => [convertedNote, ...prev]);
      setSelectedNote(convertedNote);
    } catch (err) {
      setError(`Failed to create note: ${err}`);
      console.error('Failed to create note:', err);
    }
  };

  const deleteNote = async (noteId: string) => {
    try {
      setError(null);
      await astraAPI.deleteNote(noteId);
      
      setNotes(prev => {
        const filtered = prev.filter(n => n.id !== noteId);
        if (selectedNote?.id === noteId) {
          setSelectedNote(filtered.length > 0 ? filtered[0] : null);
        }
        return filtered;
      });
    } catch (err) {
      setError(`Failed to delete note: ${err}`);
      console.error('Failed to delete note:', err);
    }
  };

  const filteredNotes = notes.filter(note =>
    note.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    note.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const exportNote = () => {
    if (!selectedNote) return;
    
    const blob = new Blob([selectedNote.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedNote.title.replace(/\s+/g, '-').toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex bg-obsidian-900">
      {/* Sidebar - Notes List */}
      <div className="w-80 flex-shrink-0 border-r border-white/10 bg-obsidian-800/50 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center gap-3 mb-4">
            <div className="text-3xl sigil animate-breathe">⚔</div>
            <div className="flex-1">
              <h1 className="text-xl font-semibold text-text-primary">Obelisk</h1>
              <p className="text-xs text-text-secondary">Knowledge notebook</p>
            </div>
            <button
              onClick={createNewNote}
              className="p-2 bg-lucid-teal/20 hover:bg-lucid-teal/30 border border-lucid-teal/50 rounded-lg transition-all duration-200 group"
              title="New Note"
            >
              <FileText className="w-4 h-4 text-lucid-teal" />
            </button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search notes..."
              className="w-full pl-9 pr-3 py-2 bg-obsidian-700 border border-white/10 rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-lucid-teal/50 focus:ring-2 focus:ring-lucid-teal/20"
            />
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mx-2 mt-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}

        {/* Notes List */}
        <div className="flex-1 overflow-y-auto scroll-smooth-obsidian p-2">
          {isLoading ? (
            <div className="text-center py-8 text-text-muted">
              <div className="animate-spin w-6 h-6 border-2 border-lucid-teal border-t-transparent rounded-full mx-auto mb-2"></div>
              Loading notes...
            </div>
          ) : filteredNotes.length === 0 ? (
            <div className="text-center py-8 text-text-muted">
              {searchQuery ? 'No notes found' : 'No notes yet. Create your first one!'}
            </div>
          ) : (
            filteredNotes.map(note => (
              <button
              key={note.id}
              onClick={() => {
                setSelectedNote(note);
                setEditContent(note.content);
              }}
              className={`w-full text-left p-3 rounded-lg mb-2 transition-colors ${
                selectedNote?.id === note.id
                  ? 'bg-limestone/20 border border-limestone/30'
                  : 'hover:bg-white/5 border border-transparent'
              }`}
            >
              <div className="flex items-start gap-2 mb-2">
                <FileText className="w-4 h-4 text-text-secondary flex-shrink-0 mt-0.5" />
                <h3 className="text-sm font-medium text-text-primary line-clamp-2">{note.title}</h3>
              </div>
              
              {note.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {note.tags.map(tag => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 bg-lucid-teal/10 border border-lucid-teal/20 rounded text-xs text-lucid-teal"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              
              <p className="text-xs text-text-muted">
                Modified {note.modified.toLocaleDateString()}
              </p>
            </button>
          ))
          )}
        </div>
      </div>

      {/* Main Editor */}
      <div className="flex-1 flex flex-col">
        {selectedNote ? (
          <>
            {/* Note Header */}
            <div className="flex-shrink-0 border-b border-white/10 bg-obsidian-800/30 px-6 py-4">
              <div className="flex items-center justify-between mb-3">
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="text-2xl font-semibold text-text-primary bg-transparent border-none outline-none flex-1"
                  placeholder="Note title..."
                />
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      if (window.confirm(`Delete "${selectedNote.title}"?`)) {
                        deleteNote(selectedNote.id);
                      }
                    }}
                    className="p-2 hover:bg-red-500/10 rounded-lg transition-colors group"
                    title="Delete note"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-text-secondary group-hover:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                  <button
                    onClick={exportNote}
                    className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                    title="Export note"
                  >
                    <Download className="w-5 h-5 text-text-secondary" />
                  </button>
                  <button 
                    onClick={saveNote}
                    disabled={isSaving}
                    className="px-4 py-2 bg-lucid-teal/20 border border-lucid-teal/30 rounded-lg text-lucid-teal text-sm font-medium hover:bg-lucid-teal/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Save className="w-4 h-4 inline mr-2" />
                    {isSaving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>

              {/* Metadata */}
              <div className="flex items-center gap-4 text-sm text-text-muted">
                <span>Created {selectedNote.created.toLocaleDateString()}</span>
                <span>•</span>
                <span>Modified {selectedNote.modified.toLocaleDateString()}</span>
                {selectedNote.links && selectedNote.links.length > 0 && (
                  <>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Link2 className="w-3.5 h-3.5" />
                      {selectedNote.links.length} links
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Editor */}
            <div className="flex-1 overflow-y-auto scroll-smooth-obsidian">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-full px-6 py-4 bg-transparent text-text-primary placeholder-text-muted focus:outline-none resize-none font-mono text-sm leading-relaxed"
                placeholder="Start writing..."
              />
            </div>

            {/* Tags Bar */}
            <div className="flex-shrink-0 border-t border-white/10 bg-obsidian-800/30 px-6 py-3">
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4 text-text-secondary" />
                <div className="flex flex-wrap gap-2">
                  {selectedNote.tags.map(tag => (
                    <span
                      key={tag}
                      className="px-3 py-1 bg-lucid-teal/10 border border-lucid-teal/20 rounded-full text-sm text-lucid-teal"
                    >
                      {tag}
                    </span>
                  ))}
                  <button className="px-3 py-1 border border-dashed border-white/20 rounded-full text-sm text-text-muted hover:border-white/40 hover:text-text-secondary transition-colors">
                    + Add tag
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <BookOpen className="w-16 h-16 text-text-muted mx-auto mb-4" />
              <p className="text-text-secondary mb-4">
                {isLoading ? 'Loading notes...' : 'Select a note to view or create a new one'}
              </p>
              {!isLoading && notes.length === 0 && (
                <button
                  onClick={createNewNote}
                  className="px-6 py-3 bg-gradient-to-br from-lucid-teal to-lucid-violet rounded-lg text-white text-sm font-medium hover:scale-105 transition-transform"
                >
                  + Create First Note
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Right Sidebar - Graph View */}
      <div className="w-64 flex-shrink-0 border-l border-white/10 bg-obsidian-800/30 p-4">
        <h3 className="text-sm font-medium text-text-secondary mb-4 flex items-center gap-2">
          <Link2 className="w-4 h-4" />
          Connections
        </h3>
        
        {selectedNote && selectedNote.links && selectedNote.links.length > 0 ? (
          <div className="space-y-2">
            {selectedNote.links.map(linkId => {
              const linkedNote = notes.find(n => n.id === linkId);
              return linkedNote ? (
                <button
                  key={linkId}
                  onClick={() => {
                    setSelectedNote(linkedNote);
                  }}
                  className="w-full p-2 bg-obsidian-700/30 hover:bg-obsidian-700/50 rounded-lg border border-white/5 transition-colors text-left group"
                >
                  <div className="flex items-center gap-2">
                    <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-lucid-teal transition-colors" />
                    <span className="text-sm text-text-primary">{linkedNote.title}</span>
                  </div>
                </button>
              ) : null;
            })}
          </div>
        ) : (
          <p className="text-sm text-text-muted">No connections yet</p>
        )}

        <div className="mt-6">
          <button className="w-full px-3 py-2 bg-lucid-violet/10 border border-lucid-violet/20 rounded-lg text-sm text-lucid-violet hover:bg-lucid-violet/20 transition-colors">
            View Graph
          </button>
        </div>
      </div>
    </div>
  );
}
