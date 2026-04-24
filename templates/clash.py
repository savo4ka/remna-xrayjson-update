from .base import YamlTemplate


class ClashTemplate(YamlTemplate):
    """Pass-through: fetch Clash YAML config and upload it as-is.

    Remnawave stores this in `encodedTemplateYaml` (base64-encoded).
    """

    name = "CLASH"

    def convert(self, source: str) -> str:
        return source
