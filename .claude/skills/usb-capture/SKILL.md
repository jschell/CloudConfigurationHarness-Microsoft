---
name: usb-capture
description: Use when capturing USB traffic for debugging devices, analyzing HID input, or reverse-engineering USB protocols
---

# USB Packet Capture

> **Requires admin/root privileges.** See [Platform Setup](references/platform-setup.md) for one-time configuration.

## Workflow

1. **Discover** → Find target device
2. **Verify** → Test capture permissions
3. **Fix** → Run platform setup if denied
4. **Capture** → Start tshark with filters

## Platform Quick Reference

| Action | Linux | Windows | macOS |
|--------|-------|---------|-------|
| **List USB devices** | `lsusb` | `USBPcapCMD.exe -d` | `system_profiler SPUSBDataType` |
| **List interfaces** | `tshark -D \| grep usbmon` | `tshark -D \| findstr USBPcap` | `tshark -D \| grep XHC` |
| **Load driver** | `sudo modprobe usbmon` | (auto with USBPcap) | (built-in, limited) |
| **Test capture** | `tshark -i usbmon0 -c 1` | `tshark -i \\.\USBPcap1 -c 1` | `tshark -i XHC20 -c 1` |

## Capture Commands

**Linux:**
```bash
# All USB buses
tshark -i usbmon0 -w usb.pcap

# Specific bus (bus 1)
tshark -i usbmon1 -w usb.pcap

# Filter specific device (bus.device.endpoint)
tshark -i usbmon1 -Y "usb.addr == 1.4.1" -w usb.pcap
```

**Windows:**
```powershell
# List available root hubs
USBPcapCMD.exe -d

# Capture specific root hub
tshark.exe -i "\\.\USBPcap1" -w usb.pcap

# With device filter
tshark.exe -i "\\.\USBPcap1" -Y "usb.addr == 1.4.0" -w usb.pcap
```

**macOS:**
```bash
# Check if XHC interface available
tshark -D | grep -i xhc

# Capture (limited support)
sudo tshark -i XHC20 -w usb.pcap
```

> **macOS limitation:** Apple restricts USB sniffing. XHC interfaces may not be available on all systems. Consider Linux VM for full USB capture.

## Common Display Filters

```bash
usb.addr == 1.4.1              # Specific device address
usb.transfer_type == 0x01      # Isochronous transfers
usb.transfer_type == 0x02      # Bulk transfers
usb.transfer_type == 0x03      # Interrupt transfers
usb.capdata                    # Packets with payload (HID data)
usb.bInterfaceClass == 0x03    # HID class devices
usb.idVendor == 0x046d         # Specific vendor (Logitech)
usb.endpoint_address.direction == 1  # IN transfers (device→host)
```

## Device Identification

Map friendly names to USB addresses:

```bash
# Linux: Find device
lsusb
# Bus 001 Device 004: ID 046d:c52b Logitech, Inc. Unifying Receiver

# Capture that device (bus 1, device 4)
tshark -i usbmon1 -Y "usb.device_address == 4"
```

See [Device Mapping](references/device-mapping.md) for detailed workflows.

## Output Formats

```bash
# Verbose decode
tshark -i usbmon1 -V

# Extract HID payload only
tshark -i usbmon1 -T fields -e usb.capdata

# JSON output
tshark -i usbmon1 -T json
```

## See Also

- [Platform Setup](references/platform-setup.md) - Permission configuration
- [Device Mapping](references/device-mapping.md) - Finding device addresses
- Related: **packet-capture** for network traffic
