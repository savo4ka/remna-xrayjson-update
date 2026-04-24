import logging
import os
import sys
import time

from remnawave_client import RemnawaveClient
from templates.base import BaseTemplate
from templates.clash import ClashTemplate
from templates.mihomo import MihomoTemplate
from templates.singbox import SingboxTemplate
from templates.stash import StashTemplate
from templates.xray_json import XrayJsonTemplate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("template-updater")


def env_bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _register_simple(
    templates: list[BaseTemplate],
    client: RemnawaveClient,
    flag: str,
    cls: type[BaseTemplate],
) -> None:
    """Register a pass-through template that needs only UUID + URL."""
    if not env_bool(flag):
        return
    uuid = os.environ.get(f"{flag}_UUID", "")
    url = os.environ.get(f"{flag}_RAW_URL", "")
    if uuid and url:
        templates.append(cls(uuid=uuid, raw_url=url, client=client))
    else:
        log.warning("%s enabled but %s_UUID or %s_RAW_URL is empty", flag, flag, flag)


def build_templates(client: RemnawaveClient) -> list[BaseTemplate]:
    templates: list[BaseTemplate] = []

    # XRAY_JSON has an extra CONVERT_FROM_HAPP flag, so it's registered by hand.
    if env_bool("XRAY_JSON"):
        uuid = os.environ.get("XRAY_JSON_UUID", "")
        url = os.environ.get("XRAY_JSON_RAW_URL", "")
        convert_from_happ = env_bool("CONVERT_FROM_HAPP", "false")
        if uuid and url:
            templates.append(
                XrayJsonTemplate(
                    uuid=uuid,
                    raw_url=url,
                    client=client,
                    convert_from_happ=convert_from_happ,
                )
            )
        else:
            log.warning("XRAY_JSON enabled but XRAY_JSON_UUID or XRAY_JSON_RAW_URL is empty")

    _register_simple(templates, client, "SINGBOX", SingboxTemplate)
    _register_simple(templates, client, "MIHOMO", MihomoTemplate)
    _register_simple(templates, client, "STASH", StashTemplate)
    _register_simple(templates, client, "CLASH", ClashTemplate)

    return templates


def main() -> None:
    api_url = os.environ["REMNAWAVE_API"].rstrip("/")
    token = os.environ["REMNAWAVE_TOKEN"]
    interval = int(os.environ.get("CHECK_INTERVAL", "300"))

    client = RemnawaveClient(api_url=api_url, token=token)
    templates = build_templates(client)

    if not templates:
        log.warning("No templates enabled — nothing to sync")
        return

    log.info(
        "Starting sync templates (interval=%ds, enabled=%s)",
        interval,
        [t.name for t in templates],
    )
    while True:
        for template in templates:
            template.run()
        log.info("Sleeping %d seconds...", interval)
        time.sleep(interval)


if __name__ == "__main__":
    main()
