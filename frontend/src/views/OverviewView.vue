<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold font-sans text-white uppercase tracking-wider mb-8">System Overview</h1>

    <!-- Summary Strip -->
    <div class="grid grid-cols-5 gap-4">
      <div class="metric-card">
        <div class="metric-label">MANIFESTS</div>
        <div class="metric-value text-[#ff00ff]">{{ stats.manifests }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">HYPERVISOR VMS</div>
        <div class="metric-value">{{ stats.vms }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">RUNNING</div>
        <div class="metric-value text-green-400">{{ stats.running }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">DRIFT</div>
        <div class="metric-value text-amber-400">{{ stats.drift }}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">ACTIVE JOBS</div>
        <div class="metric-value">{{ stats.jobs }}</div>
      </div>
    </div>

    <!-- Reconciled Node Table -->
    <div class="border border-[#9d00ff] rounded-sm bg-[#1a002a] overflow-hidden mt-8">
      <table class="w-full text-left text-sm">
        <thead class="bg-[#000d11] text-xs uppercase text-gray-400 font-mono border-b border-[#9d00ff]">
          <tr>
            <th class="px-4 py-3 font-bold tracking-wider">Node</th>
            <th class="px-4 py-3 font-bold tracking-wider">Manifest</th>
            <th class="px-4 py-3 font-bold tracking-wider">Hypervisor</th>
            <th class="px-4 py-3 font-bold tracking-wider">Drift</th>
            <th class="px-4 py-3 font-bold tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[#9d00ff]/50 font-sans">
          <tr v-for="node in nodes" :key="node.name" class="hover:bg-[#4a0072]/20 transition-colors">
            <td class="px-4 py-3 font-mono text-[#ff00ff]">{{ node.name }}</td>
            <td class="px-4 py-3">
              <span class="px-2 py-0.5 rounded text-xs" :class="node.manifest.exists ? 'bg-green-900/30 text-green-400' : 'bg-gray-800 text-gray-400'">
                {{ node.manifest.exists ? node.manifest.state || 'Ready' : 'Missing' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span class="px-2 py-0.5 rounded text-xs" :class="node.hypervisor.state === 'running' ? 'bg-green-900/30 text-green-400' : (node.hypervisor.exists ? 'bg-gray-800 text-gray-400' : 'bg-gray-800 text-gray-500')">
                {{ node.hypervisor.exists ? node.hypervisor.state : 'Missing' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span class="text-xs" :class="node.drift === 'aligned' ? 'text-gray-500' : 'text-amber-400 font-bold'">
                {{ node.drift }}
              </span>
            </td>
            <td class="px-4 py-3">
              <button class="text-xs px-3 py-1 border border-[#9d00ff] text-[#ff00ff] hover:bg-[#ff00ff] hover:text-black uppercase font-bold tracking-wider transition-colors mr-2">
                Target
              </button>
              <button class="text-xs px-3 py-1 border border-[#9d00ff] text-gray-300 hover:border-gray-300 uppercase font-bold tracking-wider transition-colors">
                Inspect
              </button>
            </td>
          </tr>
          <tr v-if="nodes.length === 0">
            <td colspan="5" class="px-4 py-8 text-center text-gray-500 italic">No nodes found</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const stats = ref({
  manifests: 0,
  vms: 0,
  running: 0,
  drift: 0,
  jobs: 0
})

const nodes = ref<any[]>([])

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/system/status')
    if (res.ok) {
      const data = await res.json()
      stats.value = data.stats
      nodes.value = data.nodes
    }
  } catch (e) {
    console.error('Failed to fetch system status', e)
    // Fallback stub for display
    nodes.value = [
      {
        name: 'worker-01',
        manifest: { exists: true, state: 'Ready' },
        hypervisor: { exists: true, state: 'running' },
        drift: 'aligned'
      },
      {
        name: 'worker-02',
        manifest: { exists: true, state: 'Ready' },
        hypervisor: { exists: true, state: 'shut-off' },
        drift: 'state-mismatch'
      }
    ]
    stats.value = { manifests: 2, vms: 2, running: 1, drift: 1, jobs: 0 }
  }
})
</script>

<style scoped>
@reference "../styles/base.css";
.metric-card {
  @apply bg-[#0a001a] border border-[#9d00ff] p-4 flex flex-col gap-1;
}
.metric-label {
  @apply text-[10px] text-gray-500 font-mono font-bold tracking-widest uppercase;
}
.metric-value {
  @apply text-2xl font-mono;
}
</style>
