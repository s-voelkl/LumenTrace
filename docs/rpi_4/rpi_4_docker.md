# Docker on Raspberry Pi 4

This document describes how to use Docker to run LumenTrace on a Raspberry Pi 4. Docker provides a consistent, isolated environment and automatically handles system-level dependencies and privileged hardware access.

## Installation

To install Docker and Docker Compose on your Raspberry Pi:

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

After installation, reboot the Raspberry Pi and verify the version:

```bash
docker --version
docker compose version
```

## Usage

Use the following commands to stop, remove, build, and start the Docker container. The `-d` flag runs the container in detached mode.

```bash
sudo docker compose -f docker-compose.yaml stop
sudo docker compose -f docker-compose.yaml down
sudo docker compose -f docker-compose.yaml build
sudo docker compose -f docker-compose.yaml up -d
```

## Autostart on Boot

To ensure LumenTrace starts automatically after a reboot, enable the Docker daemon and use the provided systemd service.

1. **Enable Docker daemon:**

    ```bash
    sudo systemctl enable docker
    sudo systemctl start docker
    ```

2. **Install and enable the systemd unit:**

    Ensure the container is built and started once (as described above), then run:

    ```bash
    sudo cp deploy/systemd/lumentrace.service /etc/systemd/system/lumentrace.service
    sudo systemctl daemon-reload
    sudo systemctl enable lumentrace.service
    sudo systemctl start lumentrace.service
    ```

3. **Verify status:**

    ```bash
    sudo systemctl status lumentrace.service
    sudo docker compose -f docker-compose.yaml ps
    ```

> [!IMPORTANT]
> If your repository path is not `/home/lumentrace/Documents/repos/LumenTrace`, update the `WorkingDirectory`, `ExecStart`, and `ExecStop` paths in `deploy/systemd/lumentrace.service` before copying the file.

## Audio Troubleshooting

If the game starts without sound:

1. **Check Logs:**

    ```bash
    sudo docker compose -f docker-compose.yaml logs lumentrace | grep -i "audio\|device"
    ```

2. **Verify Device Access:**

    ```bash
    # List audio devices inside the container
    sudo docker compose -f docker-compose.yaml exec -T lumentrace aplay -l

    # Test audio output (sine wave)
    sudo docker compose -f docker-compose.yaml exec -T lumentrace speaker-test -c 2 -t sine -f 1000 -l 1
    ```

3. **Fix "Playback open error: -524":**
    If audio device files cannot be accessed, restart the container to reapply device mount permissions:

    ```bash
    sudo docker compose -f docker-compose.yaml restart
    ```

4. **Rebuild from Scratch:**

    ```bash
    sudo docker compose -f docker-compose.yaml build --no-cache
    ```

For general system-level audio configuration (USB sound cards, etc.), see [docs/rpi_4/rpi_4_config.md](docs/rpi_4/rpi_4_config.md#sound-mit-usb-soundkarte).
