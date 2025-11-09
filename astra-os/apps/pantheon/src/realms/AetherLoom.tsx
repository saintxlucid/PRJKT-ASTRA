import { useState } from 'react';

interface Cite {
  id: string;
  doc: string;
  page: number;
  text: string;
  timestamp: number;
}

interface Claim {
  id: string;
  text: string;
  cites: string[]; // cite IDs
}

export default function AetherLoom() {
  const [sources, setSources] = useState<string[]>(['research_paper.pdf', 'article_2024.pdf']);
  const [cites, setCites] = useState<Cite[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [selectedText, setSelectedText] = useState('');

  function addSource() {
    const name = prompt('Enter source name (PDF/URL):');
    if (name) setSources([...sources, name]);
  }

  function captureCite() {
    const text = selectedText || 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.';
    const cite: Cite = {
      id: `cite-${Date.now()}`,
      doc: sources[0] || 'unknown.pdf',
      page: Math.floor(Math.random() * 50) + 1,
      text,
      timestamp: Date.now(),
    };
    setCites([cite, ...cites]);
    console.log('✓ Cite captured:', cite);
  }

  function addClaim() {
    const text = prompt('Enter claim statement:');
    if (text) {
      const claim: Claim = {
        id: `claim-${Date.now()}`,
        text,
        cites: [],
      };
      setClaims([...claims, claim]);
    }
  }

  function linkCite(claimId: string, citeId: string) {
    setClaims(claims.map(c => 
      c.id === claimId ? { ...c, cites: [...c.cites, citeId] } : c
    ));
  }

  const coveragePercent = claims.length > 0 
    ? Math.round((claims.filter(c => c.cites.length > 0).length / claims.length) * 100)
    : 0;

  return (
    <div className="grid grid-cols-12 gap-4 p-4 h-[calc(100vh-3.5rem)]">
      {/* Left: Sources Panel */}
      <aside className="col-span-2 bg-white/5 rounded-lg p-4 border border-white/10 flex flex-col">
        <h2 className="text-xs font-semibold text-white/50 uppercase tracking-wide mb-3">Sources</h2>
        <div className="space-y-2 flex-1 overflow-auto">
          {sources.map((src, i) => (
            <div
              key={i}
              className="p-2 rounded bg-white/5 hover:bg-white/10 transition-colors cursor-pointer text-sm text-white/70 truncate"
              title={src}
            >
              📄 {src}
            </div>
          ))}
        </div>
        <button
          onClick={addSource}
          className="mt-3 px-3 py-2 rounded bg-astra-accent hover:bg-astra-accent/80 text-sm font-medium transition-colors"
        >
          + Add Source
        </button>
      </aside>

      {/* Center: Reader */}
      <section className="col-span-6 bg-white/5 rounded-lg p-4 border border-white/10 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white/70">Reader</h2>
          <div className="text-xs text-white/50">Page 1 of 50</div>
        </div>

        {/* Simulated PDF Content */}
        <div className="flex-1 bg-astra-dark rounded p-6 overflow-auto border border-white/10">
          <div className="prose prose-invert max-w-none">
            <h1 className="text-xl font-bold mb-4">Sample Research Document</h1>
            <p className="mb-4 text-white/70 leading-relaxed">
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor 
              incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud 
              exercitation ullamco laboris.
            </p>
            <p className="mb-4 text-white/70 leading-relaxed">
              Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu 
              fugiat nulla pariatur. <mark className="bg-yellow-500/30 text-white">Excepteur sint 
              occaecat cupidatat non proident</mark>, sunt in culpa qui officia deserunt mollit 
              anim id est laborum.
            </p>
            <p className="text-white/70 leading-relaxed">
              Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque 
              laudantium, totam rem aperiam.
            </p>
          </div>
        </div>

        {/* Capture Controls */}
        <div className="mt-4 flex items-center gap-3">
          <input
            type="text"
            value={selectedText}
            onChange={e => setSelectedText(e.target.value)}
            placeholder="Select text or type quote..."
            className="flex-1 px-3 py-2 rounded bg-white/5 border border-white/10 outline-none focus:border-astra-accent transition-colors text-sm"
          />
          <button
            onClick={captureCite}
            className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-700 font-medium text-sm transition-colors"
          >
            Capture Cite
          </button>
        </div>
      </section>

      {/* Right: Claims & Cites Workspace */}
      <aside className="col-span-4 bg-white/5 rounded-lg p-4 border border-white/10 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white/70">Claims & Cites</h2>
          <div className="text-xs px-2 py-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            Coverage: {coveragePercent}%
          </div>
        </div>

        {/* Claims Section */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wide">Claims</h3>
            <button
              onClick={addClaim}
              className="text-xs px-2 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors"
            >
              + Claim
            </button>
          </div>
          <div className="space-y-2 max-h-48 overflow-auto">
            {claims.length === 0 ? (
              <div className="text-xs text-white/40 italic">No claims yet</div>
            ) : (
              claims.map(claim => (
                <div key={claim.id} className="p-2 rounded bg-white/5 border border-white/10 text-xs">
                  <div className="text-white/80 mb-1">{claim.text}</div>
                  <div className="text-white/40">
                    {claim.cites.length} cite{claim.cites.length !== 1 ? 's' : ''}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Cites Section */}
        <div className="flex-1 flex flex-col">
          <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wide mb-2">Captured Cites</h3>
          <div className="space-y-2 flex-1 overflow-auto">
            {cites.length === 0 ? (
              <div className="text-xs text-white/40 italic">No cites captured yet</div>
            ) : (
              cites.map(cite => (
                <div
                  key={cite.id}
                  className="p-3 rounded bg-astra-dark border border-white/10 text-xs hover:border-astra-accent/50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-1">
                    <span className="font-semibold text-white/90">{cite.doc}</span>
                    <span className="text-white/50">p.{cite.page}</span>
                  </div>
                  <p className="text-white/70 leading-relaxed mb-2">{cite.text}</p>
                  <div className="text-white/40 text-[10px]">
                    {new Date(cite.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
