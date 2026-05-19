# Linux Codex Usage Monitor: Implementation Plan

## Цель проекта

Сделать Linux-приложение/утилиту, которая показывает данные по лимитам и использованию AI coding-провайдеров, похожие по смыслу на CodexBar, но без попытки повторить macOS menu bar UI.

Главный фокус первой версии: надежно получать данные и отдавать их в удобном виде для Linux-панелей, терминала и автоматизации.

## Что берем из идеи CodexBar

CodexBar уже разделяет проект на две важные части:

- `CodexBarCore` и `CodexBarCLI`: получение, парсинг и нормализация данных.
- macOS UI: AppKit/SwiftUI menu bar, settings windows, widgets, Sparkle updates.

Для Linux нам нужна только первая идея: данные через CLI/API/local sources. macOS UI переносить не нужно.

## Что не делаем в первой версии

- Не портируем `NSStatusBar`, AppKit, SwiftUI, WidgetKit и Sparkle.
- Не пытаемся собрать оригинальное macOS-приложение под Linux.
- Не делаем полноценный визуальный клон CodexBar.
- Не поддерживаем все 40+ провайдеров сразу.
- Не делаем сложную систему логина через браузер/WebKit в первой версии.

## Базовая архитектура

Проект должен состоять из нескольких независимых слоев:

1. Data collector
   Получает сырые данные от провайдеров.

2. Normalizer
   Приводит разные ответы провайдеров к единой модели.

3. Cache
   Хранит последний успешный снимок, чтобы UI не мигал ошибками при временных сбоях.

4. Output adapters
   Отдают данные в форматах, удобных для Linux:
   - JSON для Waybar/Polybar/scripts.
   - text/table для терминала.
   - HTTP endpoint для локального dashboard/tray.

5. UI adapters
   Не обязательны для первой версии, но проект должен быть готов к ним:
   - Waybar module.
   - Polybar script.
   - KDE/Plasma widget.
   - GNOME extension.
   - Tray app через AppIndicator.

## Рекомендуемый путь реализации

Самый прагматичный старт: не переписывать провайдеры с нуля, а использовать существующий `codexbar` CLI как источник данных.

Первая версия нашего проекта должна быть Linux-wrapper поверх:

```bash
codexbar --format json --provider all
```

или локального HTTP-сервера:

```bash
codexbar serve --port 8080
```

Так мы быстро получаем реальные данные, а отдельный Linux-проект отвечает только за:

- запуск CLI;
- обработку JSON;
- кэширование;
- форматирование;
- интеграцию с Linux-панелью.

## Почему не надо сразу переписывать провайдеры

У CodexBar уже есть большая работа по:

- Codex usage;
- Claude usage;
- OpenAI API usage/cost;
- Gemini;
- Copilot;
- OpenRouter;
- локальным cost scans;
- API key based providers;
- CLI based providers.

Если начать с собственного парсинга всех провайдеров, первая версия утонет в поддержке edge cases. Лучше сначала построить стабильную Linux-оболочку вокруг уже существующего источника данных.

## Ограничения Linux-версии

Не все источники CodexBar одинаково работают на Linux.

Хорошо подходят:

- API key based providers.
- CLI based providers.
- OAuth/local config based providers.
- local log scanners.
- `codexbar cost`.
- `codexbar serve`.

Проблемные источники:

- web/browser-cookie режимы;
- WebKit-based dashboard scraping;
- macOS Keychain cache;
- Safari/Chrome cookie import через macOS APIs;
- macOS-specific OAuth storage.

Для первой версии надо явно показывать пользователю, какой источник недоступен на Linux, вместо попыток молча имитировать macOS-поведение.

## Технологический стек

### Вариант A: Python

Подходит для быстрого MVP.

Плюсы:

- Быстро писать.
- Удобно парсить JSON.
- Просто делать CLI.
- Просто интегрировать с Waybar.

Минусы:

- Надо аккуратно упаковывать зависимости.
- Tray-приложение будет менее нативным.

Подходящие библиотеки:

