import { ref } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null

export function useTerminalSession() {
  const terminalOpen = ref(true)
  const connectionStatus = ref('disconnected')
  const selectedTarget = ref('')

  const initTerminal = (container: HTMLElement) => {
    if (term) return
    
    term = new Terminal({
      theme: {
        background: '#000000',
        foreground: '#ff00ff',
        cursor: '#ff00ff'
      },
      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
      fontSize: 13
    })
    
    fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(container)
    fitAddon.fit()
    
    // Auto fit on window resize
    window.addEventListener('resize', () => {
      fitAddon?.fit()
    })
  }
  
  const connect = (targetName: string) => {
    if (!term) return
    
    if (ws) {
      ws.close()
    }
    
    selectedTarget.value = targetName
    connectionStatus.value = 'connecting'
    term.clear()
    term.writeln(`Connecting to ${targetName}...`)
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    ws = new WebSocket(`${protocol}//${host}/api/terminal/ws`)
    
    ws.onopen = () => {
      connectionStatus.value = 'connected'
      term?.writeln('Connected.')
      fitAddon?.fit()
      
      term?.onData((data) => {
        ws?.send(JSON.stringify({ type: 'input', data }))
      })
    }
    
    ws.onmessage = (event) => {
      term?.write(event.data)
    }
    
    ws.onclose = () => {
      connectionStatus.value = 'disconnected'
      term?.writeln('\r\nDisconnected from host.')
    }
  }
  
  return {
    terminalOpen,
    connectionStatus,
    selectedTarget,
    initTerminal,
    connect
  }
}
