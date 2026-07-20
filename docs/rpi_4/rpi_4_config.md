# Raspberry Pi 4 Config

## OS

- Raspberry Pi OS (64-bit): A port of Debian Trixie with Raspberry Pi Desktop (Recommended).
- Micro-SD: 32 GB.
- Country/Capital: Germany/Berlin
- Timezone: Europe/Berlin
- Keyboard Layout: de
- WLAN: Use "BND-Spionage 5" (SimonV)
- Enable SSH: Yes, with password (`lumentrace`)
- Raspberry Pi Connect: Yes, using a Raspberry Pi account. See private message for login credentials.

## Connection (SSH)

- Hostname: `lumentrace`
- Username: `lumentrace`
- Password: `lumentrace`
- ssh lumentrace@lumentrace

## Code Execution

- Navigate to folder: `cd /home/lumentrace/Documents/repos/LumenTrace`
- Create virtual environment: `python3 -m venv .venv`
- Activate virtual environment: `source .venv/bin/activate`
- Install pip packages: `pip install -r ./src/rpi_4/requirements.txt`
- Verify package list: `pip list`
- Run application: `sudo .venv/bin/python -m src.rpi_4.main` (Crucial for physical memory access required by the `rpi_ws281x` library)

```shell
source .venv/bin/activate
sudo .venv/bin/python -m src.rpi_4.main
```

## Hardware Preparation (SPI & PCM)

The round counters use **GPIO 10 (SPI)** and **GPIO 21 (PCM)**. You must configure your Raspberry Pi host to enable these modules and prevent onboard audio drivers from blocking them.

### 1. Enable SPI (Player 1 Round Counter)

Run `sudo raspi-config` on the host, go to **Interface Options** -> **SPI**, select **Yes** to enable it, and reboot.
Alternatively, verify that the following parameter is present in `/boot/firmware/config.txt`:

```ini
dtparam=spi=on
```

### 2. Disable Onboard Audio (Player 2 Round Counter / PCM)

Onboard audio drives analog jack/PWM sounds via PCM, which conflicts with GPIO 21 [3]. Open `/boot/firmware/config.txt` on the host:

```bash
sudo nano /boot/firmware/config.txt
```

Locate `dtparam=audio=on` and change it to `off`:

```ini
dtparam=audio=off
```

Reboot the Raspberry Pi to apply changes.

---

## Installations

### Sound with USB Sound Card

Disabling onboard audio means your USB Sound Card will shift to default index **0** instead of **3**.

```bash
# List all audio devices to verify that USB Audio is now Card 0
aplay -l

# Set your USB sound card as the system default:
echo "defaults.pcm.card 0" | sudo tee -a /etc/asound.conf
echo "defaults.ctl.card 0" | sudo tee -a /etc/asound.conf

# Verify the changes
cat /etc/asound.conf

# Test audio output on Raspberry Pi (before Docker)
sudo speaker-test -c 2 -t sine -f 1000 -l 1 -D sysdefault:CARD=2
```

For instructions on how to install and run the application with **Docker**, please see:
[docs/rpi_4/rpi_4_docker.md](rpi_4_docker.md)

## Hardware Set

- Raspberry Pi 4 Model B 4GB RAM, with 4 mounted heatsinks, original packaging included
- Official USB-C Power Supply
- Two-part enclosure (black base, transparent top cover)
- Raspberry Pi HDMI D/Male to HDMI A/Male 1m cable
- Power supply to USB-C cable, 15.3W black, original packaging included
- Raspberry Pi Micro-SD card 16GB with SD adapter
- Manuals (2x)

From Makerspace:

- SanDisk Extreme 32GB V30 U3 A1 with adapter --> inserted in RPI 4