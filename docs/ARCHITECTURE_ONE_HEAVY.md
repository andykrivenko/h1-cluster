# H1 Architecture — One Heavy Server

## Что такое H1

**H1** — распределённая система автоматизации на базе NATS messaging.  
Состоит из двух типов узлов:

- **Heavy** — сервер с NATS-брокером, Оркестратором и Security Monitor
- **Light** — воркер-нода с Playwright для выполнения задач

## Схема взаимодействия

```
Клиент (ноутбук)
      |
      | SSTP VPN (split-tunnel → 192.168.XX.0/24)
      |
      v
+------------------+
|   Heavy Server   |
|                  |
|  nats-server     |  :4222 (NATS)
|  :8222 (monitor) |
|                  |
|  orchestrator.py |  ← intents.mcp
|  security_monitor|  ← h1.system.events
+------------------+
      |
      | NATS pub/sub
      |
+------------------+   +------------------+
|  Light Worker 1  |   |  Light Worker 2  |
|  worker_playwright|  |  worker_playwright|
|  ← tasks.hhparse |   |  ← tasks.hhparse |
+------------------+   +------------------+
```

## NATS Topics

| Topic | Направление | Описание |
|-------|-------------|----------|
| `intents.mcp` | Client → Orchestrator | Входящие команды/интенты |
| `intents.responses` | Orchestrator → Client | Ответы на интенты |
| `h1.system.events` | Any → SecurityMonitor | Системные события |
| `tasks.hhparse` | Orchestrator → Workers | Задачи для воркеров |
| `tasks.results` | Workers → Orchestrator | Результаты задач |

## Компоненты Heavy

| Файл | Роль | NATS-подписка |
|------|------|---------------|
| `nats-server.exe` | NATS брокер | — |
| `orchestrator.py` | Маршрутизатор команд | `intents.mcp` |
| `security_monitor.py` | Логирование событий | `h1.system.events` |

## Компоненты Light

| Файл | Роль | NATS-подписка |
|------|------|---------------|
| `worker_playwright.py` | Исполнитель задач | `tasks.hhparse` |

## Порты

| Порт | Сервис | Описание |
|------|--------|----------|
| 4222 | NATS | Основной порт клиентов |
| 8222 | NATS HTTP | Мониторинг (`/varz`, `/connz`) |