- `typer` или `argparse` для CLI.
- `pydantic` или `dataclasses` для модели данных.
- `httpx` для HTTP режима.
- `rich` для терминального вывода.

### Вариант B: Rust

Лучше для долгоживущего проекта.

Плюсы:

- Один бинарник.
- Хорошая упаковка.
- Хорошо подходит для tray/daemon.
- Можно использовать `tray-icon`/GTK/AppIndicator.

Минусы:

- Дольше старт.
- Больше кода для простого MVP.

Подходящие библиотеки:

- `clap` для CLI.
- `serde`/`serde_json` для JSON.
- `reqwest` для HTTP.
- `tokio` для async.
- `tray-icon` или Tauri для tray-версии.

### Рекомендация

Начать с Python MVP, если цель - быстро получить рабочие данные в Linux-панели.

Переходить на Rust, если после MVP нужен:

- один переносимый бинарник;
- tray app;
- deb/rpm/AppImage;
- долгий background daemon.

## Формат данных проекта

Внутри проекта нужно использовать единую нормализованную модель.

Минимальная модель:

```json
{
  "provider": "codex",
  "label": "Codex",
  "source": "codex-cli",
  "status": "ok",
  "updated_at": "2026-05-19T19:00:00Z",
  "account": "user@example.com",
  "windows": [
    {
      "name": "session",
      "used_percent": 28,
      "remaining_percent": 72,
      "resets_at": "2026-05-19T21:15:00Z",
      "reset_label": "2h 15m"
    },
    {
      "name": "weekly",
      "used_percent": 59,
      "remaining_percent": 41,
      "resets_at": "2026-05-23T09:00:00Z",
      "reset_label": "Fri 09:00"
    }
  ],
  "credits": {
    "remaining": 112.4,
    "unit": "credits"
  },
  "error": null
}
```

Для провайдеров без процентных окон надо разрешить `windows: []` и показывать credits/cost/balance.

## Команды будущей CLI

Проект должен иметь свою команду, например:

```bash
linux-codex-usage status
linux-codex-usage status --provider codex
linux-codex-usage status --format json
linux-codex-usage status --format waybar
linux-codex-usage daemon
linux-codex-usage serve --port 8765
linux-codex-usage config init
linux-codex-usage config check
```

Для Waybar нужен короткий JSON:

```json
{
  "text": "Codex 72% | Claude 88%",
  "tooltip": "Codex session resets at 21:15\nClaude weekly resets Sat 06:00",
  "class": "ok"
}
```

Классы для панели:

- `ok`
- `warning`
- `critical`
- `stale`
- `error`

## Структура проекта для Python MVP

```text
.
├── README.md
├── pyproject.toml
├── src/
│   └── linux_codex_usage/
│       ├── __init__.py
│       ├── cli.py
│       ├── codexbar_client.py
│       ├── models.py
│       ├── normalize.py
│       ├── cache.py
│       ├── formatters/
│       │   ├── __init__.py
│       │   ├── json_formatter.py
│       │   ├── text_formatter.py
│       │   └── waybar_formatter.py
│       └── config.py
├── examples/
│   ├── waybar-module.jsonc
│   └── polybar-script.sh
└── tests/
    ├── test_normalize.py
    ├── test_waybar_formatter.py
    └── fixtures/
        └── codexbar_usage.json
```

## Структура проекта для Rust-версии

```text
.
├── Cargo.toml
├── README.md
├── src/
│   ├── main.rs
│   ├── codexbar_client.rs
│   ├── models.rs
│   ├── normalize.rs
│   ├── cache.rs
│   ├── config.rs
│   └── formatters/
│       ├── mod.rs
│       ├── json.rs
│       ├── text.rs
│       └── waybar.rs
├── examples/
│   ├── waybar-module.jsonc
│   └── polybar-script.sh
└── tests/
    └── fixtures/
        └── codexbar_usage.json
```

## Этап 1: MVP с JSON и Waybar

Цель: получить рабочий вывод для Linux-панели.

Задачи:

