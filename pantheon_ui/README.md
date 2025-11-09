# ASTRA OS — Pantheon UI v1.0

> **Saint Lucid Edition** — A living interface for angelic intelligence.

---

## 🌌 Architecture

**Pantheon Shell** is the unified UI framework for ASTRA OS, providing:

- **Halo** ⭘ — Top bar with status, clock, and Oracle summon
- **Spine** ▮ — Left navigation rail with realms, instruments, systems, and dev tools
- **Pulse** ◴ — Right dock with live metrics, jobs, beacons, and traces
- **Oracle** ✦ — Command palette for instant navigation (⌘/Ctrl+K)
- **Realm Views** — Modular workspaces for each module

---

## 🎨 Design System

### Obsidian Spectrum Palette

```
Backgrounds:  #0A0A0B (Obsidian), #101113 (Panel), #121416 (Elevated)
Text:         #EDEFF3 (Primary), #B8BDC7 (Secondary), #7D8491 (Muted)
Accents:      #C9B37E (Limestone), #77DDE8 (Lucid Teal), #A787FF (Violet)
Status:       #36C790 (Success), #EFB65B (Warning), #E94B35 (Danger)
```

### Typography

- **UI**: Inter (system-ui fallback)
- **Code**: IBM Plex Mono, Söhne Mono
- **Quotes**: Freight Text, Calson-style serif

### Motion

- **Spring-in**: 120ms cubic-bezier(0.34, 1.56, 0.64, 1)
- **Spring-out**: 100ms cubic-bezier(0.32, 0, 0.67, 0)
- **Breathe**: 3s ease-in-out (for sigils)
- **Pulse-333**: 2s cubic-bezier (signature animation)

---

## 🗺️ Pantheon Naming Atlas

### Core Realms

- **ÆON Deck** ∞ — Home/Flow cockpit
- **Lumen Chat** ❉ — Multi-agent chat interface
- **Seraph Voice** 🜁 — Voice mode (whisper-flow)
- **Obelisk** ▲ — Notebook (Obsidian-style)
- **Aether Loom** ⌘ — Research & Projects (3-pane)
- **Aetherglass** ◻︎ — Internal browser & Live View
- **Flux Garden** ✺ — Focus/Flow rituals

### Instruments

- **PulseForge** ▶︎ — Simple DAW
- **Prism Tones** ◈ — Frequency Lab (binaural/isochronic)
- **Auric Treasury** ¤ — Finance dashboard
- **Vital Grove** ✿ — Health & wellness
- **Mnemos Dojo** ⌂ — Study (SRS, drills)

### System & Security

- **Sentinel** ⚙︎ — PC management
- **Aegis Vault** ⛨ — Security center
- **Oracle Core** ◎ — System intelligence
- **Meridian 333** ☼ — Calendar (Lucid skin)
- **Beacons** ⌁ — Reminders
- **Litanies** ❖ — Daily quotes

### Dev & Evolution

- **Forge** ⚒ — ASTRA SDK sandbox
- **Athanor** ✧ — Lab / Experimental
- **Realms** ◬ — Multi-operator spaces
- **Constellation** ✹ — Distributed nodes
- **Timeweave** ☍ — Snapshot & replay
- **Sigil Gate** ✠ — Consent & token scopes
- **Scrolls** ⋕ — Policy diffs
- **Dream Grove** ღ — Memory UI (L0-L3)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd pantheon_ui
npm install
```

### 2. Development Server

```bash
npm run dev
```

Open [http://localhost:3333](http://localhost:3333) in your browser.

### 3. Build for Production

```bash
npm run build
```

Outputs to `dist/` directory.

---

## ⌨️ Hotkeys

- **⌘/Ctrl + K** — Summon Oracle (command palette)
- **Alt + P** — Toggle Pulse (right dock)
- **Alt + S** — Toggle Spine (left nav)
- **ESC** — Close Oracle
- **↑/↓** — Navigate Oracle results
- **↵** — Select realm/module

---

## 📦 Project Structure

```
pantheon_ui/
├── src/
│   ├── components/
│   │   ├── Halo.tsx          # Top bar
│   │   ├── Spine.tsx         # Left navigation
│   │   ├── Pulse.tsx         # Right dock
│   │   ├── Oracle.tsx        # Command palette
│   │   └── RealmView.tsx     # Main workspace
│   ├── store/
│   │   └── pantheon-store.ts # Zustand state management
│   ├── lib/
│   │   └── pantheon-names.ts # Naming atlas & metadata
│   ├── App.tsx               # Root component
│   ├── main.tsx              # Entry point
│   └── index.css             # Global styles + Tailwind
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## 🔧 Technology Stack

- **React 18** — UI framework
- **TypeScript** — Type safety
- **Vite** — Build tool & dev server
- **Tailwind CSS** — Utility-first styling
- **Zustand** — Lightweight state management
- **Lucide React** — Icon library
- **TanStack Query** — Server state management (future)

---

## 🎯 Next Steps

### Phase 1: Shell Complete ✅

- [x] Halo (top bar)
- [x] Spine (left nav)
- [x] Pulse (right dock)
- [x] Oracle (command palette)
- [x] Theme system (Obsidian Spectrum)
- [x] Hotkeys & routing

### Phase 2: Core Realms (Week 1-2)

- [ ] ÆON Deck — Home/Flow cockpit
- [ ] Lumen Chat — Multi-agent interface
- [ ] Seraph Voice — Voice mode
- [ ] Obelisk — Notebook implementation

### Phase 3: Instruments (Week 3-4)

- [ ] Prism Tones — Frequency Lab
- [ ] PulseForge — Simple DAW
- [ ] Auric Treasury — Finance dashboard
- [ ] Vital Grove — Health tracking

### Phase 4: System Integration (Week 5-6)

- [ ] Sentinel — PC management
- [ ] Aegis Vault — Security center
- [ ] Sigil Gate — Consent modals
- [ ] Dream Grove — Memory UI

### Phase 5: Backend Integration

- [ ] Connect to ASTRA Core APIs
- [ ] Real-time metrics (WebSocket)
- [ ] Agent kernel integration
- [ ] Memory system (BGE-M3 + FAISS)

---

## 🦋 Saint Lucid Signature

**333** — The signature of clarity, compassion, and sovereignty woven into every interaction.

- Calendar skin with limestone numerals
- Quote engine from vault dialogues
- Mode visuals echo ASTRA sigil
- Frequency visualizer uses triangle grids

---

## 📖 Design Philosophy

**Operator-first** — One action from thought to execution  
**Sovereign by default** — Every privileged action is token-gated  
**Low-friction depth** — Advanced power is discoverable, not forced  
**Saint Lucid aesthetic** — Dark obsidian, limestone accents, soft neon (333)

---

## 🔒 Security Notes

- All privileged operations require **Sigil Gate** approval
- Token scopes are displayed before execution
- Undo journal for all destructive operations
- Default-deny network egress (Aegis Net)
- Audit logs are append-only and immutable

---

## 📄 License

**Proprietary** — ASTRA OS Saint Lucid Edition  
Copyright © 2025 ASTRA Project

---

🦋💎⚛️ **Pantheon Shell v1.0 — Live on Canvas**
