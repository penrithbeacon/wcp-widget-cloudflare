"""
WCP Widget: Cloudflare
Four components: Workers, Domains+DNS, Settings, Help — each 12×6, full-stave default.
Port: 3742  |  Cloudflare API: https://api.cloudflare.com/client/v4
Specification: https://widgetcontextprotocol.com
"""

import io
import json
import os
import time
import zipfile
import requests
from flask import Flask, jsonify, render_template, request, Response

app = Flask(__name__)

DATA_DIR = "/app/data"
GLOBAL_CONFIG_FILE = os.path.join(DATA_DIR, "config.json")  # backward compat / fallback
CF_BASE = "https://api.cloudflare.com/client/v4"

# ── CORS ──────────────────────────────────────────────────────────────────────

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = (
        'Content-Type, Wcp-Instance-Id, Wcp-Dashboard-Id, Wcp-Version, Wcp-Widget-Id, '
        'Wcp-Orchestration-Id, Wcp-Application-Id'
    )
    return response

@app.route('/widget/<path:p>', methods=['OPTIONS'])
@app.route('/widget/', methods=['OPTIONS'])
@app.route('/wcp', methods=['OPTIONS'])
def cors_preflight(p=''):
    return Response('', status=204)

# ── Instance ID helpers ───────────────────────────────────────────────────────

# Per WCP 1.5.0: read context headers from request (header first, then query param fallback).
def get_instance_id():
    iid = request.headers.get("Wcp-Instance-Id", "").strip()
    if not iid:
        iid = (request.args.get("wcpInstanceId", "") or "").strip()
    return iid

def get_orchestration_id():
    oid = request.headers.get("Wcp-Orchestration-Id", "").strip()
    if not oid:
        oid = (request.args.get("wcpOrchestrationId", "") or "").strip()
    return oid

def get_application_id():
    aid = request.headers.get("Wcp-Application-Id", "").strip()
    if not aid:
        aid = (request.args.get("wcpApplicationId", "") or "").strip()
    return aid

def get_state_key():
    """WCP 1.5.0 compound state key. See widgetcontextprotocol.com — WCP Request Headers."""
    orch_id = get_orchestration_id()
    app_id  = get_application_id()
    if orch_id and app_id: return f"{orch_id}:{app_id}"
    if orch_id:            return orch_id
    return "global"

def _safe_iid(iid):
    # Defence against path traversal — only allow uuid-ish chars
    return "".join(c for c in iid if c.isalnum() or c == "-")[:64]

def config_file_for(iid):
    iid = _safe_iid(iid)
    if not iid:
        return GLOBAL_CONFIG_FILE
    return os.path.join(DATA_DIR, f"config-{iid}.json")

# ── Config helpers ────────────────────────────────────────────────────────────

