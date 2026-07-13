#!/usr/bin/env bash
# ============================================================================
#  GENERATE HOST README — Live System Documentation
# ============================================================================
#  Generates a HOST-README.md capturing the current state of this machine:
#  hardware, OS, network, Docker services, firewall, storage, Tailscale,
#  SSH config, and more. Run periodically or on system changes.
#
#  Usage:  sudo bash generate-readme.sh [--output <path>]
#
#  Default output: ~/HOST-README.md
#  Pairs with homelab-snapshot.sh — run this first for human-readable docs,
#  then snapshot for machine-restorable backups.
# ============================================================================

set -euo pipefail

OUTPUT="${2:-${HOME}/HOST-README.md}"
[[ "${1:-}" == "--output" ]] && OUTPUT="$2"

# Adjust for sudo
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo "~$ACTUAL_USER")
OUTPUT="${OUTPUT/#\~/$ACTUAL_HOME}"
OUTPUT="${OUTPUT/#\$HOME/$ACTUAL_HOME}"

[[ $EUID -ne 0 ]] && { echo "Run with: sudo bash $0 [--output <path>]"; exit 1; }

# ── Gather Data ──────────────────────────────────────────────────────────
HOSTNAME_STR=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')
UPTIME_STR=$(uptime -p 2>/dev/null | sed 's/^up //' || echo "unknown")
BOOT_TIME=$(who -b 2>/dev/null | awk '{print $3, $4}' || echo "unknown")

# Hardware
CPU_MODEL=$(lscpu 2>/dev/null | awk -F: '/Model name/ {gsub(/^ +/,"",$2); print $2; exit}' || echo "unknown")
CPU_CORES=$(nproc 2>/dev/null || echo "?")
RAM_TOTAL=$(free -h 2>/dev/null | awk '/^Mem:/ {print $2}' || echo "?")
RAM_USED=$(free -h 2>/dev/null | awk '/^Mem:/ {print $3}' || echo "?")
RAM_FREE=$(free -h 2>/dev/null | awk '/^Mem:/ {print $7}' || echo "?")
SWAP_TOTAL=$(free -h 2>/dev/null | awk '/^Swap:/ {print $2}' || echo "none")
DISK_ROOT=$(df -h / 2>/dev/null | awk 'NR==2 {printf "%s used / %s total (%s)", $3, $2, $5}' || echo "unknown")

# Detect if VM or physical
VIRT_TYPE="Physical"
if systemd-detect-virt &>/dev/null 2>&1; then
    VIRT_DETECT=$(systemd-detect-virt 2>/dev/null)
    [[ "$VIRT_DETECT" != "none" ]] && VIRT_TYPE="VM (${VIRT_DETECT})"
fi

# Check for battery (laptop)
BATTERY_INFO=""
if [[ -d /sys/class/power_supply/BAT0 ]]; then
    BAT_STATUS=$(cat /sys/class/power_supply/BAT0/status 2>/dev/null || echo "unknown")
    BAT_CAPACITY=$(cat /sys/class/power_supply/BAT0/capacity 2>/dev/null || echo "?")
    BATTERY_INFO="Battery: ${BAT_CAPACITY}% (${BAT_STATUS})"
fi

# OS
OS_PRETTY=$(lsb_release -ds 2>/dev/null || cat /etc/os-release 2>/dev/null | awk -F= '/^PRETTY_NAME/ {gsub(/"/,"",$2); print $2}' || echo "unknown")
KERNEL=$(uname -r)

# Desktop environment
DESKTOP_INFO="Headless (no display manager)"
if systemctl is-active lightdm &>/dev/null 2>&1; then
    WM=$(wmctrl -m 2>/dev/null | awk '/Name:/ {print $2}' || echo "unknown")
    DESKTOP_INFO="LightDM + ${WM:-IceWM}"
elif systemctl is-active gdm3 &>/dev/null 2>&1; then
    DESKTOP_INFO="GDM3"
fi

# Network — primary
PRIMARY_IFACE=$(ip route 2>/dev/null | awk '/default/ {print $5; exit}')
PRIMARY_IP=$(ip -4 addr show "$PRIMARY_IFACE" 2>/dev/null | awk '/inet / {print $2; exit}')
GATEWAY=$(ip route 2>/dev/null | awk '/default/ {print $3; exit}')
MAC_ADDR=$(ip link show "$PRIMARY_IFACE" 2>/dev/null | awk '/ether/ {print $2}')
DNS_SERVERS=$(resolvectl status 2>/dev/null | awk '/DNS Servers/ {for(i=3;i<=NF;i++) printf $i" "; exit}' || \
              grep -v '^#' /etc/resolv.conf 2>/dev/null | awk '/nameserver/ {printf $2" "}' || echo "unknown")

