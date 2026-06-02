import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'
import { resolve } from 'path'

// __dirname is not available in ESM ("type":"module") — use fileURLToPath instead
const __dirname = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Allows: import { X } from '@/components/ui/...'
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
  },
})
