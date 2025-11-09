export const REALMS = [
  { id: "aeon", label: "ÆON Deck", sigil: "∞", path: "/aeon" },
  { id: "loom", label: "Aether Loom", sigil: "⌘", path: "/loom" },
  { id: "sigil", label: "Sigil Gate", sigil: "✠", path: "/sigil" },
  { id: "grove", label: "Dream Grove", sigil: "◈", path: "/grove" },
  { id: "weaver", label: "Weaver", sigil: "⚡", path: "/weaver" },
  { id: "agent", label: "Agent Panel", sigil: "🤖", path: "/agent" },
] as const;

export const INSTRUMENTS = [
  { id: "oracle", label: "Oracle", icon: "⌘", shortcut: "Ctrl+K" },
  { id: "pulse", label: "Pulse", icon: "◉", shortcut: "" },
] as const;

export const SYSTEM = [
  { id: "settings", label: "Settings", icon: "⚙", path: "/settings" },
  { id: "logs", label: "Logs", icon: "📋", path: "/logs" },
] as const;

export type RealmId = typeof REALMS[number]["id"];
export type InstrumentId = typeof INSTRUMENTS[number]["id"];
export type SystemId = typeof SYSTEM[number]["id"];