# Network — all interfaces
ALL_IFACES=$(ip -4 addr show scope global 2>/dev/null | awk '/inet / {print $NF, $2}' || echo "none")

# Tailscale
TS_STATUS="not installed"
TS_IP=""
TS_HOSTNAME=""
if command -v tailscale &>/dev/null; then
    TS_IP=$(tailscale ip -4 2>/dev/null || echo "")
    TS_HOSTNAME=$(tailscale status --json 2>/dev/null | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('Self',{}).get('HostName',''))" 2>/dev/null || echo "")
    TS_BACKEND=$(tailscale status --json 2>/dev/null | \
        python3 -c "import sys,json; print(json.load(sys.stdin).get('BackendState',''))" 2>/dev/null || echo "")
    if [[ "$TS_BACKEND" == "Running" ]]; then
        TS_STATUS="connected"
        TS_PEERS=$(tailscale status 2>/dev/null | grep -c ' ' || echo 0)
    else
        TS_STATUS="installed, not connected"
    fi
fi

# SSH
SSH_PORT=$(grep -E '^Port ' /etc/ssh/sshd_config.d/*.conf /etc/ssh/sshd_config 2>/dev/null | head -1 | awk '{print $2}')
[[ -z "$SSH_PORT" ]] && SSH_PORT="22"
SSH_PASS=$(grep -rE '^PasswordAuthentication' /etc/ssh/sshd_config.d/ /etc/ssh/sshd_config 2>/dev/null | head -1 | awk '{print $2}')
[[ -z "$SSH_PASS" ]] && SSH_PASS="yes (default)"
SSH_USERS=$(grep -rE '^AllowUsers' /etc/ssh/sshd_config.d/ /etc/ssh/sshd_config 2>/dev/null | head -1 | sed 's/AllowUsers //')
[[ -z "$SSH_USERS" ]] && SSH_USERS="all (no restriction)"

# UFW
UFW_STATUS="not installed"
UFW_RULES=""
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(ufw status 2>/dev/null | head -1 | awk '{print $2}' || echo "unknown")
    UFW_RULES=$(ufw status numbered 2>/dev/null | grep -c '^\[' || echo 0)
fi

# Docker
DOCKER_VERSION="not installed"
DOCKER_CONTAINERS=""
DOCKER_RUNNING=0
if command -v docker &>/dev/null; then
    DOCKER_VERSION=$(docker --version 2>/dev/null | sed 's/Docker version //' | cut -d',' -f1)
    DOCKER_RUNNING=$(docker ps -q 2>/dev/null | wc -l || echo 0)
fi

# Fail2Ban
F2B_STATUS="not installed"
if command -v fail2ban-client &>/dev/null; then
    F2B_STATUS=$(systemctl is-active fail2ban 2>/dev/null || echo "inactive")
    F2B_BANS=$(fail2ban-client status sshd 2>/dev/null | awk '/Currently banned/ {print $NF}' || echo "0")
fi

# Storage / RAID
RAID_STATUS=""
if [[ -f /proc/mdstat ]] && grep -q 'md[0-9]' /proc/mdstat 2>/dev/null; then
    RAID_STATUS=$(cat /proc/mdstat 2>/dev/null | grep -A1 'md[0-9]' | head -4)
fi

# ── Generate README ──────────────────────────────────────────────────────
cat > "$OUTPUT" <<README
# ${HOSTNAME_STR} — Host README
> Auto-generated: ${TIMESTAMP}
> Uptime: ${UPTIME_STR} (since ${BOOT_TIME})

---

## Hardware

| Field | Value |
|-------|-------|
| Type | ${VIRT_TYPE} |
| CPU | ${CPU_MODEL} (${CPU_CORES} cores) |
| RAM | ${RAM_TOTAL} total, ${RAM_USED} used, ${RAM_FREE} available |
| Swap | ${SWAP_TOTAL} |
| Disk (/) | ${DISK_ROOT} |
$([ -n "$BATTERY_INFO" ] && echo "| Battery | ${BATTERY_INFO} |")

## OS & Desktop

| Field | Value |
|-------|-------|
| OS | ${OS_PRETTY} |
| Kernel | ${KERNEL} |
| Display | ${DESKTOP_INFO} |

## Network

### Physical
| Field | Value |
|-------|-------|
| Primary interface | ${PRIMARY_IFACE} |
| IP | ${PRIMARY_IP} |
| Gateway | ${GATEWAY} |
| DNS | ${DNS_SERVERS} |
| MAC | ${MAC_ADDR} |

**All interfaces:**
\`\`\`
${ALL_IFACES}
\`\`\`
README

# Tailscale section
if [[ -n "$TS_IP" ]]; then
    cat >> "$OUTPUT" <<README

### Tailscale
| Field | Value |
|-------|-------|
| Status | ${TS_STATUS} |
| IP | ${TS_IP} |
| Hostname | ${TS_HOSTNAME} |
| Peers | ${TS_PEERS:-unknown} |

**Mesh peers:**
\`\`\`
$(tailscale status 2>/dev/null || echo "unable to query")
\`\`\`
README
fi

# SSH section
cat >> "$OUTPUT" <<README

## SSH

| Field | Value |
|-------|-------|
| Port | ${SSH_PORT} |
| Password auth | ${SSH_PASS} |
| Allowed users | ${SSH_USERS} |

**Connect:**
\`\`\`bash
ssh -p ${SSH_PORT} ${ACTUAL_USER}@${PRIMARY_IP%%/*}
$([ -n "$TS_HOSTNAME" ] && echo "ssh -p ${SSH_PORT} ${ACTUAL_USER}@${TS_HOSTNAME}  # via Tailscale MagicDNS")
\`\`\`

## Firewall

| Field | Value |
|-------|-------|
| UFW status | ${UFW_STATUS} |
| Rules | ${UFW_RULES} |
| Fail2Ban | ${F2B_STATUS}$([ -n "$F2B_BANS" ] && [ "$F2B_BANS" != "0" ] && echo " (${F2B_BANS} currently banned)") |

**UFW rules:**
\`\`\`
$(ufw status numbered 2>/dev/null || echo "UFW not available")
\`\`\`
README

# Docker section
if command -v docker &>/dev/null; then
    cat >> "$OUTPUT" <<README

## Docker

| Field | Value |
|-------|-------|
| Version | ${DOCKER_VERSION} |
| Running containers | ${DOCKER_RUNNING} |

**Containers:**
\`\`\`
$(docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null || echo "none")
\`\`\`

**Volumes:**
\`\`\`
$(docker volume ls --format 'table {{.Name}}\t{{.Driver}}' 2>/dev/null || echo "none")
\`\`\`

**Networks (custom):**
\`\`\`
$(docker network ls --format 'table {{.Name}}\t{{.Driver}}\t{{.Scope}}' 2>/dev/null | grep -v '^bridge\|^host\|^none' || echo "none")
\`\`\`
README
fi

# Listening ports
cat >> "$OUTPUT" <<README

## Listening Ports

\`\`\`
$(ss -tulnp 2>/dev/null | head -30 || echo "unable to query")
\`\`\`
README

# Storage / RAID
if [[ -n "$RAID_STATUS" ]]; then
    cat >> "$OUTPUT" <<README

## RAID

\`\`\`
${RAID_STATUS}
\`\`\`
README
fi

# Disk usage
cat >> "$OUTPUT" <<README

## Disk Usage

\`\`\`
$(df -h --output=target,size,used,avail,pcent -x tmpfs -x devtmpfs -x squashfs 2>/dev/null || df -h 2>/dev/null)
\`\`\`
README

# Cron / scheduled tasks
cat >> "$OUTPUT" <<README

## Scheduled Tasks

**User crontab (${ACTUAL_USER}):**
\`\`\`
$(crontab -u "$ACTUAL_USER" -l 2>/dev/null || echo "no crontab")
\`\`\`

**Root crontab:**
\`\`\`
$(crontab -l 2>/dev/null || echo "no crontab")
\`\`\`

**Systemd timers:**
\`\`\`
$(systemctl list-timers --no-pager 2>/dev/null | head -15 || echo "none")
\`\`\`
README

# Package summary
cat >> "$OUTPUT" <<README

## Key Packages

\`\`\`
$(apt-mark showmanual 2>/dev/null | sort | tr '\n' ' ' | fold -s -w 80 || echo "unable to query")
\`\`\`
README

# Footer
cat >> "$OUTPUT" <<README

---

*Generated by \`generate-readme.sh\` on ${TIMESTAMP}*
*Re-run: \`sudo bash generate-readme.sh --output ${OUTPUT}\`*
README

# Fix ownership
chown "${ACTUAL_USER}:${ACTUAL_USER}" "$OUTPUT" 2>/dev/null || true

echo "✔ HOST-README.md generated: ${OUTPUT}"
echo "  $(wc -l < "$OUTPUT") lines"