1. Создать базовый CLI проекта.
2. Научиться запускать `codexbar --format json --provider all`.
3. Обработать ошибки:
   - `codexbar` не установлен;
   - провайдер не настроен;
   - команда завершилась с non-zero exit code;
   - JSON не распарсился;
   - нет доступных провайдеров.
4. Нормализовать данные в свою модель.
5. Сделать `--format json`.
6. Сделать `--format waybar`.
7. Добавить кэш последнего успешного ответа.
8. Добавить fixtures и тесты нормализации.

Готовность этапа:

```bash
linux-codex-usage status --format waybar
```

возвращает JSON, который можно сразу вставить в Waybar custom module.

## Этап 2: Конфиг и выбор провайдеров

Цель: сделать инструмент удобным для повседневного использования.

Задачи:

1. Добавить конфиг проекта:

```text
~/.config/linux-codex-usage/config.toml
```

2. Поддержать настройки:

```toml
providers = ["codex", "claude", "openai"]
refresh_seconds = 60
warning_threshold = 80
critical_threshold = 95
use_cache_on_error = true
codexbar_path = "codexbar"
```

3. Добавить команду:

```bash
linux-codex-usage config init
linux-codex-usage config check
```

4. Разрешить override через CLI flags:

```bash
linux-codex-usage status --provider codex --provider claude
```

5. Документировать, что provider auth/settings остаются в `~/.codexbar/config.json`.

Готовность этапа:

Пользователь может настроить отображаемые провайдеры без правки Waybar script.

## Этап 3: Локальный daemon/HTTP server

Цель: не запускать `codexbar` слишком часто из панели.

Задачи:

1. Добавить foreground daemon:

```bash
linux-codex-usage daemon
```

2. Добавить HTTP server:

```bash
linux-codex-usage serve --port 8765
```

3. Реализовать endpoints:

```text
GET /health
GET /status
GET /status?provider=codex
GET /waybar
GET /metrics
```

4. Кэшировать данные в памяти.
5. Ограничить bind по умолчанию только на `127.0.0.1`.
6. Сделать systemd user service example.

Готовность этапа:

Waybar читает `http://127.0.0.1:8765/waybar`, а сбор данных идет по расписанию в daemon.

## Этап 4: Улучшенный терминальный вывод

Цель: сделать CLI полезным без панели.

Задачи:

1. Табличный вывод:

```text
Provider  Source       Session  Weekly  Credits  Reset
Codex     codex-cli    72%      41%     112.4    2h 15m
Claude    oauth        88%      63%     -        Sat 06:00
```

2. Цветовые статусы:
   - normal;
   - warning;
   - critical;
   - stale;
   - error.

3. Компактный one-line режим:

```bash
linux-codex-usage status --compact
```

4. Поддержка `NO_COLOR`.

Готовность этапа:

CLI можно использовать как самостоятельную замену быстрому dashboard.

## Этап 5: Tray-приложение

Цель: сделать аналог “иконки рядом с часами”, но по Linux-правилам.

Рекомендуемый стек для tray:

- Rust + `tray-icon`/GTK/AppIndicator;
- или Tauri, если нужна HTML/CSS popup UI;
- или Qt, если нужна максимально привычная Linux desktop-интеграция.

Задачи:

1. Запустить tray icon через AppIndicator/StatusNotifierItem.
2. Показать короткий текст/tooltip с главным провайдером.
3. Добавить menu actions:
   - Refresh;
   - Open config;
   - Open CodexBar config;
   - Quit.
4. Читать данные из локального daemon, а не запускать `codexbar` напрямую.
5. Обработать отсутствие tray support в окружении.

Готовность этапа:

В KDE/XFCE/Cinnamon/Ubuntu AppIndicator появляется иконка с актуальным статусом. Для GNOME надо документировать необходимость AppIndicator extension.

## Этап 6: Нативные провайдеры без зависимости от `codexbar`

Цель: постепенно уменьшить зависимость от внешнего CLI, если это понадобится.

Начинать стоит только после рабочего MVP.

Кандидаты для первого нативного переноса:

