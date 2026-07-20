# Docker and Systemd Integration Architecture

LumenTrace uses Docker [merkel:2014docker] for containerized deployment and systemd for service management on the Raspberry Pi 4 [magpi:2024raspberry], ensuring consistent runtime environments and automated lifecycle control.

## Docker Architecture

**Container Image**: Built from Python 3.14 slim with native C extensions (GPIO/LED libraries) and ALSA audio support. Dependencies are cached independently to accelerate rebuilds.

**Runtime Configuration**:

- Runs in privileged mode with access to `/dev` hierarchy for GPIO, SPI, UART, and PCM control
- Volume mounts: `/dev:/dev`, `/dev/snd:/dev/snd`, `/run/dbus:/run/dbus` (read-only)
- Cgroup device rules restrict access to ALSA (device 116) and USB devices (device 189)
- Environment: `ALSA_CARD=0` (USB sound card), optional PulseAudio socket

**Image Optimization**: `.dockerignore` excludes documentation, logs, archived code, tests, and development modules while preserving ``assets/`` (sound files)

## Systemd Service Integration

The `lumentrace.service` unit file manages the Docker container as a system service:

- **Type**: `oneshot` — executes `docker compose up -d` on start and `docker compose down` on stop
- **Dependencies**:
  - `Requires=docker.service` (hard dependency)
  - `After=docker.service network-online.target` (ordering)
- **Working Directory**: `/home/lumentrace/Documents/repos/LumenTrace`
- **Boot Integration**: `WantedBy=multi-user.target` enables auto-start; `RemainAfterExit=yes` maintains active state
- **Restart Policy**: Configured in docker-compose.yaml as `restart: unless-stopped`

## Hardware Access and Device Binding

The container accesses Raspberry Pi hardware through Linux device files:

- **GPIO**: GPIO 18/19 (LED control), GPIO 10 (SPI), GPIO 21 (PCM) via `/dev/mem` and `/dev/gpiomem`
- **Serial**: UART to Pico controller via `/dev/ttyAMA0` or `/dev/ttyUSB0`
- **Audio**: ALSA through `/dev/snd/*` devices for USB sound card output
- **Privilege**: Container runs as root to maintain necessary device access permissions

## Deployment Characteristics

**Service Model**: Single-service, stateless deployment with one instance per Raspberry Pi. Container restarts are automatic via Docker's restart policy; systemd monitors the docker-compose process for overall health.

**Resource Management**: Memory limits are disabled due to Raspberry Pi 4 cgroup constraints. Device access is controlled through fine-grained cgroup rules. The container shares the host network namespace for UART and GPIO control.

**Resilience**: Auto-restart on failure, boot-time dependency ordering, graceful shutdown via `ExecStop`, and state isolation through fresh container restarts prevent state pollution.
