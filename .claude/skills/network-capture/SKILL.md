---
name: network-capture
description: Use when capturing network traffic for debugging connectivity, analyzing HTTP/TCP/DNS, or troubleshooting latency issues
---

# Network Packet Capture

> See **packet-capture** for tshark installation and general filter syntax.

## Interface Discovery

| Platform | List Interfaces | Common Names |
|----------|-----------------|--------------|
| Linux | `ip link show` | eth0, enp3s0, wlan0 |
| macOS | `networksetup -listallhardwareports` | en0 (WiFi), en1 (Ethernet) |
| Windows | `Get-NetAdapter` | Ethernet, Wi-Fi |

```bash
# All platforms: tshark interface list
tshark -D
```

## Common Capture Scenarios

### HTTP Traffic

```bash
# Capture HTTP requests/responses
tshark -i eth0 -f "tcp port 80" -Y "http"

# Extract URLs
tshark -i eth0 -Y "http.request" -T fields -e http.host -e http.request.uri
```

### HTTPS/TLS

```bash
# TLS handshakes only
tshark -i eth0 -f "tcp port 443" -Y "tls.handshake"

# Extract SNI (Server Name Indication)
tshark -i eth0 -Y "tls.handshake.type == 1" -T fields -e tls.handshake.extensions_server_name
```

### DNS

```bash
# All DNS traffic
tshark -i eth0 -f "udp port 53"

# Extract queries
tshark -i eth0 -Y "dns.qry.name" -T fields -e dns.qry.name -e dns.a
```

### TCP Troubleshooting

```bash
# SYN packets (connection attempts)
tshark -i eth0 -Y "tcp.flags.syn == 1 && tcp.flags.ack == 0"

# Retransmissions
tshark -i eth0 -Y "tcp.analysis.retransmission"

# RST packets (connection resets)
tshark -i eth0 -Y "tcp.flags.rst == 1"
```

### Specific Host/Port

```bash
# Single host
tshark -i eth0 -f "host 192.168.1.100"

# Host and port combination
tshark -i eth0 -f "host 10.0.0.1 and port 443"

# Exclude local traffic
tshark -i eth0 -f "not host 127.0.0.1"
```

## Platform-Specific

### Linux

```bash
# Capture on any interface
tshark -i any -f "port 80"

# Bridge/docker traffic
tshark -i docker0 -f "port 80"
tshark -i br-xxx -f "port 443"
```

### macOS

```bash
# WiFi (usually en0)
sudo tshark -i en0 -f "port 443"

# Capture with monitor mode (requires compatible adapter)
sudo tshark -i en0 -I -f "type mgt"
```

### Windows

```powershell
# Find interface name
Get-NetAdapter | Select-Object Name, InterfaceDescription

# Capture (use exact name from tshark -D)
tshark.exe -i "Ethernet" -f "port 80"
tshark.exe -i "Wi-Fi" -f "port 443"
```

## Live Analysis

```bash
# Count packets per protocol
tshark -i eth0 -q -z io,phs -a duration:30

# Top talkers
tshark -i eth0 -q -z endpoints,ip -a duration:30

# TCP conversation stats
tshark -i eth0 -q -z conv,tcp -a duration:30
```

## Save and Analyze

```bash
# Capture to file with rotation
tshark -i eth0 -b filesize:10240 -b files:5 -w capture.pcap

# Later analysis
tshark -r capture.pcap -Y "http.response.code >= 400"
tshark -r capture.pcap -q -z http,tree
```

## See Also

- [Protocol Filters](references/protocol-filters.md)
- Parent: **packet-capture** for tshark fundamentals
- Related: **usb-capture** for USB traffic
