export interface Command {
  id: string;
  label: string;
  shortcut?: string;
  action: () => void | Promise<void>;
}

export const createCommands = (navigate: (path: string) => void): Command[] => [
  { id: "open:aeon", label: "Open ÆON Deck", shortcut: "Alt+1", action: () => navigate("/aeon") },
  { id: "open:loom", label: "Open Aether Loom", shortcut: "Alt+2", action: () => navigate("/loom") },
  { id: "open:sigil", label: "Open Sigil Gate", shortcut: "Alt+3", action: () => navigate("/sigil") },
  { id: "open:grove", label: "Open Dream Grove", shortcut: "Alt+4", action: () => navigate("/grove") },
  { id: "open:weaver", label: "Open Weaver", shortcut: "Alt+5", action: () => navigate("/weaver") },
  { id: "approve:plan", label: "Approve Current Plan (✠)", shortcut: "Ctrl+Shift+A", action: async () => {
    console.log("Approve plan triggered");
  }},
  { id: "rollback:last", label: "Rollback Last Action", shortcut: "Ctrl+Shift+Z", action: async () => {
    console.log("Rollback triggered");
  }},
  { id: "toggle:oracle", label: "Toggle Oracle", shortcut: "Ctrl+K", action: () => {
    console.log("Oracle toggled");
  }},
];
