# WCP Widget — Cloudflare

A [Widget Context Protocol (WCP)](https://widgetcontextprotocol.com) widget container
that brings your Cloudflare account into any WCP-compatible dashboard. Manage your
Workers, browse Domains and DNS records, and update credentials — all without leaving
your dashboard.

**Specification:** [widgetcontextprotocol.com](https://widgetcontextprotocol.com)  
**Part of the** [Penrith Beacon WCP](https://penrithbeacon.com) widget suite.

> **WCP 1.5.0 certified.** This widget implements the full
> [Widget Context Protocol 1.5.0](https://widgetcontextprotocol.com) specification,
> including server UUID, Container Directory (`GET /wcp`), all six `Wcp-*` request headers, and context-scoped runtime state isolation (`Wcp-Orchestration-Id`, `Wcp-Application-Id`).

---

## Components

The widget exposes **four components**, each sized at `12 × 6` by default — a full stave
in standard Penrith Beacon WCP layout. The intended usage is a dedicated **Cloudflare
orchestration** with one component per stave, switched to via the Orchestration Manager
whenever you need to manage Cloudflare.

| Component | Default size | What it shows |
|-----------|:------------:|---------------|
| **Workers** | 12 × 6 | All Cloudflare Workers with their bound domains. Open Site and Open Repo buttons per worker. |
| **Domains + DNS** | 12 × 6 | Zones list in a left pane; click any domain to load its DNS records in the right pane. |
| **Settings** | 12 × 6 | In-widget editor for your API Token, Account ID, and Worker → repository URL mappings. |
| **Help** | 12 × 6 | Step-by-step setup guide, FAQ, and reference links. |

---

## Requirements

- Docker and Docker Compose
- A Cloudflare account with API access

---

## Quick Start

```bash
docker run -d \
  --name wcp-widget-cloudflare \
  -p 3742:3742 \
  -v cf-data:/app/data \
  --restart unless-stopped \
  penrithbeacon/wcp-widget-cloudflare:latest
```

Then add it to your WCP dashboard at `http://localhost:3742`.

---

## Docker Compose

Clone this repository and run:

```bash
docker compose up -d
```

Or use this compose snippet directly:

```yaml
services:
  cloudflare:
    image: penrithbeacon/wcp-widget-cloudflare:latest
    container_name: wcp-widget-cloudflare
    ports:
      - "3742:3742"
    volumes:
      - cf-data:/app/data
    restart: unless-stopped

volumes:
  cf-data:
```

---

## Setup Guide

You need two pieces of information from Cloudflare before the widget can show live data.

### 1. Find your Account ID

1. Log in to the [Cloudflare dashboard](https://dash.cloudflare.com)
2. Open any domain (or go to **Workers & Pages**)
3. Look at the right-hand sidebar — your **Account ID** is a 32-character hex string
4. Click the copy icon next to it

### 2. Create an API Token

1. Go to [My Profile → API Tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Click **Create Token**
3. Choose the **Custom token** template
4. Add the following permissions:

   | Resource | Permission |
   |----------|------------|
   | Zone → Zone | Read |
   | Zone → DNS | Read |
   | Account → Workers Scripts | Read |
   | Account → Worker Routes | Read |

5. Set **Account Resources** to your account and **Zone Resources** to All zones
6. Click **Continue to summary** → **Create Token**
7. Copy the token immediately — Cloudflare only shows it once

### 3. Configure the widget

Open the **Settings** component and paste both values in, then click **Save Settings**.
The Workers and Domains components will immediately start showing your live data.

> **Tip.** If you are adding the widget to a stave for the first time, the dashboard's
> standard widget configuration form can accept the API Token and Account ID directly
> on add. The Settings component is there for editing them later or for adding
> Worker → repo URL mappings.

---

## WCP Request Headers

This widget supports the WCP 1.3.1 instance headers for multi-instance deployment:

| Header | Required | Description |
|--------|----------|-------------|
| `Wcp-Instance-Id` | Required | UUID identifying this widget instance |
| `Wcp-Dashboard-Id` | Optional | UUID identifying the requesting dashboard |
| `Wcp-Version` | Optional | Protocol version the dashboard speaks |

Each instance stores its credentials separately inside the Docker volume
(`config-<instance-id>.json`), so a single container can serve multiple dashboards
with independent Cloudflare accounts.

---

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /widget/` | GET | Compact widget card (iframe) |
| `GET /widget/wcp` | GET | WCP 1.3.1 manifest |
| `GET /widget/health` | GET | `{"status":"ok","name":"Cloudflare"}` |
| `GET /widget/icon.svg` | GET | Widget icon (SVG) |
| `GET /widget/workers` | GET | Workers component page |
| `GET /widget/domains` | GET | Domains + DNS component page |
| `GET /widget/settings` | GET | Settings component page |
| `GET /widget/help` | GET | Help component page |
| `POST /widget/configure` | POST | Save API token, Account ID, and repo mappings |
| `GET /widget/api/config-status` | GET | Configuration status (token masked) |
| `GET /widget/api/workers` | GET | Workers list (30 s cache) |
| `GET /widget/api/zones` | GET | Zones list (120 s cache) |
| `GET /widget/api/dns/<zone_id>` | GET | DNS records for a zone (30 s cache) |
| `GET /widget/api/guids` | GET | Component UUIDs for Bonjour discovery |
| `GET /widget/export.wcp` | GET | Self-export as a `.wcp` package |

---

## Data Storage

All credentials and Worker → repo mappings are stored in `/app/data/config.json` (or
`/app/data/config-<instance-id>.json` for multi-instance deployments) inside the
container's named Docker volume. **Credentials never leave your machine** — they are
used only in direct API calls to Cloudflare.

| Data | Cache TTL |
|------|-----------|
| Workers | 30 seconds |
| Zones | 120 seconds |
| DNS records | 30 seconds |

Click the Refresh button on any component to bypass the cache immediately.

---

## FAQ

**Where is the data stored?**  
Inside the named Docker volume at `/app/data/`. Nothing is sent to any third party
other than the Cloudflare API.

**Can I run multiple instances pointing at different Cloudflare accounts?**  
Yes. Each WCP dashboard instance sends a `Wcp-Instance-Id` header; the widget stores
separate credentials per instance in the same volume.

**What if my API token leaks?**  
Revoke it immediately from [My Profile → API Tokens](https://dash.cloudflare.com/profile/api-tokens),
generate a new one, and paste it into the Settings component.

**Can I add more Cloudflare components beyond Workers and Domains?**  
Open an issue in this repository. The widget currently focuses on Workers + Domains + DNS —
the three most commonly glanced at — but more components can be added as needs emerge.

---

## WCP Compatibility

| Property | Value |
|----------|-------|
| WCP Version | 1.3.1 |
| Widget Version | 1.0.0 |
| Render mode | iframe |
| Auth | none (credentials stored server-side) |
| Default card size | 12 × 6 |
| Multi-instance | Yes — per `Wcp-Instance-Id` |

---

## Technical Details

- **Base image:** `python:3.12-slim`
- **Port:** `3742`
- **Framework:** Flask
- **External calls:** Cloudflare API only (`api.cloudflare.com`)
- **Persistent storage:** Named Docker volume `cf-data`

---

## Links

- [Penrith Beacon](https://penrithbeacon.com)
- [Widget Context Protocol specification](https://widgetcontextprotocol.com)
- [Cloudflare API documentation](https://developers.cloudflare.com/api/)
- [Docker Hub — penrithbeacon/wcp-widget-cloudflare](https://hub.docker.com/r/penrithbeacon/wcp-widget-cloudflare)
