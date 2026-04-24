import logging

import requests
import urllib3

log = logging.getLogger(__name__)


class RemnawaveClient:
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url.rstrip("/")
        self.ssl_verify = self.api_url.startswith("https://")
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        if not self.ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.headers["X-Forwarded-Proto"] = "https"
            self.headers["X-Forwarded-For"] = "127.0.0.1"

    def get_template(self, uuid: str) -> dict:
        url = f"{self.api_url}/api/subscription-templates/{uuid}"
        log.info("Fetching Remnawave template: GET %s", url)
        resp = requests.get(
            url,
            headers=self.headers,
            timeout=30,
            verify=self.ssl_verify,
        )
        resp.raise_for_status()
        log.info("Remnawave GET responded %s", resp.status_code)
        return resp.json()

    def update_template(self, uuid: str, body: dict) -> dict:
        """PATCH /api/subscription-templates with {"uuid": ..., **body}.

        ``body`` carries exactly one of ``templateJson`` (for XRAY_JSON / SINGBOX)
        or ``encodedTemplateYaml`` (for MIHOMO / STASH / CLASH). The caller decides
        which — the client stays format-agnostic.
        """
        url = f"{self.api_url}/api/subscription-templates"
        log.info("Updating Remnawave template: PATCH %s", url)
        resp = requests.patch(
            url,
            headers={**self.headers, "Content-Type": "application/json"},
            json={"uuid": uuid, **body},
            timeout=30,
            verify=self.ssl_verify,
        )
        if not resp.ok:
            log.error("Remnawave PATCH failed %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
        log.info("Remnawave PATCH responded %s", resp.status_code)
        return resp.json()
