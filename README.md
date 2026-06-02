# WCP Widget — Cloudflare

A [Widget Context Protocol](https://widgetcontextprotocol.com) widget container
exposing four components for managing your Cloudflare account from any
WCP-compatible dashboard.

## Components

| Component | Default size | What it shows |
|-----------|:------------:|---------------|
| Workers | 12 × 6 | Cloudflare Workers with their domains, Open Site / Open Repo buttons |
| Domains + DNS | 12 × 6 | Domain list (left) + DNS records pane (right, on click) |
| Settings | 12 × 6 | In-widget editor for API token, Account ID, Worker → repo URL map |
| Help | 12 × 6 | Setup guide, FAQ, links |

All four components are sized to fill a full stave by default. The intended
usage pattern is a dedicated "Cloudflare" orchestration with one component
per stave, switched to via the Orchestration Manager when you want to manage
Cloudflare.

## Requirements

- Docker + Docker Compose
- A Cloudflare account with API access

## Run

```bash
docker compose up -d
```

The widget will be available at <http://localhost:3742>.

## Configure

You'll need two pieces of information from Cloudflare:

1. **Account ID** — visible in the right sidebar of any zone or in Workers & Pages
2. **API Token** — create via
   [My Profile → API Tokens](https://dash.cloudflare.com/profile/api-tokens)
   with the following permissions:
   - `Zone:Read`
   - `Zone:DNS:Read`
   - `Account:Workers Scripts:Read`
   - `Account:Worker Routes:Read`

Paste both into the **Settings** component (or into the dashboard's standard
widget configuration form when adding the widget). The Help component walks
through this step-by-step.

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /widget/wcp` | WCP manifest |
| `GET /widget/health` | Health check |
| `GET /widget/icon.svg` | Widget icon |
| `GET /widget/api/guids` | Component UUIDs for Bonjour discovery |
| `GET /widget/export.wcp` | Self-export as `.wcp` package |
| `POST /widget/configure` | Set / update credentials |
| `GET /widget/api/config-status` | Configuration status (token masked) |
| `GET /widget/api/workers` | Cached workers list (30s TTL) |
| `GET /widget/api/zones` | Cached zones list (120s TTL) |
| `GET /widget/api/dns/<zone_id>` | Cached DNS records per zone (30s TTL) |

## Data storage

All configuration lives in `/app/data/config.json` inside the container's
named Docker volume. Credentials never leave your machine except as API
calls direct to Cloudflare.

## Links

- [Penrith Beacon](https://penrithbeacon.com)
- [Widget Context Protocol specification](https://widgetcontextprotocol.com)
- [Cloudflare API documentation](https://developers.cloudflare.com/api/)
