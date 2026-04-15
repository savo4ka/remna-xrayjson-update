import json
import logging
import os
import sys
import time

import requests
import urllib3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("happ-sync")

TEMPLATE_UUID = os.environ["TEMPLATE_UUID"]
REMNAWAVE_API = os.environ["REMNAWAVE_API"].rstrip("/")
REMNAWAVE_TOKEN = os.environ["REMNAWAVE_TOKEN"]
GITHUB_RAW_URL = os.environ.get(
    "GITHUB_RAW_URL",
    "https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/refs/heads/main/HAPP/DEFAULT.JSON",
)
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "300"))
SSL_VERIFY = REMNAWAVE_API.startswith("https://")

REMNAWAVE_HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {REMNAWAVE_TOKEN}",
}

if not SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    REMNAWAVE_HEADERS["X-Forwarded-Proto"] = "https"
    REMNAWAVE_HEADERS["X-Forwarded-For"] = "127.0.0.1"


def fetch_happ_config(url: str) -> dict:
    log.info("Fetching Happ config from GitHub: %s", url)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    log.info("GitHub responded %s", resp.status_code)
    return resp.json()


def happ_to_xray(happ: dict) -> dict:
    remote_dns_domain = happ["RemoteDNSDomain"]
    domestic_dns_domain = happ["DomesticDNSDomain"]
    remote_dns_ip = happ["RemoteDNSIP"]
    domestic_dns_ip = happ["DomesticDNSIP"]

    direct_sites = happ.get("DirectSites", [])
    direct_ip = happ.get("DirectIp", [])
    proxy_sites = happ.get("ProxySites", [])
    proxy_ip = happ.get("ProxyIp", [])
    block_sites = happ.get("BlockSites", [])
    block_ip = happ.get("BlockIp", [])
    domain_strategy = happ.get("DomainStrategy", "IPIfNonMatch")

    # --- DNS ---
    dns_hosts = happ.get("DnsHosts", {})
    dns_servers = [remote_dns_domain]
    if proxy_sites:
        dns_servers.append({"address": remote_dns_domain, "domains": list(proxy_sites)})
    if direct_sites:
        dns_servers.append({"address": domestic_dns_domain, "domains": list(direct_sites)})

    # --- Routing rules ---
    rules = [{"port": 53, "outboundTag": "dns-out"}]

    route_order = happ.get("RouteOrder", "block-proxy-direct")
    order_parts = route_order.split("-")

    for part in order_parts:
        if part == "block":
            if block_sites:
                rules.append({"domain": list(block_sites), "outboundTag": "block"})
            if block_ip:
                rules.append({"ip": list(block_ip), "outboundTag": "block"})
        elif part == "proxy":
            rules.append({"ip": [domestic_dns_ip], "outboundTag": "direct"})
            rules.append({"ip": [remote_dns_ip], "outboundTag": "proxy"})
            if proxy_sites:
                rules.append({"domain": list(proxy_sites), "outboundTag": "proxy"})
            if proxy_ip:
                rules.append({"ip": list(proxy_ip), "outboundTag": "proxy"})
        elif part == "direct":
            if direct_sites:
                rules.append({"domain": list(direct_sites), "outboundTag": "direct"})
            if direct_ip:
                rules.append({"ip": list(direct_ip), "outboundTag": "direct"})

    return {
        "dns": {
            "hosts": dns_hosts,
            "servers": dns_servers,
            "queryStrategy": "UseIPv4",
        },
        "log": {"loglevel": "warning"},
        "stats": {},
        "policy": {
            "levels": {
                "8": {
                    "connIdle": 300,
                    "handshake": 4,
                    "uplinkOnly": 1,
                    "downlinkOnly": 1,
                }
            },
            "system": {
                "statsOutboundUplink": True,
                "statsOutboundDownlink": True,
            },
        },
        "routing": {
            "rules": rules,
            "domainStrategy": domain_strategy,
        },
        "inbounds": [
            {
                "tag": "socks",
                "port": 10808,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"udp": True, "auth": "noauth", "userLevel": 8},
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "quic", "tls"],
                },
            },
            {
                "tag": "http",
                "port": 10809,
                "listen": "127.0.0.1",
                "protocol": "http",
                "settings": {"userLevel": 8},
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "quic", "tls"],
                },
            },
        ],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
            {
                "tag": "dns-out",
                "protocol": "dns",
                "proxySettings": {"tag": "proxy"},
            },
        ],
    }


def get_remnawave_template(uuid: str) -> dict:
    url = f"{REMNAWAVE_API}/api/subscription-templates/{uuid}"
    log.info("Fetching Remnawave template: GET %s", url)
    resp = requests.get(
        url,
        headers=REMNAWAVE_HEADERS,
        timeout=30,
        verify=SSL_VERIFY,
    )
    resp.raise_for_status()
    log.info("Remnawave GET responded %s", resp.status_code)
    return resp.json()


def update_remnawave_template(uuid: str, name: str, template_json: dict) -> dict:
    url = f"{REMNAWAVE_API}/api/subscription-templates"
    log.info("Updating Remnawave template: PATCH %s", url)
    resp = requests.patch(
        url,
        headers={**REMNAWAVE_HEADERS, "Content-Type": "application/json"},
        json={"uuid": uuid, "name": name, "templateJson": template_json},
        timeout=30,
        verify=SSL_VERIFY,
    )
    resp.raise_for_status()
    log.info("Remnawave PATCH responded %s", resp.status_code)
    return resp.json()


def configs_equal(a: dict, b: dict) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def run_once():
    try:
        happ = fetch_happ_config(GITHUB_RAW_URL)
    except Exception:
        log.exception("Failed to fetch Happ config from GitHub")
        return

    try:
        xray = happ_to_xray(happ)
        log.info("Happ -> XRAY_JSON conversion successful")
    except Exception:
        log.exception("Failed to convert Happ config to XRAY_JSON")
        return

    try:
        rw_data = get_remnawave_template(TEMPLATE_UUID)
    except Exception:
        log.exception("Failed to fetch Remnawave template")
        return

    response = rw_data.get("response", rw_data)
    current_json = response.get("templateJson")
    template_name = response.get("name", "")

    if configs_equal(xray, current_json):
        log.info("Configs are identical — no update needed")
        return

    log.info("Configs differ — updating Remnawave template")
    try:
        update_remnawave_template(TEMPLATE_UUID, template_name, xray)
        log.info("Template updated successfully")
    except Exception:
        log.exception("Failed to update Remnawave template")


def main():
    log.info(
        "Starting happ-sync (interval=%ds, template=%s)", CHECK_INTERVAL, TEMPLATE_UUID
    )
    while True:
        run_once()
        log.info("Sleeping %d seconds...", CHECK_INTERVAL)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
