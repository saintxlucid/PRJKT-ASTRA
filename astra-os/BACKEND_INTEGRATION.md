# Integrating ASTRA Backend with Electron

This document explains how to connect the Electron app to your existing ASTRA backend.

## Current Setup

The Electron app (`electron/main.ts`) is configured to:

1. **Auto-start backend** on app launch (production mode)
2. **Check backend health** via `http://127.0.0.1:8080/health`
3. **Display status** in the UI (green/red dot)

## Backend Connection Flow

```
Electron App Launch
  ↓
Check if backend is running (HTTP GET /health)
  ↓
If NOT running → Start backend process
  ↓
Wait for health check to pass (max 30 seconds)
  ↓
Display main window
  ↓
UI shows backend status
```

## Adding Backend API Calls

### Method 1: Direct HTTP from React (Current)

Your React UI can call the backend directly:

```typescript
// In src/App.tsx or any component
const response = await fetch('http://127.0.0.1:8080/v1/conversations', {
  method: 'GET',
  headers: { 'Content-Type': 'application/json' }
});
const data = await response.json();
```

**Pros**: Simple, no IPC needed
**Cons**: CORS issues if backend doesn't allow `file://` origin

### Method 2: IPC Bridge (Recommended for Security)

Proxy backend calls through Electron's main process:

#### Step 1: Add IPC handler in `electron/main.ts`

```typescript
import http from "http";

// Add after other ipcMain.handle() calls
ipcMain.handle("backend-chat", async (event, message: string, conversationId?: string) => {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify({
      message,
      conversation_id: conversationId,
      use_memory: true,
      streaming: false,
    });

    const options = {
      hostname: "127.0.0.1",
      port: 8080,
      path: "/v1/chat",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(postData),
      },
    };

    const req = http.request(options, (res) => {
      let body = "";
      res.on("data", (chunk) => (body += chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(e);
        }
      });
    });

    req.on("error", reject);
    req.write(postData);
    req.end();
  });
});

// Add more handlers for other endpoints:
// - backend-memory-search
// - backend-conversations-list
// - backend-conversations-create
// etc.
```

#### Step 2: Expose in `electron/preload.ts`

```typescript
contextBridge.exposeInMainWorld("ASTRA", {
  version: "1.0.0",
  getBackendStatus: () => ipcRenderer.invoke("get-backend-status"),
  launchConsole: () => ipcRenderer.invoke("launch-console"),
  openSettings: () => ipcRenderer.invoke("open-settings"),
  
  // Backend API proxies
  chat: (message: string, conversationId?: string) => 
    ipcRenderer.invoke("backend-chat", message, conversationId),
  
  memory: {
    search: (query: string, limit?: number) =>
      ipcRenderer.invoke("backend-memory-search", query, limit),
  },
  
  conversations: {
    list: () => ipcRenderer.invoke("backend-conversations-list"),
    create: (title: string) => ipcRenderer.invoke("backend-conversations-create", title),
    get: (id: string) => ipcRenderer.invoke("backend-conversations-get", id),
  },
});
```

#### Step 3: Use in React

```typescript
// In src/App.tsx or any component
const sendMessage = async () => {
  if (!window.ASTRA?.chat) return;
  
  try {
    const response = await window.ASTRA.chat("Hello, ASTRA!");
    console.log("Response:", response);
  } catch (err) {
    console.error("Chat error:", err);
  }
};
```

## Reusing Existing Python API Client

You already have a Python API client in `desktop_app/api_client.py`. Instead of duplicating logic:

### Option A: Keep Python Desktop App (Existing)

Your existing PySide6 app (`desktop_app/`) works perfectly! You could:
- Use Electron for the **main launcher/dashboard**
- Use PySide6 for the **chat console window**

To launch it from Electron:

```typescript
// In electron/main.ts
import { spawn } from "child_process";

function launchPythonConsole() {
  const pythonPath = path.join(BACKEND_PATH, ".venv", "Scripts", "python.exe");
  const scriptPath = path.join(BACKEND_PATH, "desktop_app", "main.py");
  
  spawn(pythonPath, [scriptPath], {
    cwd: path.join(BACKEND_PATH, "desktop_app"),
    detached: true,
    windowsHide: false,
  });
}

// Call from IPC
ipcMain.handle("launch-console", async () => {
  launchPythonConsole();
});
```

### Option B: Build Full React Console

Create a new React component for chat:

```typescript
// src/Console.tsx
import { useState, useEffect } from "react";

export default function Console() {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");

  const sendMessage = async () => {
    if (!window.ASTRA?.chat) return;
    
    const response = await window.ASTRA.chat(input);
    setMessages([...messages, { user: input, assistant: response.response }]);
    setInput("");
  };

  return (
    <div className="flex flex-col h-screen bg-astra-bg">
      <div className="flex-1 overflow-auto p-4">
        {messages.map((msg, i) => (
          <div key={i} className="mb-4">
            <div className="text-blue-400">You: {msg.user}</div>
            <div className="text-white">ASTRA: {msg.assistant}</div>
          </div>
        ))}
      </div>
      <div className="p-4 border-t border-astra-border">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && sendMessage()}
          className="w-full px-4 py-2 bg-astra-card rounded-lg"
        />
      </div>
    </div>
  );
}
```

Then route to it in `electron/main.ts` when creating console window:

```typescript
consoleWindow.loadURL("http://localhost:5173/?mode=console");
```

And in `src/App.tsx`:

```typescript
const params = new URLSearchParams(window.location.search);
if (params.get("mode") === "console") {
  return <Console />;
}
```

## Streaming Support

For streaming chat responses, use Server-Sent Events (SSE):

```typescript
// In React component
const streamChat = async (message: string) => {
  const response = await fetch("http://127.0.0.1:8080/v1/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, streaming: true }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader!.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split("\n");

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = JSON.parse(line.slice(6));
        if (data.delta) {
          // Update UI with streaming text
          appendToLastMessage(data.delta);
        }
      }
    }
  }
};
```

## CORS Configuration

If you get CORS errors, ensure your backend (`backend/app.py`) allows the Electron origin:

```python
# backend/app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev
        "null",  # Electron file://
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Next Steps

1. **Test basic connection**: Run `npm run dev` and check if backend status shows green
2. **Add one API call**: Try `window.ASTRA.chat()` from React DevTools console
3. **Build full UI**: Either reuse Python console or build React chat interface
4. **Test streaming**: Implement SSE for real-time responses
5. **Polish**: Add error handling, loading states, reconnection logic

---

**Your backend is already rock-solid. Now you just need to wire it to the shiny new Electron UI! 🚀**
