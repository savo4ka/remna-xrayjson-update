# remna-xrayjson-update

Микросервис для автоматического обновления `XRAY JSON` шаблона в Remna панели при появлении новых данных в GitHub-репозитории [roscomvpn-happ-routing](https://github.com/hydraponique/roscomvpn-happ-routing).

## Как работает

1. При запуске получает текущие настройки подписки из Remna API (`GET /subscription-settings`)
2. Периодически проверяет файл `DEFAULT.DEEPLINK` в GitHub-репозитории
3. Если содержимое изменилось — отправляет обновление в Remna (`PATCH /subscription-settings`)
4. Если изменений нет — ничего не делает

1. Каждые `CHECK_INTERVAL` секунд (по умолчанию 300) скачивает Happ конфигурацию с GitHub
2. Трансформирует её в `XRAY_JSON` формат (DNS, routing rules по порядку из RouteOrder, статичные inbounds/outbounds/policy)
3. Получает текущий шаблон из Remnawave по `TEMPLATE_UUID`
4. Сравнивает JSON-ы — если идентичны, пропускает
5. Если отличаются — отправляет `PATCH` запрос с новой конфигурацией

## Быстрый старт

```bash
mkdir remna-xrayjson-update && cd remna-xrayjson-update
```

### Внешняя панель (HTTPS)

Создайте файл `.env`:

```env
TEMPLATE_UUID=your-template-uuid-here
REMNAWAVE_API=https://your-host
REMNAWAVE_TOKEN=your-remnawave-api-token-here
# GITHUB_RAW_URL=https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/refs/heads/main/HAPP/DEFAULT.JSON
# CHECK_INTERVAL=300
```

Создайте файл `docker-compose.yml`:

```yaml
services:
  routing-updater:
    image: ghcr.io/savo4ka/remna-xrayjson-update:latest
    container_name: remna-xrayjson-updater
    restart: unless-stopped
    env_file:
      - .env
```

### Локальная панель (Docker)

Если RemnaWave панель запущена локально в Docker (образ `remnawave/backend:latest`), контейнер updater нужно подключить к той же сети `remnawave-network` и обращаться к панели по имени контейнера.

Создайте файл `.env`:

```env
TEMPLATE_UUID=your-template-uuid-here
REMNAWAVE_API=https://remnawave:3000
REMNAWAVE_TOKEN=your-remnawave-api-token-here
# GITHUB_RAW_URL=https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/refs/heads/main/HAPP/DEFAULT.JSON
# CHECK_INTERVAL=300
```

> `remnawave` — имя контейнера панели, `3000` — порт по умолчанию. Измените при необходимости.

Создайте файл `docker-compose.yml`:

```yaml
services:
  routing-updater:
    image: ghcr.io/savo4ka/remna-xrayjson-update:latest
    container_name: remna-xrayjson-updater
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

> Сеть `remnawave-network` должна уже существовать (создаётся docker-compose панели RemnaWave).

Запуск:

```bash
docker compose up -d
```

### Сборка из исходников

Если хотите собрать образ самостоятельно:

```bash
git clone https://github.com/savo4ka/remna-xrayjson-update.git
cd remna-xrayjson-update
cp .env.example .env
# отредактируйте .env
docker build -t remna-xrayjson-updater .
docker compose up -d
```

## Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `TEMPLATE_UUID` | да | — | `uuid` шаблона XRAY JSON, который необходимо обновлять |
| `REMNAWAVE_API` | да | — | Базовый URL API Remna (например `https://host/api` или `http://remnawave-backend:3000/api`) |
| `REMNAWAVE_TOKEN` | да | — | Bearer-токен для авторизации в Remna API |
| `GITHUB_RAW_URL` | нет | [DEFAULT.JSON](https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/refs/heads/main/HAPP/DEFAULT.JSON) | URL файла с роутингом на GitHub |
| `CHECK_INTERVAL` | нет | `300` | Интервал проверки обновлений (в секундах) |

## Логи

```bash
docker compose logs -f
```

## Лицензия

MIT