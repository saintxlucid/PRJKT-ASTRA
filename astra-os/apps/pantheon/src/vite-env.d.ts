/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MEMORY_API: string
  readonly VITE_SIGIL_API: string
  readonly VITE_SUPERVISOR_API: string
  readonly VITE_DEV_MODE: string
  readonly VITE_LOG_LEVEL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