def read_config(iid=None):
    """Per-instance config, falling back to global on first use."""
    if iid is None:
        iid = get_instance_id()
    path = config_file_for(iid)
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        # First-time fallback to legacy global config so existing single-tenant
        # deployments continue to work without reconfiguration
        if path != GLOBAL_CONFIG_FILE:
            try:
                with open(GLOBAL_CONFIG_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

def write_config(data, iid=None):
    if iid is None:
        iid = get_instance_id()
    os.makedirs(DATA_DIR, exist_ok=True)
    path = config_file_for(iid)
    current = {}
    try:
        with open(path) as f:
            current = json.load(f)
    except Exception:
        pass
    current.update({k: v for k, v in data.items() if v is not None})
    with open(path, "w") as f:
        json.dump(current, f, indent=2)
    return current

def mask_token(token):
    if not token or len(token) < 4:
        return ""
    return "****" + token[-4:]

# ── Cache (in-memory, per-process, keyed by instance) ────────────────────────

# { iid: { "workers": {data,time}, "zones": {data,time}, "dns": {zone_id: {...}} } }
_cache = {}
WORKERS_TTL = 30
ZONES_TTL = 120
DNS_TTL = 30

def _cache_for(iid):
    if iid not in _cache:
        _cache[iid] = {"workers": {"data": None, "time": 0},
                       "zones":   {"data": None, "time": 0},
                       "dns":     {}}
    return _cache[iid]

def clear_cache(iid=None):
    if iid is None:
        _cache.clear()
    else:
        _cache.pop(iid, None)

# ── Cloudflare API helper ─────────────────────────────────────────────────────

def cf_fetch(path, token):
    r = requests.get(f"{CF_BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    return r.json()

# ── WCP Manifest ─────────────────────────────────────────────────────────────

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
  <path fill="#f0883e" d="M12.5 8.5c0-.3-.05-.6-.14-.87.32-.41.52-.92.52-1.49 0-1.4-1.13-2.53-2.53-2.53-.27 0-.53.04-.78.12C9.06 2.5 7.83 1.5 6.37 1.5 4.6 1.5 3.16 2.85 3.02 4.59 1.86 4.92 1 5.98 1 7.25 1 8.77 2.23 10 3.75 10h7.86c.69 0 1.31-.28 1.76-.74-.55-.18-.94-.55-.87-.76zM3.75 9C2.78 9 2 8.22 2 7.25S2.78 5.5 3.75 5.5h.5l.05-.5C4.4 3.6 5.52 2.5 6.87 2.5c1.18 0 2.21.83 2.46 1.98l.16.75.71-.32c.18-.08.38-.13.59-.13.86 0 1.55.69 1.55 1.55 0 .3-.09.59-.24.83l-.3.45.35.4c.07.08.11.18.11.29 0 .22-.18.4-.4.4H3.75z"/>
</svg>"""

WCP_MANIFEST = {
    "wcp": "2.1.0",
    "uuid": "e7cf3182-b4d5-4389-8019-02181d897ef3",
    "name": "Cloudflare",
    "version": "1.4.0",
    "description": (
        "Cloudflare Workers, Domains, DNS records — four components designed for "
        "a dedicated Cloudflare orchestration. Use your own API token and Account ID."
    ),
    "icon": "/widget/icon.svg",
    "health": "/widget/health",
    "container": {
        "image":            "docker.io/penrithbeacon/wcp-widget-cloudflare",
        "source":           {"type": "registry"},
        "tag":              "1.4.0-wcp2.1.0",
        "port":             3742,
        "volumes":          [{"name": "cf-data", "mountPath": "/app/data"}],
        "defaultLifecycle": "always",
    },
    "configuration": {
        "submitEndpoint": "/widget/configure",
        "fields": [
            {
                "id": "apiToken",
                "type": "password",
                "sensitive": True,
                "label": "Cloudflare API Token",
                "placeholder": "Bearer token with Zone:Read, Workers:Read, DNS:Read scopes",
            },
            {
                "id": "accountId",
                "type": "text",
                "sensitive": True,
                "label": "Cloudflare Account ID",
                "placeholder": "32-character hex string from your dashboard sidebar",
            },
        ],
    },
    "pages": [
        {"id": "workers",  "path": "/widget/workers",  "title": "Cloudflare Workers"},
        {"id": "domains",  "path": "/widget/domains",  "title": "Cloudflare Domains + DNS"},
        {"id": "settings", "path": "/widget/settings", "title": "Cloudflare Settings"},
        {"id": "help",     "path": "/widget/help",     "title": "Cloudflare Help"},
    ],
    "components": [
        {
            "id": "cf-workers",
            "uuid": "40c2ae0f-f61c-493f-b649-d9b792450325",
            "name": "Cloudflare Workers",
            "role": "widget",
            "path": "/widget/workers",
            "icon": "/widget/icon.svg",
            "renderMode": "iframe",
            "defaultSize": {"w": 12, "h": 12},
        },
        {
            "id": "cf-domains",
            "uuid": "98ea302f-5005-4dd2-9fd8-0030cbbfd92b",
            "name": "Cloudflare Domains + DNS",
            "role": "widget",
            "path": "/widget/domains",
            "icon": "/widget/icon.svg",
            "renderMode": "iframe",
            "defaultSize": {"w": 12, "h": 12},
        },
        {
            "id": "cf-settings",
            "uuid": "95883ab1-3056-4098-b2b6-6cf3c990de8f",
            "name": "Cloudflare Settings",
            "role": "widget",
            "path": "/widget/settings",
            "icon": "/widget/icon.svg",
            "renderMode": "iframe",
            "defaultSize": {"w": 12, "h": 12},
        },
        {
            "id": "cf-help",
            "uuid": "47a91f67-8642-484d-898b-f1a8023043a3",
            "name": "Cloudflare Help",
            "role": "widget",
            "path": "/widget/help",
            "icon": "/widget/icon.svg",
            "renderMode": "iframe",
            "defaultSize": {"w": 12, "h": 12},
        },
    ],
}

PUBLISHED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'published', 'index.html')

WIDGET_JSONLD = json.dumps({
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": WCP_MANIFEST["name"],
    "softwareVersion": WCP_MANIFEST["version"],
    "description": WCP_MANIFEST["description"],
    "identifier": WCP_MANIFEST["uuid"],
    "applicationCategory": "WCP Widget",
    "operatingSystem": "Web",
    "isBasedOn": {
        "@type": "WebSite",
        "name": "Widget Context Protocol",
        "url": "https://widgetcontextprotocol.com",
    },
    "additionalProperty": [
        {"@type": "PropertyValue", "name": "wcpVersion",      "value": WCP_MANIFEST["wcp"]},
        {"@type": "PropertyValue", "name": "containerImage",  "value": WCP_MANIFEST["container"]["image"]},
        {"@type": "PropertyValue", "name": "containerTag",    "value": WCP_MANIFEST["container"]["tag"]},
        {"@type": "PropertyValue", "name": "containerPort",   "value": str(WCP_MANIFEST["container"]["port"])},
    ],
}, indent=2)

# ── WCP boilerplate endpoints ─────────────────────────────────────────────────

@app.route("/wcp")
def container_directory():
    return jsonify({
        "type":    "directory",
        "wcp":     "2.1.0",
        "widgets": [{
            "id":          "cloudflare",
            "uuid":        WCP_MANIFEST["uuid"],
            "name":        WCP_MANIFEST["name"],
            "description": WCP_MANIFEST["description"],
            "icon":        WCP_MANIFEST["icon"],
            "manifest":    "/widget/wcp",
        }]
    })

@app.route('/')
def published_spa():
    if os.path.exists(PUBLISHED_PATH):
        with open(PUBLISHED_PATH, 'r', encoding='utf-8') as f:
            return Response(f.read(), mimetype='text/html')
    return Response('Not Found', status=404, mimetype='text/plain')

@app.route('/widget/publish', methods=['POST'])
def publish():
    html = request.get_data(as_text=True)
    if not html:
        return jsonify({'success': False, 'error': 'Empty body'}), 400
    try:
        os.makedirs(os.path.dirname(PUBLISHED_PATH), exist_ok=True)
        with open(PUBLISHED_PATH, 'w', encoding='utf-8') as f:
            f.write(html)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/widget/publish', methods=['DELETE'])
def unpublish():
    try:
        if os.path.exists(PUBLISHED_PATH):
            os.remove(PUBLISHED_PATH)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/widget/")
@app.route("/widget/index.html")
def widget_root():
    return render_template("widget.html", manifest=WCP_MANIFEST, jsonld=WIDGET_JSONLD,
        wcp_instance_id=get_instance_id(),
        wcp_orchestration_id=get_orchestration_id(), wcp_application_id=get_application_id())

@app.route("/widget/wcp")
def widget_wcp():
    manifest = dict(WCP_MANIFEST)
    manifest['web'] = {'published': os.path.exists(PUBLISHED_PATH)}
    return jsonify(manifest)

@app.route("/widget/index")
def widget_index():
    return render_template("index-page.html", manifest=WCP_MANIFEST, jsonld=WIDGET_JSONLD,
        wcp_instance_id=get_instance_id(),
        wcp_orchestration_id=get_orchestration_id(), wcp_application_id=get_application_id())

@app.route("/widget/health")
def widget_health():
    return jsonify({"status": "ok", "name": WCP_MANIFEST["name"],
                    "container": os.environ.get("CONTAINER_NAME", "unknown")})

@app.route("/widget/icon.svg")
def widget_icon():
    return Response(ICON_SVG, mimetype="image/svg+xml")

@app.route("/widget/api/guids")
def api_guids():
    return jsonify({
        "uuid": WCP_MANIFEST["uuid"],
        "components": [
            {"id": c["id"], "uuid": c["uuid"], "name": c["name"]}
            for c in WCP_MANIFEST.get("components", [])
    ]})

@app.route("/widget/export.wcp")
def export_wcp():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(WCP_MANIFEST, indent=2))
        z.writestr("icon.svg", ICON_SVG)
        z.writestr("DOCKER.md", f"""# {WCP_MANIFEST['name']} — WCP Container

## Pull
```
docker pull penrithbeacon/wcp-widget-cloudflare
```

## Run
```
docker compose up -d
```

Port: 3742 | Spec: https://widgetcontextprotocol.com
""")
    buf.seek(0)
    resp = Response(buf.read(), mimetype="application/zip")
    resp.headers["Content-Disposition"] = 'attachment; filename="cloudflare.wcp"'
    return resp

# ── Component pages ───────────────────────────────────────────────────────────

@app.route("/widget/workers")
def page_workers():
    return render_template("workers.html", manifest=WCP_MANIFEST, jsonld=WIDGET_JSONLD,
        wcp_instance_id=get_instance_id(),
        wcp_orchestration_id=get_orchestration_id(), wcp_application_id=get_application_id())

@app.route("/widget/domains")
def page_domains():
    return render_template("domains.html", manifest=WCP_MANIFEST, jsonld=WIDGET_JSONLD,
        wcp_instance_id=get_instance_id(),
        wcp_orchestration_id=get_orchestration_id(), wcp_application_id=get_application_id())

@app.route("/widget/settings")
def page_settings():
    return render_template("settings.html", manifest=WCP_MANIFEST, jsonld=WIDGET_JSONLD,
        wcp_instance_id=get_instance_id(),
        wcp_orchestration_id=get_orchestration_id(), wcp_application_id=get_application_id())

@app.route("/widget/help")
def page_help():
    return render_template("help.html", manifest=WCP_MANIFEST, jsonld=WIDGET_JSONLD,
        wcp_instance_id=get_instance_id(),
        wcp_orchestration_id=get_orchestration_id(), wcp_application_id=get_application_id())

# ── Configuration ─────────────────────────────────────────────────────────────

@app.route("/widget/configure", methods=["POST"])
def widget_configure():
    try:
        iid = get_instance_id()
        data = request.get_json(force=True) or {}
        cfg = write_config({
            "apiToken":    (data.get("apiToken")    or "").strip() or None,
            "accountId":   (data.get("accountId")   or "").strip() or None,
            "workerRepos": data.get("workerRepos")  if isinstance(data.get("workerRepos"), dict) else None,
        }, iid=iid)
        clear_cache(iid)
        return jsonify({"success": True, "configured": bool(cfg.get("apiToken") and cfg.get("accountId"))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/widget/api/config-status")
def config_status():
    cfg = read_config()
    return jsonify({
        "configured":       bool(cfg.get("apiToken") and cfg.get("accountId")),
        "apiTokenMasked":   mask_token(cfg.get("apiToken", "")),
        "accountId":        cfg.get("accountId", ""),
        "workerRepos":      cfg.get("workerRepos", {}),
    })

# ── Cloudflare data endpoints ─────────────────────────────────────────────────

def _not_configured_response():
    return jsonify({
        "success": False,
        "error": "Cloudflare not configured. Open the Settings component to add your API token and Account ID.",
        "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

@app.route("/widget/api/workers")
def api_workers():
    iid = get_instance_id()
    cache = _cache_for(iid)
    now = time.time()
    if cache["workers"]["data"] and now - cache["workers"]["time"] < WORKERS_TTL:
        return jsonify(cache["workers"]["data"])

    cfg = read_config(iid)
    token = cfg.get("apiToken")
    account_id = cfg.get("accountId")
    worker_repos = cfg.get("workerRepos", {})

    if not token or not account_id:
        return _not_configured_response()

    try:
        services = cf_fetch(f"/accounts/{account_id}/workers/services", token)
        domains  = cf_fetch(f"/accounts/{account_id}/workers/domains", token)

        if not services.get("success"):
            return jsonify({"success": False, "error": (services.get("errors") or [{}])[0].get("message", "Cloudflare API error")})

        # Build domain map: service_id → [{hostname, zone}]
        domain_map = {}
        for d in (domains.get("result") or []):
            domain_map.setdefault(d["service"], []).append({"hostname": d["hostname"], "zone": d["zone_name"]})

        workers = []
        for s in (services.get("result") or []):
            env = s.get("default_environment") or {}
            script = env.get("script") or {}
            doms = domain_map.get(s["id"], [])
            primary = next((d for d in doms if not d["hostname"].startswith("www.")), doms[0] if doms else None)
            workers.append({
                "id":         s["id"],
                "modifiedOn": script.get("modified_on") or env.get("modified_on"),
                "domains":    doms,
                "siteUrl":    f"https://{primary['hostname']}" if primary else None,
                "repoUrl":    worker_repos.get(s["id"]),
            })

        result = {"success": True, "data": {"workers": workers}, "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        cache["workers"]["data"] = result
        cache["workers"]["time"] = now
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/widget/api/zones")
def api_zones():
    iid = get_instance_id()
    cache = _cache_for(iid)
    now = time.time()
    if cache["zones"]["data"] and now - cache["zones"]["time"] < ZONES_TTL:
        return jsonify(cache["zones"]["data"])

    cfg = read_config(iid)
    token = cfg.get("apiToken")
    account_id = cfg.get("accountId")

    if not token:
        return _not_configured_response()

    try:
        zones = cf_fetch("/zones?per_page=50", token)
        registrar = cf_fetch(f"/accounts/{account_id}/registrar/domains?per_page=50", token) if account_id else {"result": []}

        if not zones.get("success"):
            return jsonify({"success": False, "error": (zones.get("errors") or [{}])[0].get("message", "Cloudflare API error")})

        cf_registered = {r["name"].lower() for r in (registrar.get("result") or [])}
        out = []
        for z in sorted(zones.get("result") or [], key=lambda x: x["name"]):
            out.append({
                "id":                     z["id"],
                "name":                   z["name"],
                "status":                 z.get("status"),
                "modifiedOn":             z.get("modified_on"),
                "registeredAtCloudflare": z["name"].lower() in cf_registered,
                "originalRegistrar":      z.get("original_registrar"),
            })

        result = {"success": True, "data": {"zones": out}, "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        cache["zones"]["data"] = result
        cache["zones"]["time"] = now
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/widget/api/dns/<zone_id>")
def api_dns(zone_id):
    iid = get_instance_id()
    cache = _cache_for(iid)
    now = time.time()
    dns = cache["dns"]
    if zone_id in dns and now - dns[zone_id]["time"] < DNS_TTL:
        return jsonify(dns[zone_id]["data"])

    cfg = read_config(iid)
    token = cfg.get("apiToken")
    if not token:
        return _not_configured_response()

    try:
        resp = cf_fetch(f"/zones/{zone_id}/dns_records?per_page=100", token)
        if not resp.get("success"):
            return jsonify({"success": False, "error": (resp.get("errors") or [{}])[0].get("message", "Cloudflare API error")})

        records = []
        for r in sorted(resp.get("result") or [], key=lambda x: (x["type"], x["name"])):
            records.append({
                "type":     r["type"],
                "name":     r["name"],
                "content":  r["content"],
                "ttl":      "Auto" if r["ttl"] == 1 else str(r["ttl"]),
                "proxied":  r.get("proxied", False),
                "priority": r.get("priority"),
            })

        result = {"success": True, "data": {"records": records, "zoneId": zone_id}, "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        dns[zone_id] = {"data": result, "time": now}
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("/app/data", exist_ok=True)
    app.run(host="0.0.0.0", port=3742, debug=False)
