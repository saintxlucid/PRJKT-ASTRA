import { contextBridge, ipcRenderer } from "electron";

// Expose a minimal, safe API surface to the renderer
contextBridge.exposeInMainWorld("ASTRA", {
  version: "1.0.0",
  
  // Backend status
  getBackendStatus: () => ipcRenderer.invoke("get-backend-status"),
  
  // Window management
  launchConsole: () => ipcRenderer.invoke("launch-console"),
  openSettings: () => ipcRenderer.invoke("open-settings"),
  
  // Future: Backend API proxies
  // chat: (message: string) => ipcRenderer.invoke("backend-chat", message),
  // memory: {
  //   search: (query: string) => ipcRenderer.invoke("backend-memory-search", query),
  // },
  // conversations: {
  //   list: () => ipcRenderer.invoke("backend-conversations-list"),
  //   create: (title: string) => ipcRenderer.invoke("backend-conversations-create", title),
  // },
});
