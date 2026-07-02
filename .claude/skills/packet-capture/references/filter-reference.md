# Tshark Filter Reference

## Capture Filters (BPF Syntax)

Applied during capture, reduces file size.

```bash
# By host
host 192.168.1.1
src host 10.0.0.1
dst host 10.0.0.2

# By port
port 80
src port 443
dst port 22
portrange 8000-9000

# By protocol
tcp
udp
icmp
arp

# Combinations
tcp port 80 or tcp port 443
host 10.0.0.1 and port 22
not port 53
```

## Display Filters (Wireshark Syntax)

Applied after capture, for analysis.

### IP
```
ip.addr == 192.168.1.1
ip.src == 10.0.0.1
ip.dst == 10.0.0.2
ip.ttl < 64
```

### TCP
```
tcp.port == 443
tcp.srcport == 8080
tcp.flags.syn == 1
tcp.flags.rst == 1
tcp.analysis.retransmission
tcp.stream eq 5
```

### HTTP
```
http.request
http.response
http.request.method == "POST"
http.host contains "example"
http.response.code == 200
```

### DNS
```
dns
dns.qry.name contains "google"
dns.flags.response == 1
```

### TLS/SSL
```
tls.handshake
tls.handshake.type == 1    # Client Hello
ssl.handshake.extensions_server_name
```

## Field Extraction

```bash
# Single field
tshark -r file.pcap -T fields -e ip.src

# Multiple fields
tshark -r file.pcap -T fields -e ip.src -e ip.dst -e tcp.port

# With separator
tshark -r file.pcap -T fields -E separator=, -e ip.src -e ip.dst

# Headers
tshark -r file.pcap -T fields -E header=y -e frame.number -e ip.src
```

## Statistics

```bash
# Protocol hierarchy
tshark -r file.pcap -q -z io,phs

# Conversations
tshark -r file.pcap -q -z conv,tcp

# HTTP requests
tshark -r file.pcap -q -z http,tree

# Endpoints
tshark -r file.pcap -q -z endpoints,ip
```
