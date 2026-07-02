---
name: packet-capture
description: Use when capturing network traffic, analyzing protocols, or debugging network issues with tshark/Wireshark
---

# Packet Capture

## Prerequisites

| Platform | Install |
|----------|---------|
| Linux | `sudo apt install tshark` / `sudo dnf install wireshark-cli` |
| macOS | `brew install wireshark` |
| Windows | [Wireshark installer](https://www.wireshark.org/download.html) (includes tshark) |

## Quick Start

```bash
# List interfaces
tshark -D

# Capture 100 packets
tshark -i eth0 -c 100

# Capture to file
tshark -i eth0 -w capture.pcap

# Read capture file
tshark -r capture.pcap
```

## Common Filters

### Capture Filters (BPF - applied during capture)
```bash
tshark -i eth0 -f "port 443"           # HTTPS only
tshark -i eth0 -f "host 192.168.1.1"   # Specific host
tshark -i eth0 -f "tcp port 80"        # HTTP
```

### Display Filters (applied to captured data)
```bash
tshark -r file.pcap -Y "http.request"          # HTTP requests
tshark -r file.pcap -Y "tcp.flags.syn == 1"    # SYN packets
tshark -r file.pcap -Y "ip.addr == 10.0.0.1"   # Specific IP
```

## Output Formats

| Flag | Output |
|------|--------|
| (none) | Summary lines |
| `-V` | Verbose/full decode |
| `-T fields -e http.host` | Extract specific fields |
| `-T json` | JSON output |
| `-T pdml` | XML output |

## Permission Requirements

**Linux:**
```bash
sudo usermod -aG wireshark $USER
sudo setcap 'CAP_NET_RAW,CAP_NET_ADMIN=eip' $(which dumpcap)
# Logout/login required
```

**macOS:**
```bash
# Grant access to BPF devices
sudo dseditgroup -o edit -a $USER -t user access_bpf
```

**Windows:** Run as Administrator or install Npcap with "Install in WinPcap API-compatible mode"

## Circular Buffer (Long Captures)

```bash
# 10 files, 100MB each, rotating
tshark -i eth0 -b filesize:102400 -b files:10 -w capture.pcap
```

## Platform Commands

| Action | Linux/macOS | Windows |
|--------|-------------|---------|
| List interfaces | `tshark -D` | `tshark.exe -D` |
| Capture | `tshark -i eth0` | `tshark.exe -i Ethernet` |
| Stop | Ctrl+C | Ctrl+C |

## See Also

- [Filter Reference](references/filter-reference.md)
- Child skills:
  - **network-capture** - Network traffic (HTTP, DNS, TCP)
  - **usb-capture** - USB device traffic
