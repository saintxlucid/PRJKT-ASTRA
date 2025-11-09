import { useEffect, useState } from "react";
import { motion } from "framer-motion";

declare global {
  interface Window {
    ASTRA?: {
      version: string;
      launchConsole: () => Promise<void>;
      openSettings: () => Promise<void>;
      getBackendStatus: () => Promise<{ running: boolean; url?: string }>;
    };
  }
}

export default function App() {
  const [version, setVersion] = useState("…");
  const [backendStatus, setBackendStatus] = useState<{ running: boolean; url?: string }>({ 
    running: false 
  });

  useEffect(() => {
    setVersion(window.ASTRA?.version ?? "1.0.0");
    
    // Check backend status
    const checkBackend = async () => {
      if (window.ASTRA?.getBackendStatus) {
        const status = await window.ASTRA.getBackendStatus();
        setBackendStatus(status);
      }
    };
    
    checkBackend();
    const interval = setInterval(checkBackend, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleLaunchConsole = async () => {
    if (window.ASTRA?.launchConsole) {
      await window.ASTRA.launchConsole();
    } else {
      alert("Console feature coming soon!");
    }
  };

  const handleOpenSettings = async () => {
    if (window.ASTRA?.openSettings) {
      await window.ASTRA.openSettings();
    } else {
      alert("Settings feature coming soon!");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-astra-bg via-black to-[#0a0a14] text-white overflow-auto">
      <div className="p-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-8"
        >
          <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-white via-blue-100 to-purple-200 bg-clip-text text-transparent">
            ASTRA OS
          </h1>
          <p className="mt-2 text-lg opacity-70">
            Your Local AI Assistant • Desktop Core v{version}
          </p>
        </motion.div>

        {/* Status Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-6 rounded-2xl border border-astra-border bg-astra-card backdrop-blur-2xl p-6"
        >
          <div className="flex items-center gap-3">
            <div className={`h-3 w-3 rounded-full ${backendStatus.running ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
            <div>
              <p className="font-medium">
                Backend Status: {backendStatus.running ? "Running" : "Offline"}
              </p>
              {backendStatus.url && (
                <p className="text-sm opacity-60 mt-1">
                  {backendStatus.url}
                </p>
              )}
            </div>
          </div>
        </motion.div>

        {/* Main Content */}
        <div className="mx-auto max-w-5xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="rounded-3xl border border-astra-border bg-astra-card backdrop-blur-2xl p-10 shadow-2xl"
          >
            {/* Quick Actions */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleLaunchConsole}
                className="group rounded-2xl border border-astra-border bg-astra-card px-6 py-8 hover:bg-astra-hover transition-all duration-200"
              >
                <div className="text-4xl mb-3">🚀</div>
                <h3 className="text-xl font-semibold mb-2">Launch Console</h3>
                <p className="text-sm opacity-70 group-hover:opacity-90 transition-opacity">
                  Open the chat interface
                </p>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleOpenSettings}
                className="group rounded-2xl border border-astra-border bg-astra-card px-6 py-8 hover:bg-astra-hover transition-all duration-200"
              >
                <div className="text-4xl mb-3">⚙️</div>
                <h3 className="text-xl font-semibold mb-2">Settings</h3>
                <p className="text-sm opacity-70 group-hover:opacity-90 transition-opacity">
                  Configure your preferences
                </p>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="group rounded-2xl border border-astra-border bg-astra-card px-6 py-8 hover:bg-astra-hover transition-all duration-200"
              >
                <div className="text-4xl mb-3">🧠</div>
                <h3 className="text-xl font-semibold mb-2">Memory</h3>
                <p className="text-sm opacity-70 group-hover:opacity-90 transition-opacity">
                  Manage knowledge base
                </p>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="group rounded-2xl border border-astra-border bg-astra-card px-6 py-8 hover:bg-astra-hover transition-all duration-200"
              >
                <div className="text-4xl mb-3">📊</div>
                <h3 className="text-xl font-semibold mb-2">Analytics</h3>
                <p className="text-sm opacity-70 group-hover:opacity-90 transition-opacity">
                  View usage statistics
                </p>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="group rounded-2xl border border-astra-border bg-astra-card px-6 py-8 hover:bg-astra-hover transition-all duration-200"
              >
                <div className="text-4xl mb-3">📁</div>
                <h3 className="text-xl font-semibold mb-2">Documents</h3>
                <p className="text-sm opacity-70 group-hover:opacity-90 transition-opacity">
                  Browse uploaded files
                </p>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="group rounded-2xl border border-astra-border bg-astra-card px-6 py-8 hover:bg-astra-hover transition-all duration-200"
              >
                <div className="text-4xl mb-3">🔌</div>
                <h3 className="text-xl font-semibold mb-2">Extensions</h3>
                <p className="text-sm opacity-70 group-hover:opacity-90 transition-opacity">
                  Manage integrations
                </p>
              </motion.button>
            </div>

            {/* Info Footer */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
              className="mt-8 pt-6 border-t border-astra-border"
            >
              <p className="text-sm opacity-60 leading-relaxed">
                <span className="font-medium opacity-80">💡 Tip:</span> This is your local ASTRA OS dashboard. 
                All processing happens on your machine with full privacy. 
                The console will open in a new window for seamless multitasking.
              </p>
            </motion.div>
          </motion.div>

          {/* System Info */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
            className="mt-6 rounded-2xl border border-astra-border bg-astra-card backdrop-blur-2xl p-6"
          >
            <h3 className="text-lg font-semibold mb-3">System Information</h3>
            <div className="grid gap-3 sm:grid-cols-2 text-sm">
              <div>
                <span className="opacity-60">Platform:</span>{" "}
                <span className="font-medium">Windows</span>
              </div>
              <div>
                <span className="opacity-60">Version:</span>{" "}
                <span className="font-medium">{version}</span>
              </div>
              <div>
                <span className="opacity-60">LLM Engine:</span>{" "}
                <span className="font-medium">llama.cpp (local)</span>
              </div>
              <div>
                <span className="opacity-60">Memory:</span>{" "}
                <span className="font-medium">ChromaDB + SQLite</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
