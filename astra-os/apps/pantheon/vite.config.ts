import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import type { ManualChunkMeta } from 'rollup';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: false,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    
    // Performance budgets
    chunkSizeWarningLimit: 500, // Warn if chunk > 500KB
    
    rollupOptions: {
      output: {
        // Manual chunking strategy for optimal code-splitting
        manualChunks: (id: string, meta: ManualChunkMeta) => {
          // Vendor chunks
          if (id.includes('node_modules')) {
            // React ecosystem
            if (id.includes('react') || id.includes('react-dom') || id.includes('scheduler')) {
              return 'vendor-react';
            }
            // TanStack ecosystem
            if (id.includes('@tanstack')) {
              return 'vendor-tanstack';
            }
            // Radix UI (when installed)
            if (id.includes('@radix-ui')) {
              return 'vendor-radix';
            }
            // Framer Motion
            if (id.includes('framer-motion')) {
              return 'vendor-framer';
            }
            // Other vendors
            return 'vendor';
          }
          
          // Realm chunks (lazy-loaded)
          if (id.includes('/src/realms/AEON')) {
            return 'realm-aeon';
          }
          if (id.includes('/src/realms/AetherLoom')) {
            return 'realm-loom';
          }
          if (id.includes('/src/realms/SigilGate')) {
            return 'realm-sigil';
          }
          if (id.includes('/src/realms/DreamGrove')) {
            return 'realm-grove';
          }
          if (id.includes('/src/realms/Weaver')) {
            return 'realm-weaver';
          }
          
          // Views (Settings, Logs)
          if (id.includes('/src/views/')) {
            return 'views';
          }
          
          // Components
          if (id.includes('/src/components/')) {
            return 'components';
          }
        },
        
        // Naming pattern for chunks
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
    
    // Minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
      },
    },
  },
  
  // Optimization
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      '@tanstack/react-router',
      '@tanstack/react-query',
      'zustand',
      'framer-motion',
    ],
  },
});
