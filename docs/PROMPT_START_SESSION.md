Сейчас я работаю над проектом **H1 Platform** — это продакшн‑готовая распределённая система оркестрации агентов и сервисов поверх NATS messaging.

Код хранится в публичном репозитории GitHub: **https://github.com/andykrivenko/h1-cluster** и локально в `C:\h1_network\workspace\h1-repo\`. Все секреты (токены, пароли, IP) хранятся только в `.env` файлах на серверах и никогда не попадают в Git.

---

## Инфраструктура (боевой кластер)

Серверы находятся в закрытом VPN-сегменте `192.168.99.0/24`. Доступ — через SSTP VPN (`H1-Kulakova`, split-tunnel).

**Роли серверов:**

| Сервер | IP | Роль |
|--------|----|------|
| Heavy-1 | 192.168.99.11 | NATS брокер 1, Оркестратор, Security Monitor, MCP Bridge, мастер-данные |
| Heavy-2 | 192.168.99.12 | NATS брокер 2, резервный Security Monitor |
| Light-1 | 192.168.99.13 | Playwright Worker (запущен, работает) |
| Light-2 | 192.168.99.14 | Playwright Worker (не запущен) |

**Архитектура децентрализована, но ролевая:**
- **Heavy** — «мозг»: NATS-брокер, Оркестратор (`intents.mcp`), Security Monitor (`h1.system.events`), MCP Bridge (`intents.hh_expert`)
- **Light** — «руки»: Playwright Worker (`tasks.hhparse`), подключается к NATS на Heavy

**NATS-топики:**
- `intents.mcp` — общие интенты к Оркестратору
- `h1.system.events` — системные события
- `tasks.hhparse` — задачи для воркеров
- `tasks.results` — результаты задач
- `intents.hh_expert` — вызовы инструментов hh_expert через MCP Bridge
- `intents.hh_expert.responses` — ответы MCP Bridge

---

## Репозиторий h1-cluster (единственный источник правды)

```
h1-cluster/
├── h1_server/                      # Heavy server
│   ├── orchestrator.py             # Маршрутизатор интентов (intents.mcp)
│   ├── security_monitor.py         # Логирование событий
│   ├── mcp_hh_expert_bridge.py     # NATS ↔ MCP hh_expert мост
│   ├── nats-server.conf            # Конфиг NATS (шаблон)
│   ├── requirements.txt
│   ├── install_service.bat
│   └── .env.example
├── h1_light_worker/                # Light worker
│   ├── worker_playwright.py        # Playwright исполнитель
│   ├── requirements.txt
│   ├── install_dependencies.bat
│   ├── install_service.bat
│   └── .env.example
├── tests/
│   ├── test_publisher.py           # Базовая NATS-связность
│   ├── test_orchestrator_reply.py  # Request/Reply к Оркестратору
│   ├── test_worker_task.py         # Heavy → Light воркер
│   └── test_hh_expert_bridge.py    # MCP hh_expert мост
└── docs/
    ├── H1_ARCHITECTURE_AND_DEPLOYMENT.md  # Полная архитектура + план переезда
    └── PROMPT_START_SESSION.md            # Этот файл
```

**Реестр агентов:** `h1_server/config/agent_registry.json` — карта того, какой агент на каком хосте живёт и какой NATS-топик слушает.

---

## Концепция данных

- **Код** → GitHub (`h1-cluster`) — единый источник правды
- **Данные** (`DATADIR` для hh_expert) → локально на Heavy-1 (`C:\H1_Server\hh_expert_datadir`)
- **Разработка** → ноутбук (тестовые данные) → GitHub → боевые серверы (боевые данные)
- **Секреты** → только в `.env` на серверах, никогда в коде

---

## Интеграция hh_expert (текущий статус)

```
Cherry Studio (ноутбук)
    │ HTTP/SSE :8333
    ▼
h1_mcp_gateway.py [TODO] (Heavy-1)
    │ NATS intents.hh_expert
    ▼
mcp_hh_expert_bridge.py ✅ (Heavy-1)
    │ stdio
    ▼
hh_expert/server.py (Heavy-1)
```

- ✅ `mcp_hh_expert_bridge.py` написан, тест `test_hh_expert_bridge.py` готов
- 🔲 `h1_mcp_gateway.py` (FastAPI/SSE) — следующий шаг
- 🔲 Подключение Cherry Studio к gateway

---

## Правила работы (clinerules)

1. **Конфигурация только из `.env`:** Любые настройки (`NATS_SERVERS`, `NATS_TOKEN`, пути к файлам, IP-адреса) читаются из `.env`, никогда не захардкожены в коде.

2. **Безопасность:** Никаких реальных IP, токенов, паролей в коде или документации. `.env` исключён через `.gitignore`.

3. **Перед коммитом** запустить тесты:
   ```cmd
   cd c:\h1_network\workspace\h1-repo\tests
   python test_orchestrator_reply.py
   python test_worker_task.py
   python test_hh_expert_bridge.py
   ```

4. **Структура кода:** Каждый компонент читает конфиг из `.env` через `python-dotenv`, логирует через `logging`.

---

## Я использую связку

- **Gemini (ты)** — как Архитектора, который пишет ТЗ и планы.
- **Roo Code в VS Code** — как Исполнителя, который видит весь проект, запускает команды, пишет и редактирует код, коммитит в GitHub.

---

## Твоя роль в этой сессии

1. На основе описания проекта и будущих задач писать **чёткие, поэтапные технические задания (ТЗ) для Roo Code** в формате Markdown.
2. Для каждого этапа:
   - разобрать цель на шаги;
   - указать, какие файлы/модули вероятнее всего придётся менять или создавать;
   - прописать, какие тесты нужно добавить/обновить;
   - в конце дать готовый текст промпта, который я смогу скопировать и вставить Roo.

**Формат ответа для каждого нового этапа:**

1. Краткое описание цели Stage/фичи.
2. Список шагов реализации (по пунктам).
3. Список затрагиваемых файлов и новых файлов.
4. Требования к тестам и проверкам (что именно должен прогнать Roo).
5. Готовый блок **`PROMPT ДЛЯ ROO`**, который я смогу целиком вставить в чат Roo.

---

**Следующие задачи (опиши здесь своими словами, чего хочешь от следующего этапа):**

