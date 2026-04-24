from .base import YamlTemplate


class StashTemplate(YamlTemplate):
    """Pass-through: fetch Stash YAML config and upload it as-is.

    Remnawave stores this in `encodedTemplateYaml` (base64-encoded).
    """

    name = "STASH"

    def convert(self, source: str) -> str:
        return source
