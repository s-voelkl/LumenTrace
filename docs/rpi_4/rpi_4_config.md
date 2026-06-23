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

- Ordner finden: ``cd ./documents/repos/lumentrace``
- Enviroment erstellen: ``python3 -m venv .venv``
- Environment aktivieren: ``source .venv/bin/activate``
- Pip packages installieren: ``pip install -r ./src/rpi_4/requirements.txt``
- Pip package list checken: ``pip list``
- Code ausführen: ``sudo .venv/bin/python -m src.rpi_4.main`` (updated, wichtig für Memory-Zugriff durch die rpi_ws281x library)

```shell
source .venv/bin/activate
sudo .venv/bin/python -m src.rpi_4.main
```

## Installationen

### Sound mit USB Soundkarte

Ensure the USB sound card is recognized and set as the default:

```bash
# List all audio devices
aplay -l

# Identify your USB sound card (usually appears as a separate card, e.g., "card 3: USB Audio Device")
# Set the USB sound card as default (update card number if different):
echo "defaults.pcm.card 3" | sudo tee -a /etc/asound.conf
echo "defaults.ctl.card 3" | sudo tee -a /etc/asound.conf

# Verify the USB sound card is now default
aplay -l
cat /etc/asound.conf

# Test audio output on Raspberry Pi (before Docker)
speaker-test -c 2 -t sine -f 1000 -l 1
```

Once Docker is running, verify audio inside the container:

```bash
sudo docker compose -f docker-compose.yaml exec -T lumentrace aplay -l
sudo docker compose -f docker-compose.yaml exec -T lumentrace speaker-test -c 2 -t sine -f 1000 -l 1
```

If playback fails with "Playback open error: -524", the device file permissions are not accessible inside the container:

```bash
# Check that /dev/snd is properly accessible on the host
ls -la /dev/snd/

# Restart the Docker container to apply new device permissions
sudo docker compose -f docker-compose.yaml restart

# Ensure /dev/snd is explicitly mounted with RW access in docker-compose.yaml (already configured)
```

If `speaker-test` is not found inside the container, check Docker logs for audio device errors:

```bash
sudo docker compose -f docker-compose.yaml logs lumentrace | grep -i "audio\|device\|asound"
```

### Docker installieren

```shell
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

Starte den Raspberry neu, dann mit ``docker --version`` überprüfen, ob die Installation erfolgreich war.
Docker Compose auch mit ``docker compose version`` überprüfen.

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