1. Local cost scanner для Codex/Claude.
2. API-key providers:
   - OpenAI Admin API;
   - OpenRouter;
   - ElevenLabs;
   - Deepgram;
   - GroqCloud.
3. CLI-based providers:
   - Codex CLI;
   - Claude CLI;
   - Kiro CLI;
   - Augment CLI.

Не стоит начинать с browser-cookie провайдеров, потому что на Linux это быстро превращается в поддержку разных браузеров, keyrings и cookie encryption.

## Ошибки и деградация

Инструмент должен быть устойчивым.

Правила:

- Если свежий fetch упал, но есть cache, показывать stale данные.
- Если cache старше лимита, показывать `stale`/`error`.
- Ошибки по одному провайдеру не должны ломать весь вывод.
- В Waybar режиме вывод всегда должен быть валидным JSON.
- stderr можно использовать для debug logs, но stdout должен оставаться машинно-читаемым.

Пример Waybar error output:

```json
{
  "text": "AI usage unavailable",
  "tooltip": "codexbar command failed: executable not found",
  "class": "error"
}
```

## Безопасность

Правила первой версии:

- Не хранить API keys в новом проекте.
- Не копировать cookies.
- Не логировать secrets.
- Использовать `~/.codexbar/config.json` как источник provider-настроек.
- Свой config держать только для UI/refresh/output настроек.
- HTTP server по умолчанию слушает только `127.0.0.1`.
- Не добавлять CORS/auth/remote bind в MVP.

## Тестирование

Минимальный набор тестов:

1. Нормализация CodexBar JSON fixtures.
2. Waybar formatter.
3. Ошибка `codexbar` не найден.
4. Ошибка invalid JSON.
5. Stale cache fallback.
6. Threshold classes:
   - ok;
   - warning;
   - critical;
   - error.

Для fixtures надо сохранить несколько примеров:

- один провайдер с session/weekly windows;
- несколько провайдеров;
- provider с credits only;
- provider с error;
- пустой список провайдеров.

## Документация

В `README.md` должны быть:

1. Что это не порт macOS UI.
2. Зависимость от `codexbar` CLI в MVP.
3. Установка `codexbar`.
4. Проверка:

```bash
codexbar --format json --pretty
```

5. Установка нашего проекта.
6. Waybar example.
7. Polybar example.
8. systemd user service example.
9. Known limitations on Linux.

## Первый рабочий сценарий

Пользователь устанавливает `codexbar`, настраивает провайдеры через `~/.codexbar/config.json`, затем ставит наш wrapper.

Проверка:

```bash
codexbar --provider codex --format json --pretty
linux-codex-usage status --provider codex --format json
linux-codex-usage status --provider codex --format waybar
```

Waybar config:

```jsonc
"custom/ai-usage": {
  "exec": "linux-codex-usage status --format waybar",
  "return-type": "json",
  "interval": 60,
  "tooltip": true
}
```

## Критерии готовности MVP

MVP готов, когда:

- проект устанавливается локально;
- команда status работает без daemon;
- Waybar получает валидный JSON;
- есть cache fallback;
- есть понятные ошибки;
- есть README с настройкой;
- есть tests для нормализации и форматирования;
- код не хранит secrets и не читает cookies напрямую.

## Рекомендуемый порядок работ

1. Создать каркас проекта.
2. Добавить запуск `codexbar`.
3. Добавить модель данных.
4. Добавить нормализацию JSON.
5. Добавить JSON/text/Waybar formatter.
6. Добавить cache.
7. Добавить конфиг.
8. Добавить тесты.
9. Добавить README и examples.
10. Добавить daemon/serve.
11. После этого решать, нужен ли tray UI.

## Главный технический принцип

Первая версия должна быть не “Linux CodexBar”, а “надежный Linux data layer для AI usage”.

UI можно менять сколько угодно раз. Если слой данных, кэш и форматы вывода сделаны правильно, потом легко добавить Waybar, tray, terminal dashboard или web dashboard без переписывания провайдеров.
