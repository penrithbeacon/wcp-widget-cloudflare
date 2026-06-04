# WCP Widget: Cloudflare

A [Widget Context Protocol (WCP)](https://widgetcontextprotocol.com) compliant widget
container that brings your Cloudflare account into any WCP-compatible dashboard. View
your Workers and their bound domains, browse all your zones and DNS records, and manage
API credentials — all without leaving the dashboard. Calls the Cloudflare API directly
using your own token; no data passes through any third party.

**Specification:** [widgetcontextprotocol.com](https://widgetcontextprotocol.com)

## Quick Start

```bash
docker run -d \
  --name wcp-widget-cloudflare \
  -p 3742:3742 \
  -v cf-data:/app/data \
  --restart unless-stopped \
  docker.io/penrithbeacon/wcp-widget-cloudflare:latest
```

Then add it to your WCP dashboard at the container's network address.

## Docker Compose

```yaml
services:
  cloudflare:
    image: docker.io/penrithbeacon/wcp-widget-cloudflare:latest
    container_name: wcp-widget-cloudflare
    ports:
      - "3742:3742"
    volumes:
      - cf-data:/app/data
    restart: unless-stopped

volumes:
  cf-data:
```

## Components

The widget exposes four components, each `12 × 6` by default (full stave in Penrith Beacon WCP):

| Component | What it shows |
|-----------|---------------|
| **Workers** | Cloudflare Workers with bound domains. Open Site / Open Repo buttons per worker. |
| **Domains + DNS** | Zones list (left pane) + DNS records (right pane, on click). |
| **Settings** | In-widget editor for API Token, Account ID, and Worker → repo URL mappings. |
| **Help** | Step-by-step setup guide, FAQ, and reference links. |

## Setup

You need a Cloudflare **Account ID** and an **API Token** with these permissions:

| Resource | Permission |
|----------|------------|
| Zone → Zone | Read |
| Zone → DNS | Read |
| Account → Workers Scripts | Read |
| Account → Worker Routes | Read |

Create a token at [My Profile → API Tokens](https://dash.cloudflare.com/profile/api-tokens).
Then open the **Settings** component and paste both values in.

## WCP Request Headers

This widget supports the WCP 2.0.0 request headers:

| Header | Required | Description |
|--------|----------|-------------|
| `Wcp-Instance-Id` | Required | UUID identifying this widget instance |
| `Wcp-Dashboard-Id` | Optional | UUID identifying the requesting dashboard |
| `Wcp-Version` | Optional | Protocol version the dashboard speaks |
| `Wcp-Widget-Id` | Optional | Widget ID from Container Directory selection |
| `Wcp-Orchestration-Id` | Optional | UUID of the active orchestration — shared state key for multi-component coordination |
| `Wcp-Application-Id` | Optional | UUID of the active application window (kiosk only) — combined with orchestration ID for full isolation |

## WCP Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /wcp` | WCP 2.0.0 Container Directory |
| `GET /widget/` | Compact widget card (iframe) |
| `GET /widget/wcp` | WCP 2.0.0 manifest |
| `GET /widget/health` | Health check |
| `GET /widget/icon.svg` | Widget icon (SVG) |
| `GET /widget/workers` | Workers component page |
| `GET /widget/domains` | Domains + DNS component page |
| `GET /widget/settings` | Settings component page |
| `GET /widget/help` | Help component page |
| `POST /widget/configure` | Save credentials and repo mappings |
| `GET /widget/api/config-status` | Configuration status (token masked) |
| `GET /widget/api/workers` | Workers list (30 s cache) |
| `GET /widget/api/zones` | Zones list (120 s cache) |
| `GET /widget/api/dns/<zone_id>` | DNS records for a zone (30 s cache) |
| `GET /widget/api/guids` | Component UUIDs for Bonjour discovery |
| `GET /widget/export.wcp` | Self-export as a `.wcp` package |

## WCP Compatibility

| Property | Value |
|----------|-------|
| WCP Version | 2.0.0 |
| Widget Version | 1.1.0 |
| Render mode | iframe |
| Auth | none (credentials stored server-side) |
| Default card size | 12 × 6 |
| Multi-instance | Yes — per `Wcp-Instance-Id` |

## Technical Details

- **Base image:** `python:3.12-slim`
- **Port:** `3742`
- **Dependencies:** Flask, requests
- **Persistent storage:** Named Docker volume `cf-data` stores per-instance credentials
- **External calls:** Cloudflare API only — no third-party services

## Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `1.1.0-wcp2.0.0` | Widget v1.1.0, WCP 2.0.0 — container block, manifest image source |
| `1.0.1-wcp1.4.0` | Widget v1.0.1, WCP 2.0.0 — server UUID, Container Directory, Wcp-Widget-Id CORS |
| `1.0.0-wcp1.3.1` | Widget v1.0.0, WCP 1.3.1 — initial release |

## Source

- Docker Hub: [penrithbeacon/wcp-widget-cloudflare](https://hub.docker.com/r/penrithbeacon/wcp-widget-cloudflare)
- GitHub: [penrithbeacon/wcp-widget-cloudflare](https://github.com/penrithbeacon/wcp-widget-cloudflare)
- WCP Specification: [widgetcontextprotocol.com](https://widgetcontextprotocol.com)
