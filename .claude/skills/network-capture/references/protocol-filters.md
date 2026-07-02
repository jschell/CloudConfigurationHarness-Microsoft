# Network Protocol Filters

Quick reference for common protocol filters.

## Layer 3 (Network)

### IP
```
ip.addr == 192.168.1.1
ip.src == 10.0.0.1
ip.dst == 10.0.0.2
ip.ttl < 64
ip.version == 4
ipv6.addr == ::1
```

### ICMP
```
icmp
icmp.type == 8          # Echo request (ping)
icmp.type == 0          # Echo reply
icmp.type == 3          # Destination unreachable
```

## Layer 4 (Transport)

### TCP
```
tcp.port == 443
tcp.srcport == 8080
tcp.dstport == 22
tcp.flags.syn == 1
tcp.flags.ack == 1
tcp.flags.fin == 1
tcp.flags.rst == 1
tcp.flags.push == 1
tcp.stream eq 5
tcp.len > 0
tcp.window_size < 1000
tcp.analysis.retransmission
tcp.analysis.duplicate_ack
tcp.analysis.zero_window
```

### UDP
```
udp.port == 53
udp.srcport == 123
udp.length > 100
```

## Layer 7 (Application)

### HTTP
```
http
http.request
http.response
http.request.method == "GET"
http.request.method == "POST"
http.host contains "api"
http.request.uri contains "/login"
http.response.code == 200
http.response.code >= 400
http.content_type contains "json"
http.user_agent contains "curl"
```

### DNS
```
dns
dns.qry.name
dns.qry.name contains "google"
dns.qry.type == 1       # A record
dns.qry.type == 28      # AAAA record
dns.qry.type == 5       # CNAME
dns.qry.type == 15      # MX
dns.flags.response == 1
dns.flags.rcode == 3    # NXDOMAIN
```

### TLS/SSL
```
tls
tls.handshake
tls.handshake.type == 1              # Client Hello
tls.handshake.type == 2              # Server Hello
tls.handshake.type == 11             # Certificate
tls.handshake.extensions_server_name # SNI
tls.record.version == 0x0303         # TLS 1.2
tls.alert_message
```

### SSH
```
ssh
ssh.protocol
```

### DHCP
```
dhcp
dhcp.type == 1          # Discover
dhcp.type == 2          # Offer
dhcp.type == 3          # Request
dhcp.type == 5          # ACK
```

### ARP
```
arp
arp.opcode == 1         # Request
arp.opcode == 2         # Reply
arp.src.proto_ipv4 == 192.168.1.1
```

## Combining Filters

```
# AND
http.request && ip.src == 10.0.0.1

# OR
tcp.port == 80 || tcp.port == 443

# NOT
!arp && !dns

# Parentheses
(http || tls) && ip.addr == 192.168.1.1

# Complex example
tcp.flags.syn == 1 && tcp.flags.ack == 0 && !tcp.port == 22
```

## Field Extraction Examples

```bash
# HTTP hosts and URIs
tshark -Y "http.request" -T fields -e http.host -e http.request.uri

# DNS queries and responses
tshark -Y "dns" -T fields -e dns.qry.name -e dns.a -e dns.aaaa

# TLS SNI values
tshark -Y "tls.handshake.type == 1" -T fields -e tls.handshake.extensions_server_name

# TCP streams with ports
tshark -Y "tcp" -T fields -e tcp.stream -e ip.src -e tcp.srcport -e ip.dst -e tcp.dstport
```
