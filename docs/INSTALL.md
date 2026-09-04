# Installation

Requires **Python 3.9+** on **Linux** (the CPU/memory/disk/network panels work
anywhere psutil runs; the *Services* panel needs `systemctl`, and load average
needs a POSIX host).

Pick one of the three methods below. All of them leave the dashboard on
`http://127.0.0.1:8080` with the web terminal disabled — see
[SECURITY.md](SECURITY.md) before exposing it.

---

## 1. pipx (simplest)

```bash
pipx install git+https://github.com/xelest/mav-monitor.git
mavmon
```

Or into a plain venv:

```bash
python3 -m venv .venv
.venv/bin/pip install git+https://github.com/xelest/mav-monitor.git
.venv/bin/mavmon
```

---

## 2. Docker

```bash
git clone https://github.com/xelest/mav-monitor.git
cd mav-monitor
docker compose -f deploy/docker-compose.yml up -d
```

The compose file runs with `pid: host` (so the process list reflects the host)
and publishes only to `127.0.0.1:8080`. Adjust the `MONITOR_*` environment
block in `deploy/docker-compose.yml` as needed.

Plain `docker run`:

```bash
docker build -t mav-monitor -f deploy/Dockerfile .
docker run -d --name mav-monitor \
  --pid host \
  -p 127.0.0.1:8080:8080 \
  mav-monitor
```

---

## 3. systemd (native, recommended for a permanent install)

```bash
sudo git clone https://github.com/xelest/mav-monitor.git /opt/mav-monitor
cd /opt/mav-monitor
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt

# create a dedicated unprivileged user
sudo useradd --system --no-create-home --shell /usr/sbin/nologin mavmon

# install the unit (edit User= first, or use sed as below)
sudo sed 's/^User=CHANGE_ME/User=mavmon/' deploy/mav-monitor.service \
  | sudo tee /etc/systemd/system/mav-monitor.service

sudo systemctl daemon-reload
sudo systemctl enable --now mav-monitor
systemctl status mav-monitor
```

Verify:

```bash
curl -s http://127.0.0.1:8080/api/overview | head -c 200
```

---

## Configuration

Everything is an environment variable. Nothing is read from a config file.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MONITOR_HOST` | `127.0.0.1` | bind address |
| `MONITOR_PORT` | `8080` | bind port |
| `MONITOR_TOKEN` | *(unset)* | if set, every `/api/*` call needs `Authorization: Bearer <token>` |
| `MONITOR_CORS_ORIGINS` | *(unset)* | comma-separated allowed origins; unset = same-origin only |
| `MONITOR_SERVICES` | `ssh,cron,nginx,docker,systemd-resolved,ufw` | systemd units shown in the Services panel |
| `MONITOR_HIDE_PROCESSES` | `false` | hide the process list entirely |
| `MONITOR_PROCESS_LIMIT` | `50` | rows in the process list |
| `MONITOR_TERMINAL_TOKEN` | *(unset)* | set to enable the web shell; sessions must present this token |
| `MONITOR_HISTORY_POINTS` | `60` | data points kept per chart (client-side) |

### Exposing on a LAN or the internet

```bash
MONITOR_HOST=0.0.0.0 MONITOR_TOKEN="$(openssl rand -hex 24)" mavmon
```

Then open `http://<host>:8080` and paste the token when prompted. For anything
public, front it with a reverse proxy that terminates TLS.

---

## Reverse proxy example (Caddy)

```
monitor.example.com {
    reverse_proxy 127.0.0.1:8080
    basicauth {
        admin JDJhJDE0...   # caddy hash-password
    }
}
```

## Uninstall

```bash
sudo systemctl disable --now mav-monitor
sudo rm /etc/systemd/system/mav-monitor.service
sudo rm -rf /opt/mav-monitor
sudo userdel mavmon
```
