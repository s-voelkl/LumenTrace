# Raspberry 4 Config

## OS

- Raspberry Pi OS (64-bit): A port of Debian Trixie with Raspberry Pi Desktop (Recommended).
- Micro-SD: 32 GB.
- Hauptstadt: Berlin/Germany
- Zeitzone: Europe/Berlin
- Tastaturlayout: de
- Wlan: Erst mal das bei SimonV "BND-Spionage 5"
- SSh aktivieren: Ja, mit Passwort (lumentrace)
- Raspberry Pi Connect: Ja, mit einem Raspberry Pi Account. Siehe Privatnachricht für Zugangsdaten.

## Verbindung (SSH)

- Hostname: lumentrace
- Username: lumentrace
- Passwort: lumentrace
- ssh lumentrace@

## Codeausführung

- Ordner finden: ``cd /home/lumentrace/Documents/repos/LumenTrace``
- Enviroment erstellen: ``python3 -m venv .venv``
- Environment aktivieren: ``source .venv/bin/activate``
- Pip packages installieren: ``pip install -r ./src/rpi_4/requirements.txt``
- Pip package list checken: ``pip list``
- Code ausführen: ``sudo .venv/bin/python -m src.rpi_4.main`` (Wichtig für Memory-Zugriff durch die rpi_ws281x library)

```shell
source .venv/bin/activate
sudo .venv/bin/python -m src.rpi_4.main
```

## Hardware-Vorbereitung (SPI & PCM)

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

## Installationen

### Sound mit USB Soundkarte

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
speaker-test -c 2 -t sine -f 1000 -l 1
```

For instructions on how to install and run the application with **Docker**, please see:
[docs/rpi_4/rpi_4_docker.md](rpi_4_docker.md)

## Hardware-Set

- Raspberry Pi 4 Model B 4GB RAM, mit 4 montierten Kühlkörpern, mit Verpackung
- Official USB-C Power Supply
- Gehäuse aus zwei Teilen (schwarze Basis unten, transparente Abdeckung oben)
- Raspberry PI HDMI D/Male zu HDMI A/Male 1m Kabel
- Ladestecker Netzteil zu USB-C Kabel, 15,3W schwarz, mit Verpackung
- Raspberry Pi Micro-SD-Karte 16GB mit SD-Adapter
- Anleitungen 2x

Von Makerspace:

- SanDisk Extreme 32GB V30 U3 A1 mit Adapter --> steckt im RPI 4