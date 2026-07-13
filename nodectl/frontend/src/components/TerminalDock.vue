<template>
  <aside class="flex-none w-1/3 border-l border-[#9d00ff] bg-black flex flex-col hidden lg:flex h-full">
    <div class="px-4 py-2 border-b border-[#9d00ff] text-xs font-mono text-gray-400 uppercase flex justify-between items-center">
      <span>Terminal · {{ selectedTarget || 'Watcher' }}</span>
      <span :class="connectionStatus === 'connected' ? 'text-green-400' : 'text-gray-500'">{{ connectionStatus }}</span>
    </div>
    <div class="flex-1 p-2 font-mono text-sm relative" ref="terminalContainer">
      <!-- Terminal mount point -->
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTerminalSession } from '../features/terminal/useTerminalSession'

const terminalContainer = ref<HTMLElement | null>(null)
const { initTerminal, connect, selectedTarget, connectionStatus } = useTerminalSession()

onMounted(() => {
  if (terminalContainer.value) {
    initTerminal(terminalContainer.value)
    // Connect to host by default
    connect('host')
  }
})
</script>

<style scoped>
:deep(.xterm-viewport::-webkit-scrollbar) {
  width: 6px;
  height: 6px;
}
:deep(.xterm-viewport::-webkit-scrollbar-track) {
  background: transparent;
}
:deep(.xterm-viewport::-webkit-scrollbar-thumb) {
  background: #4a0072;
  border-radius: 3px;
}
:deep(.xterm-viewport::-webkit-scrollbar-thumb:hover) {
  background: #9d00ff;
}
</style>
