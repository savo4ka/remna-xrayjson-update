from .base import YamlTemplate


class MihomoTemplate(YamlTemplate):
    """Pass-through: fetch Mihomo YAML config and upload it as-is.

    Remnawave stores this in `encodedTemplateYaml` (base64-encoded).
    """

    name = "MIHOMO"

    def convert(self, source: str) -> str:
        return source
