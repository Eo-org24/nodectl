<template>
  <div class="flex flex-col h-screen overflow-hidden bg-[#0a001a] text-gray-200">
    <!-- System bar -->
    <header class="flex-none flex items-center justify-between px-4 py-1.5 border-b border-[#9d00ff] bg-[#1a002a] text-xs font-mono">
      <div class="flex items-center gap-4">
        <span class="text-[#ff00ff] font-bold tracking-widest uppercase text-glow">NodePanel</span>
        <div class="flex items-center gap-2">
          <span class="text-green-400">●</span>
          <span class="text-gray-400">API</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-green-400">●</span>
          <span class="text-gray-400">HYPERVISOR</span>
        </div>
      </div>
      <div class="flex items-center gap-4">
        <span class="text-gray-400">TARGET: {{ targetName || 'none' }}</span>
        <span class="text-gray-400">JOBS: 0</span>
        <button class="text-[#ff00ff] hover:text-white uppercase tracking-wider">Terminal ▣</button>
      </div>
    </header>

    <!-- Main Workspace -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Navigation -->
      <nav class="flex-none w-48 border-r border-[#9d00ff] bg-[#000d11] py-4 flex flex-col gap-1">
        <router-link to="/overview" class="nav-link">Overview</router-link>
        <div class="nav-link text-gray-500 cursor-not-allowed">Nodes</div>
        <div class="nav-link text-gray-500 cursor-not-allowed">Workflows</div>
        <div class="nav-link text-gray-500 cursor-not-allowed">Repositories</div>
        <div class="nav-link text-gray-500 cursor-not-allowed">Audit</div>
        <div class="nav-link text-gray-500 cursor-not-allowed">Settings</div>
      </nav>

      <!-- Content -->
      <main class="flex-1 relative overflow-auto custom-scrollbar p-6">
        <slot />
      </main>

      <TerminalDock />
    </div>

    <!-- Activity Center -->
    <footer class="flex-none px-4 py-2 border-t border-[#9d00ff] bg-[#1a002a] text-xs font-mono flex items-center justify-between">
      <div class="flex items-center gap-2 text-gray-400">
        Activity: none
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import TerminalDock from '../components/TerminalDock.vue'
import { useTerminalSession } from '../features/terminal/useTerminalSession'

const { selectedTarget: targetName } = useTerminalSession()
</script>

<style scoped>
@reference "../styles/base.css";
.nav-link {
  @apply px-4 py-2 text-sm text-gray-400 hover:bg-[#4a0072]/30 hover:text-[#ff00ff] transition-colors uppercase tracking-wider font-bold;
}
.router-link-active {
  @apply text-[#ff00ff] border-l-2 border-[#ff00ff] bg-[rgba(255,0,255,0.05)];
}
</style>
