import { useState } from 'react';
import { Globe, ArrowLeft, ArrowRight, RotateCw, Home, Star, BookmarkPlus, Share2, Search } from 'lucide-react';

interface Tab {
  id: string;
  title: string;
  url: string;
  favicon?: string;
}

interface Bookmark {
  id: string;
  title: string;
  url: string;
  folder: string;
}

export function Aetherglass() {
  const [tabs, setTabs] = useState<Tab[]>([
    {
      id: '1',
      title: 'ASTRA Documentation',
      url: 'https://astra-docs.local/',
      favicon: '📚'
    }
  ]);

  const [activeTabId, setActiveTabId] = useState('1');
  const [urlInput, setUrlInput] = useState('https://astra-docs.local/');
  const [bookmarks] = useState<Bookmark[]>([
    { id: '1', title: 'ASTRA Docs', url: 'https://astra-docs.local/', folder: 'Work' },
    { id: '2', title: 'GitHub', url: 'https://github.com/', folder: 'Development' },
    { id: '3', title: 'Research Portal', url: 'https://research.local/', folder: 'Research' }
  ]);

  const activeTab = tabs.find(t => t.id === activeTabId);

  const handleNavigate = (url: string) => {
    if (activeTab) {
      setTabs(tabs.map(t => 
        t.id === activeTabId ? { ...t, url, title: new URL(url).hostname } : t
      ));
      setUrlInput(url);
    }
  };

  const handleNewTab = () => {
    const newTab: Tab = {
      id: Date.now().toString(),
      title: 'New Tab',
      url: 'https://astra.local/start',
      favicon: '🌐'
    };
    setTabs([...tabs, newTab]);
    setActiveTabId(newTab.id);
    setUrlInput(newTab.url);
  };

  const handleCloseTab = (tabId: string) => {
    const newTabs = tabs.filter(t => t.id !== tabId);
    if (newTabs.length === 0) {
      handleNewTab();
    } else if (activeTabId === tabId) {
      setActiveTabId(newTabs[0].id);
      setUrlInput(newTabs[0].url);
    }
    setTabs(newTabs);
  };

  return (
    <div className="h-full flex flex-col bg-obsidian-900">
      {/* Browser Chrome */}
      <div className="flex-shrink-0 bg-obsidian-800/50 border-b border-white/10">
        {/* Tabs Bar */}
        <div className="flex items-center gap-1 px-2 pt-2">
          {tabs.map(tab => (
            <div
              key={tab.id}
              onClick={() => {
                setActiveTabId(tab.id);
                setUrlInput(tab.url);
              }}
              className={`group flex items-center gap-2 px-4 py-2 rounded-t-lg cursor-pointer transition-colors max-w-xs ${
                activeTabId === tab.id
                  ? 'bg-obsidian-900 border-t border-l border-r border-white/10'
                  : 'bg-obsidian-700/30 hover:bg-obsidian-700/50'
              }`}
            >
              <span className="text-sm">{tab.favicon || '🌐'}</span>
              <span className="text-sm text-text-primary truncate flex-1">{tab.title}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleCloseTab(tab.id);
                }}
                className="opacity-0 group-hover:opacity-100 hover:bg-white/10 rounded p-0.5 transition-all"
                title="Close tab"
              >
                <span className="text-xs text-text-muted">×</span>
              </button>
            </div>
          ))}
          
          <button
            onClick={handleNewTab}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
            title="New tab"
          >
            <span className="text-text-secondary">+</span>
          </button>
        </div>

        {/* Navigation Bar */}
        <div className="px-4 py-3 flex items-center gap-2">
          {/* Navigation Controls */}
          <div className="flex items-center gap-1">
            <button
              className="p-2 hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30"
              title="Back"
              disabled
            >
              <ArrowLeft className="w-4 h-4 text-text-secondary" />
            </button>
            <button
              className="p-2 hover:bg-white/5 rounded-lg transition-colors disabled:opacity-30"
              title="Forward"
              disabled
            >
              <ArrowRight className="w-4 h-4 text-text-secondary" />
            </button>
            <button
              className="p-2 hover:bg-white/5 rounded-lg transition-colors"
              title="Refresh"
            >
              <RotateCw className="w-4 h-4 text-text-secondary" />
            </button>
            <button
              className="p-2 hover:bg-white/5 rounded-lg transition-colors"
              title="Home"
              onClick={() => handleNavigate('https://astra.local/start')}
            >
              <Home className="w-4 h-4 text-text-secondary" />
            </button>
          </div>

          {/* URL Bar */}
          <div className="flex-1 relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
              <Globe className="w-4 h-4 text-lucid-teal" />
            </div>
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleNavigate(urlInput);
                }
              }}
              className="w-full pl-10 pr-10 py-2.5 bg-obsidian-700 border border-white/10 rounded-lg text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-lucid-teal/50 focus:ring-2 focus:ring-lucid-teal/20"
              placeholder="Search or enter address"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <Star className="w-4 h-4 text-text-muted hover:text-amber-400 cursor-pointer transition-colors" title="Bookmark" />
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1">
            <button className="p-2 hover:bg-white/5 rounded-lg transition-colors" title="Share">
              <Share2 className="w-4 h-4 text-text-secondary" />
            </button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Bookmarks */}
        <div className="w-64 flex-shrink-0 border-r border-white/10 bg-obsidian-800/30 overflow-y-auto scroll-smooth-obsidian">
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-text-secondary flex items-center gap-2">
                <BookmarkPlus className="w-4 h-4" />
                Bookmarks
              </h2>
            </div>

            <div className="space-y-1">
              {bookmarks.map(bookmark => (
                <button
                  key={bookmark.id}
                  onClick={() => handleNavigate(bookmark.url)}
                  className="w-full text-left p-2 hover:bg-white/5 rounded-lg transition-colors group"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Globe className="w-3.5 h-3.5 text-lucid-teal flex-shrink-0" />
                    <span className="text-sm text-text-primary truncate">{bookmark.title}</span>
                  </div>
                  <p className="text-xs text-text-muted truncate pl-5">{bookmark.url}</p>
                </button>
              ))}
            </div>

            <button className="w-full mt-4 px-3 py-2 border border-dashed border-white/20 rounded-lg text-sm text-text-secondary hover:border-white/40 hover:text-text-primary transition-colors">
              + Add Bookmark
            </button>
          </div>
        </div>

        {/* Browser View */}
        <div className="flex-1 bg-obsidian-900 flex items-center justify-center">
          <div className="text-center max-w-2xl px-8">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-lucid-teal to-lucid-violet flex items-center justify-center">
              <Globe className="w-10 h-10 text-white" />
            </div>
            
            <h2 className="text-2xl font-semibold text-text-primary mb-3">
              Aetherglass Browser
            </h2>
            
            <p className="text-text-secondary mb-6">
              Internal browser for ASTRA OS. Navigate to web resources, documentation, and integrated tools.
            </p>

            <div className="card-obsidian p-6 text-left">
              <h3 className="text-sm font-medium text-text-primary mb-3 flex items-center gap-2">
                <Search className="w-4 h-4 text-lucid-teal" />
                Quick Access
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Documentation', url: 'https://astra-docs.local/' },
                  { label: 'API Reference', url: 'https://api-docs.local/' },
                  { label: 'Community', url: 'https://community.local/' },
                  { label: 'Research Hub', url: 'https://research.local/' }
                ].map(item => (
                  <button
                    key={item.url}
                    onClick={() => handleNavigate(item.url)}
                    className="px-4 py-2 bg-obsidian-700/50 hover:bg-obsidian-700 border border-white/5 rounded-lg text-sm text-text-primary transition-colors"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <p className="text-xs text-text-muted mt-6">
              In production, this would render actual web content using a Chromium-based view
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
