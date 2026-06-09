# Cloudflare — Specification

## Overview
Cloudflare Workers, Domains, DNS records — four components designed for a dedicated Cloudflare orchestration. Uses your own API token and Account ID.

- **Port:** 3742
- **Container:** `wcp-widget-cloudflare`
- **Image:** `docker.io/penrithbeacon/wcp-widget-cloudflare`

## Version
- **Widget:** 1.4.0
- **WCP:** 2.1.0
- **Docker tag:** `1.4.0-wcp2.1.0`

## Controls (HTML Templates)

| Template | Route | Purpose | Default Size |
|----------|-------|---------|--------------|
| widget.html | `/widget/` | Compact overview card | (compact) |
| workers.html | `/widget/workers` | Workers management view | 12×12 |
| domains.html | `/widget/domains` | Domains + DNS records | 12×12 |
| settings.html | `/widget/settings` | API token configuration | 12×12 |
| help.html | `/widget/help` | Setup guide and help | 12×12 |

## Components

| ID | Name | Role | Size |
|----|------|------|------|
| cf-workers | Cloudflare Workers | widget | 12×12 |
| cf-domains | Cloudflare Domains + DNS | widget | 12×12 |
| cf-settings | Cloudflare Settings | widget | 12×12 |
| cf-help | Cloudflare Help | widget | 12×12 |

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/wcp` | Container directory |
| GET | `/widget/wcp` | Widget manifest |
| GET | `/widget/index` | Widget index directory |
| GET | `/widget/` | Compact view |
| GET | `/widget/workers` | Workers management |
| GET | `/widget/domains` | Domains + DNS |
| GET | `/widget/settings` | Settings page |
| GET | `/widget/help` | Help page |
| GET | `/widget/health` | Health check |
| GET | `/widget/icon.svg` | Widget icon |
| GET | `/widget/api/guids` | Component UUIDs |
| GET | `/widget/export.wcp` | WCP export package |
| GET | `/widget/api/config-status` | Check if API token is configured |
| GET | `/widget/api/workers` | List Cloudflare Workers |
| GET | `/widget/api/zones` | List DNS zones/domains |
| GET | `/widget/api/dns/<zone_id>` | List DNS records for a zone |
| POST | `/widget/configure` | Save API token configuration |
| POST | `/widget/publish` | Publish SPA |
| DELETE | `/widget/publish` | Remove published SPA |
| GET | `/` | Serve published SPA |

## Features
- Browse and manage Cloudflare Workers
- Browse domains and DNS records
- DNS record detail view with splitter pane
- API token and Account ID configuration
- Per-orchestration credential storage
- Help/setup guide
- Publish to Web support

## Configuration
- Cloudflare API Token (via `POST /widget/configure`)
- Cloudflare Account ID
- Persisted per orchestration/application context in `/app/data/`

## Data Persistence
- Named volume: `cf-data:/app/data`
- Stores API credentials per context

## Dependencies
- Python: `flask`, `requests`
- External API: Cloudflare API (requires user's API token)
