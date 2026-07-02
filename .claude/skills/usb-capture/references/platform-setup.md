# USB Capture Platform Setup

One-time configuration to enable USB packet capture.

## Linux

### Install Dependencies

```bash
# Debian/Ubuntu
sudo apt install tshark wireshark-common

# Fedora/RHEL
sudo dnf install wireshark-cli

# Arch
sudo pacman -S wireshark-cli
```

### Load USB Monitor Driver

```bash
# Load module (required each boot, or add to /etc/modules)
sudo modprobe usbmon

# Verify loaded
ls /sys/kernel/debug/usb/usbmon/
```

### Configure Non-Root Access

```bash
# Add user to wireshark group
sudo usermod -aG wireshark $USER

# Create udev rule for usbmon devices
echo 'SUBSYSTEM=="usbmon", GROUP="wireshark", MODE="0640"' | sudo tee /etc/udev/rules.d/99-usbmon.rules

# Grant capabilities to dumpcap
sudo setcap 'CAP_NET_RAW,CAP_NET_ADMIN=eip' $(which dumpcap)

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Logout and login for group membership to take effect
```

### Verify Setup

```bash
# Should work without sudo
tshark -D | grep usbmon
tshark -i usbmon0 -c 1
```

---

## Windows

### Install USBPcap

1. Download from [USBPcap releases](https://github.com/desowin/usbpcap/releases)
2. Run installer as Administrator
3. Reboot when prompted

### Verify Installation

```powershell
# Check USBPcap service
Get-Service USBPcap

# List USB root hubs
& "C:\Program Files\USBPcap\USBPcapCMD.exe" -d

# Test capture (requires admin PowerShell)
tshark.exe -D | Select-String USBPcap
```

### Running Captures

USBPcap requires Administrator privileges:

```powershell
# Option 1: Run PowerShell as Administrator
Start-Process powershell -Verb RunAs

# Option 2: Use gsudo (install via winget/scoop)
gsudo tshark.exe -i "\\.\USBPcap1" -c 10
```

### Troubleshooting

```powershell
# Restart USBPcap service
Restart-Service USBPcap

# Reinstall filter driver
& "C:\Program Files\USBPcap\USBPcapCMD.exe" --install-filter
```

---

## macOS

### Install Wireshark

```bash
brew install wireshark
```

### Check XHC Interface

```bash
# List interfaces
tshark -D | grep -i xhc

# If XHC20 or similar appears, capture is possible
sudo tshark -i XHC20 -c 1
```

### Limitations

macOS has significant restrictions on USB packet capture:

| Issue | Details |
|-------|---------|
| **SIP (System Integrity Protection)** | Blocks low-level USB access |
| **No usbmon equivalent** | Apple doesn't expose USB monitor interface |
| **XHC availability** | Varies by hardware and macOS version |

### Workarounds

1. **Use Linux VM**: Run USB capture in a Linux VM with USB passthrough
2. **Boot Camp**: Dual-boot to Windows/Linux for full capture
3. **USB Prober**: Apple's USB Prober tool (from Xcode Additional Tools) provides limited inspection

### USB Prober (Alternative)

```bash
# Install Xcode Additional Tools from Apple Developer site
# Open USB Prober from /Applications/Utilities/
```

---

## Verification Checklist

| Platform | Command | Expected |
|----------|---------|----------|
| Linux | `tshark -i usbmon0 -c 1` | Packet captured |
| Windows | `tshark -i \\.\USBPcap1 -c 1` | Packet captured |
| macOS | `sudo tshark -i XHC20 -c 1` | Packet captured (if available) |

If capture fails with "permission denied", re-run platform setup steps.
