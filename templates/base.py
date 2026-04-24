import base64
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import requests

from remnawave_client import RemnawaveClient

log = logging.getLogger(__name__)


class BaseTemplate(ABC):
    name: str = "base"

    def __init__(self, uuid: str, raw_url: str, client: RemnawaveClient):
        self.uuid = uuid
        self.raw_url = raw_url
        self.client = client

    def fetch_source(self) -> str:
        log.info("[%s] Fetching source: %s", self.name, self.raw_url)
        resp = requests.get(self.raw_url, timeout=30)
        resp.raise_for_status()
        log.info("[%s] Source responded %s", self.name, resp.status_code)
        return resp.text

    @abstractmethod
    def convert(self, source: str) -> Any:
        """Parse raw source text into the value that will be compared and sent."""

    @abstractmethod
    def extract_current(self, rw_data: dict) -> Any:
        """Pull the currently-stored value from a Remnawave GET response."""

    @abstractmethod
    def values_equal(self, new: Any, current: Any) -> bool:
        """Compare new vs current value in a format-appropriate way."""

    @abstractmethod
    def build_patch_body(self, value: Any) -> dict:
        """Build the PATCH body (without uuid) for this template format."""

    def run(self) -> None:
        try:
            source = self.fetch_source()
        except Exception:
            log.exception("[%s] Failed to fetch source", self.name)
            return

        try:
            new_value = self.convert(source)
            log.info("[%s] Conversion successful", self.name)
        except Exception:
            log.exception("[%s] Failed to convert source", self.name)
            return

        try:
            rw_data = self.client.get_template(self.uuid)
        except Exception:
            log.exception("[%s] Failed to fetch Remnawave template", self.name)
            return

        current_value = self.extract_current(rw_data)

        if self.values_equal(new_value, current_value):
            log.info("[%s] Configs are identical — no update needed", self.name)
            return

        log.info("[%s] Configs differ — updating Remnawave template", self.name)
        try:
            self.client.update_template(self.uuid, self.build_patch_body(new_value))
            log.info("[%s] Template updated successfully", self.name)
        except Exception:
            log.exception("[%s] Failed to update Remnawave template", self.name)


class JsonTemplate(BaseTemplate):
    """Template stored in Remnawave as a dict in `templateJson` (XRAY_JSON, SINGBOX)."""

    def extract_current(self, rw_data: dict) -> dict | None:
        response = rw_data.get("response", rw_data)
        return response.get("templateJson")

    def values_equal(self, new: dict, current: dict | None) -> bool:
        return json.dumps(new, sort_keys=True) == json.dumps(current, sort_keys=True)

    def build_patch_body(self, value: dict) -> dict:
        return {"templateJson": value}


class YamlTemplate(BaseTemplate):
    """Template stored in Remnawave as base64-encoded YAML in `encodedTemplateYaml`.

    Used for MIHOMO, STASH, CLASH. `convert` should return the YAML text as a str —
    encoding to base64 and decoding for comparison is handled here.
    """

    def extract_current(self, rw_data: dict) -> str | None:
        response = rw_data.get("response", rw_data)
        encoded = response.get("encodedTemplateYaml")
        if not encoded:
            return None
        return base64.b64decode(encoded).decode("utf-8")

    def values_equal(self, new: str, current: str | None) -> bool:
        return new == current

    def build_patch_body(self, value: str) -> dict:
        encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
        return {"encodedTemplateYaml": encoded}
