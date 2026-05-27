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
- Environment aktivieren: ``source .venv/bin/activate``
- Pip package list checken: ``pip list``
- Optional pip packages installieren: ``pip install -r src/rpi_4/requirements.txt``
- Code ausführen: ``sudo .venv/bin/python -m src.rpi_4.main`` (updated, wichtig für Memory-Zugriff durch die rpi_ws281x library)


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
