# Security model

MAV Monitor exposes real information about the host it runs on (metrics, the
process list, interface addresses, systemd service states) and, optionally, an
interactive shell. Treat it like an admin tool, not a public web page.

## Defaults are safe

Out of the box:

| Setting | Default | Effect |
| --- | --- | --- |
| `MONITOR_HOST` | `127.0.0.1` | not reachable from the network |
| `MONITOR_TOKEN` | *(unset)* | no auth — acceptable **only** because the bind is loopback |
| `MONITOR_CORS_ORIGINS` | *(unset)* | same-origin only |
| `MONITOR_TERMINAL_TOKEN` | *(unset)* | **web shell is completely disabled** |
| `MONITOR_HIDE_PROCESSES` | `false` | process list visible |

If you never change these, the dashboard is only reachable from the machine
itself (e.g. via an SSH tunnel: `ssh -L 8080:127.0.0.1:8080 host`).

## Exposing it on a network

If you bind to a non-loopback address you **must** set `MONITOR_TOKEN`:

```
MONITOR_HOST=0.0.0.0
MONITOR_TOKEN=$(openssl rand -hex 24)
```

All `/api/*` responses and the dashboard then require
`Authorization: Bearer <token>`. The token is compared with `hmac.compare_digest`.
`/api/config` is intentionally unauthenticated (it only reports which features are
on) so the frontend can prompt for the token.

Better still, keep the bind on loopback and put a real reverse proxy in front
(Caddy, nginx, Tailscale Serve, Cloudflare Tunnel) that adds TLS and its own
authentication.

## The web terminal

`MONITOR_TERMINAL_TOKEN` enables a websocket channel that spawns a login shell
as the **same OS user the monitor runs as**. Every session must send that token
in the `terminal_start` event.

This is a deliberate remote-shell feature. Consequences:

- The shell has whatever privileges the service user has. If that user has
  passwordless `sudo`, the terminal is effectively root.
- Anyone with the terminal token and network reach to the port gets that shell.
- Run the service as an unprivileged, dedicated user if you enable it.
- Prefer leaving it off and using SSH.

The provided `deploy/mav-monitor.service` sets `NoNewPrivileges=true`,
`ProtectSystem=strict` and `ProtectHome=read-only` to limit blast radius.

## What is never collected or sent anywhere

There is no telemetry, no outbound network calls, no database, and nothing is
written to disk. Metric history lives only in the browser tab.

## Reporting

Open a GitHub issue, or for anything sensitive, use the repository's private
vulnerability reporting.
