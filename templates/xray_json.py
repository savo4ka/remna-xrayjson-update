import json

from remnawave_client import RemnawaveClient

from .base import JsonTemplate


class XrayJsonTemplate(JsonTemplate):
    name = "XRAY_JSON"

    def __init__(
        self,
        uuid: str,
        raw_url: str,
        client: RemnawaveClient,
        convert_from_happ: bool = False,
    ):
        super().__init__(uuid=uuid, raw_url=raw_url, client=client)
        self.convert_from_happ = convert_from_happ

    def convert(self, source: str) -> dict:
        data = json.loads(source)

        if not self.convert_from_happ:
            return data

        happ = data

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
