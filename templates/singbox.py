import json

from .base import JsonTemplate


class SingboxTemplate(JsonTemplate):
    """Pass-through: fetch a sing-box JSON config and upload it as-is.

    Remnawave stores this in `templateJson`.
    """

    name = "SINGBOX"

    def convert(self, source: str) -> dict:
        return json.loads(source)
