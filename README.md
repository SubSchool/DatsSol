# DatsSol

Операционный каркас под DatsSol с архитектурой `Python + Vue + Postgres`.

Что уже собрано:

- backend на FastAPI с DatsSol-provider abstraction, пайплайном `observe -> analyze -> decide -> execute -> submit` и логами в Postgres;
- frontend на Vue 3 + PrimeVue + PixiJS с интерактивной картой и вкладкой подробных логов;
- mock sandbox `datssol-mock` для локальной отладки без живого сервера;
- live adapter под актуальные эндпоинты `GET /api/arena`, `POST /api/command`, `GET /api/logs`;
- исследовательские заметки по стратегии, визуализации и ассетам именно под DatsSol.

## Структура

```text
backend/                  FastAPI runtime, планировщик хода, провайдеры, Postgres
docs/contracts/           сохранённый OpenAPI DatsSol и исторические контракты
docs/research/            стратегические заметки, стек и визуальные материалы
frontend/                 Vue 3, PrimeVue, PixiJS, вкладки Visualization / Logs
docker-compose.yml        postgres + backend + frontend
```

## Быстрый старт

1. Скопировать `.env.example` в `.env`.
2. При необходимости прописать `DATSSOL_AUTH_TOKEN` в `.env`.
3. Поднять Postgres:

```bash
docker compose up postgres -d
```

4. Запустить backend:

```bash
make install-backend
make dev-backend
```

5. Запустить frontend:

```bash
make install-frontend
make dev-frontend
```

## Backend pipeline

Каждый ход разбит на изолированные шаги с отдельным логированием:

1. `observe` получает состояние арены и игровые логи.
2. `analyze` строит связную сеть от ЦУ, оценивает frontier, угрозы, лимиты и forecast.
3. `decide` формирует стратегические intents.
4. `execute` собирает конкретные `path`, выбор апгрейда и перенос ЦУ.
5. `submit` отправляет ход или прогоняет его в `dry-run` или `mock`.

Это позволяет отдельно оптимизировать эвристики, маршрутизацию и политику сабмита.

## Базовая стратегия

- Дефолт: `Economy / Rolling Carpet` — строить компактную двухполосную сеть с резервными связями, а не длинную одинарную змейку.
- Ранняя игра: сначала держать минимум две безопасные adjacent-опоры возле ЦУ, только потом уходить глубже во frontier.
- Основной порядок хода: `repair core -> finish existing builds -> extend backbone -> beaver window -> short raid`.
- Дефолтный апгрейд: `repair_power`, так как он ускоряет и стройку, и ремонт; дальше обычно `signal_range` или `settlement_limit`.
- Перенос ЦУ планируется заранее и не только на low HP, а по оставшемуся сроку жизни клетки и числу безопасных anchor-кандидатов.
- Клетки с высоким уже накопленным terraform-progress не используются как базовые anchor-узлы, потому что они дают короткую жизнь новой плантации и ломают темп сети.
- Уничтожение бобров: только когда логово душит основной фронтир, можно обеспечить burst выше регена или есть шанс забрать secure last-hit.
- Диверсии: оппортунистически, при локальном численном перевесе, в contested-зоне или по хрупким relay/bridge-узлам врага.

## Документы

- [OpenAPI DatsSol](./docs/contracts/datssol.openapi.yml)
- [Контракт DatsBlack](./docs/contracts/datsblack.openapi.json)
- [Выбранный стек и ассеты](./docs/research/stack-and-assets.md)
- [Стратегический playbook DatsSol](./docs/research/strategy-playbook.md)
- [Подробная стратегия под DatsSol](./docs/research/datssol-strategy.md)
