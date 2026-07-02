# USB Device Mapping

Map friendly device names to USB addresses for filtering.

## Linux

### List All Devices

```bash
lsusb
# Bus 001 Device 004: ID 046d:c52b Logitech, Inc. Unifying Receiver
# Bus 002 Device 003: ID 8087:0a2b Intel Corp. Bluetooth
```

**Format:** `Bus XXX Device YYY: ID vendor:product Name`

### Detailed Device Info

```bash
# Verbose output
lsusb -v -d 046d:c52b

# Tree view showing hierarchy
lsusb -t
```

### Map to Capture Filter

| lsusb Output | Capture Interface | Filter |
|--------------|-------------------|--------|
| Bus 001 Device 004 | usbmon1 | `usb.device_address == 4` |
| Bus 002 Device 003 | usbmon2 | `usb.device_address == 3` |

```bash
# Capture device 4 on bus 1
tshark -i usbmon1 -Y "usb.device_address == 4"
```

### Find by Vendor/Product ID

```bash
# Filter by vendor ID (Logitech = 046d)
tshark -i usbmon0 -Y "usb.idVendor == 0x046d"

# Filter by product ID
tshark -i usbmon0 -Y "usb.idProduct == 0xc52b"
```

---

## Windows

### List Root Hubs

```powershell
# Using USBPcapCMD
& "C:\Program Files\USBPcap\USBPcapCMD.exe" -d

# Output shows device tree:
# \\.\USBPcap1
#   [Port 1] USB Composite Device
#   [Port 3] Logitech USB Receiver
```

### Device Manager Method

```powershell
# List USB devices via PowerShell
Get-PnpDevice -Class USB | Select-Object Status, Class, FriendlyName, InstanceId
```

### Map to Capture Filter

```powershell
# Capture on specific root hub
tshark.exe -i "\\.\USBPcap1" -w capture.pcap

# Filter by port (from USBPcapCMD output)
tshark.exe -i "\\.\USBPcap1" -Y "usb.addr contains .3."
```

---

## macOS

### List USB Devices

```bash
# Full USB device tree
system_profiler SPUSBDataType

# Compact list
system_profiler SPUSBDataType | grep -E "(Product ID|Vendor ID|Location ID|:$)"
```

### ioreg Method

```bash
# USB device registry
ioreg -p IOUSB -l -w 0

# Find specific device
ioreg -p IOUSB | grep -i logitech
```

### Map to Capture

macOS USB capture is limited. Use Location ID when available:

```bash
# If XHC interface exists
sudo tshark -i XHC20 -Y "usb.addr == 0x14100000"
```

---

## USB Address Format

| Component | Description | Example |
|-----------|-------------|---------|
| Bus | USB controller number | 1, 2 |
| Device | Device number on bus | 4, 7 |
| Endpoint | Specific endpoint | 0 (control), 1-15 |

**Full address format:** `bus.device.endpoint`

Example: `1.4.1` = Bus 1, Device 4, Endpoint 1

## Common Filters by Device Type

| Device Type | Class Code | Filter |
|-------------|------------|--------|
| HID (keyboard/mouse) | 0x03 | `usb.bInterfaceClass == 0x03` |
| Mass Storage | 0x08 | `usb.bInterfaceClass == 0x08` |
| Audio | 0x01 | `usb.bInterfaceClass == 0x01` |
| Video | 0x0e | `usb.bInterfaceClass == 0x0e` |
| Wireless | 0xe0 | `usb.bInterfaceClass == 0xe0` |
