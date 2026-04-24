# remna-xrayjson-update

Микросервис для автоматической синхронизации шаблонов подписок в Remnawave с внешними источниками (GitHub raw-файлы и т.п.).

Поддерживает 5 типов шаблонов:

| Тип | Формат | Где хранится в Remnawave |
|---|---|---|
| `XRAY_JSON` | JSON | `templateJson` |
| `SINGBOX` | JSON | `templateJson` |
| `MIHOMO` | YAML | `encodedTemplateYaml` (base64) |
| `STASH` | YAML | `encodedTemplateYaml` (base64) |
| `CLASH` | YAML | `encodedTemplateYaml` (base64) |

Для `XRAY_JSON` дополнительно поддерживается конвертация из формата [Happ](https://github.com/hydraponique/roscomvpn-routing) в нативный Xray JSON (флаг `CONVERT_FROM_HAPP`). Остальные типы работают в режиме pass-through: скачивают файл из `*_RAW_URL` и загружают его в Remnawave как есть.

## Как работает

Каждые `CHECK_INTERVAL` секунд (по умолчанию 300) для каждого включённого типа шаблона:

1. Скачивает конфигурацию с соответствующего `*_RAW_URL`.
2. Для `XRAY_JSON` с `CONVERT_FROM_HAPP=true` — конвертирует Happ JSON в Xray JSON (DNS, routing rules в порядке из `RouteOrder`, статичные inbounds/outbounds/policy). В остальных случаях — парсит «как есть» (JSON для `XRAY_JSON`/`SINGBOX`, YAML-текст без парсинга для `MIHOMO`/`STASH`/`CLASH`).
3. Получает текущий шаблон из Remnawave по `*_UUID`.
4. Сравнивает с новой версией — если идентичны, пропускает.
5. Если отличаются — отправляет `PATCH /api/subscription-templates`. Для JSON-типов в поле `templateJson`, для YAML-типов в `encodedTemplateYaml` (с base64-кодированием).

Ошибка в одном шаблоне (сеть, невалидный источник, отвалившийся API) не ломает остальные — каждый обрабатывается независимо и следующая попытка будет через `CHECK_INTERVAL`.

## Быстрый старт

### Внешняя панель (HTTPS)

Создайте файл `.env`:

```env
REMNAWAVE_API=https://your-host
REMNAWAVE_TOKEN=your-remnawave-api-token-here
CHECK_INTERVAL=300

# XRAY_JSON — конвертация Happ → Xray
XRAY_JSON=true
XRAY_JSON_UUID=your-xray-template-uuid
XRAY_JSON_RAW_URL=https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/refs/heads/main/HAPP/DEFAULT.JSON
CONVERT_FROM_HAPP=true

# Остальные — pass-through (включайте по необходимости)
MIHOMO=false
MIHOMO_UUID=
MIHOMO_RAW_URL=

STASH=false
STASH_UUID=
STASH_RAW_URL=

SINGBOX=false
SINGBOX_UUID=
SINGBOX_RAW_URL=

CLASH=false
CLASH_UUID=
CLASH_RAW_URL=
```

Создайте файл `docker-compose.yml`:

```yaml
services:
  template-updater:
    image: ghcr.io/savo4ka/remna-xrayjson-update:latest
    container_name: template-updater
    restart: unless-stopped
    env_file:
      - .env
```

### Локальная панель (Docker)

Если Remnawave запущен локально в Docker, контейнер updater'а нужно подключить к сети `remnawave-network` и обращаться к панели по имени контейнера.

В `.env` укажите:

```env
REMNAWAVE_API=http://remnawave:3000
```

> `remnawave` — имя контейнера панели, `3000` — порт по умолчанию.

`docker-compose.yml`:

```yaml
services:
  template-updater:
    image: ghcr.io/savo4ka/remna-xrayjson-update:latest
    container_name: template-updater
    restart: unless-stopped
    env_file:
      - .env
    networks:
      - remnawave-network

networks:
  remnawave-network:
    name: remnawave-network
    external: true
```

> Сеть `remnawave-network` должна уже существовать (создаётся docker-compose панели Remnawave).

Запуск:

```bash
docker compose up -d
```

### Сборка из исходников

```bash
git clone https://github.com/savo4ka/remna-xrayjson-update.git
cd remna-xrayjson-update
cp .env.example .env
# отредактируйте .env
docker compose up -d --build
```

## Переменные окружения

### Общие

| Переменная | Обяз. | По умолчанию | Описание |
|---|---|---|---|
| `REMNAWAVE_API` | да | — | Базовый URL Remnawave API (например `https://host` или `http://remnawave:3000`). Для `http://` SSL-проверка отключается и добавляются заголовки `X-Forwarded-Proto: https`, `X-Forwarded-For: 127.0.0.1` |
| `REMNAWAVE_TOKEN` | да | — | Bearer-токен для авторизации |
| `CHECK_INTERVAL` | нет | `300` | Интервал проверки обновлений (секунды) |

### Per-template

Каждый тип шаблона включается флагом `*=true` и требует два параметра — `*_UUID` и `*_RAW_URL`. Если флаг `true`, но параметры пустые — шаблон пропускается с warning в логе.

| Переменная | По умолчанию | Описание |
|---|---|---|
| `XRAY_JSON` | `false` | Включить синхронизацию Xray JSON |
| `XRAY_JSON_UUID` | — | UUID шаблона в Remnawave |
| `XRAY_JSON_RAW_URL` | — | URL исходной конфигурации |
| `CONVERT_FROM_HAPP` | `false` | Просто загрузить JSON как есть. `true` — конвертировать Happ JSON → Xray JSON |
| `SINGBOX` / `SINGBOX_UUID` / `SINGBOX_RAW_URL` | — | Sing-box, pass-through JSON |
| `MIHOMO` / `MIHOMO_UUID` / `MIHOMO_RAW_URL` | — | Mihomo, pass-through YAML |
| `STASH` / `STASH_UUID` / `STASH_RAW_URL` | — | Stash, pass-through YAML |
| `CLASH` / `CLASH_UUID` / `CLASH_RAW_URL` | — | Clash, pass-through YAML |

> **Важно про URL'ы.** Для GitHub-файлов используйте **`raw.githubusercontent.com/.../refs/heads/...`**, а не `github.com/.../blob/...`. Второй вариант возвращает HTML-страницу GitHub, а не исходный файл — программа честно загрузит этот HTML в шаблон, и на каждой итерации (из-за динамических токенов в HTML) будет триггерить бесполезный PATCH.

## Архитектура

Код разбит на модули:

```
main.py                 # Точка входа — читает env, регистрирует шаблоны, запускает цикл
remnawave_client.py     # HTTP-клиент Remnawave API
templates/
├── base.py             # BaseTemplate (ABC) → JsonTemplate / YamlTemplate
├── xray_json.py        # Happ → Xray (c флагом CONVERT_FROM_HAPP)
├── singbox.py          # pass-through JSON
├── mihomo.py           # pass-through YAML
├── stash.py            # pass-through YAML
└── clash.py            # pass-through YAML
```

Чтобы добавить новый тип шаблона — создайте подкласс `JsonTemplate` (если Remnawave хранит его в `templateJson`) или `YamlTemplate` (если в `encodedTemplateYaml`), реализуйте `convert(source: str)`, и зарегистрируйте в `main.build_templates`. Подробности и обоснования архитектурных решений — в [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Логи

```bash
docker compose logs -f
```

Каждое сообщение префиксируется именем шаблона (`[XRAY_JSON]`, `[MIHOMO]` и т.д.) — по нему можно грепать логи отдельных типов.

## Лицензия

MIT

## Поддержать автора

* [Tribute RUB](https://t.me/tribute/app?startapp=dyfn)
* [Tribute EURO](https://t.me/tribute/app?startapp=duPf)
