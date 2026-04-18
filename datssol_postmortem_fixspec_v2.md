# DatsSol: постмортем по логам и техническая спецификация v2

## 1) Что реально сломалось в последнем боевом запуске

### Наблюдения по CSV-логам
- В последней длинной live-сессии (`2026-04-17 16:36:34Z` → `16:45:11Z`) движок увидел только **108 игровых ходов**, а не весь раунд.
- Между наблюдаемыми ходами были огромные дыры: `0→92`, `121→158`, `184→240`, `421→542` и т.д.
- На всех наблюдаемых live-ходах максимум собственных плантаций был **ровно 1**. Значения `own > 1` в live-наблюдениях не встречаются.
- В логах **нет ни одного** `relocate_main != None`. Перенос ЦУ не отправлялся вообще.
- `hq_remaining_turns` минимум 4 раза делал скачок `1 -> 20`: `96→97`, `116→117`, `256→257`, `400→401`. Это типичный след **потери ЦУ и респавна**, а не штатного переноса.
- На боевых ходах регулярно летели ошибки:
  - `429 Too Many Requests` на `GET /api/arena`
  - `429 Too Many Requests` на `POST /api/command`
  - `command already submitted this turn`
  - после rate limit включался локальный `live submit backoff active`
- Часто была странная пара:
  - `top_intent = Build at X,Y`
  - но `actions = 0` и `command = []`
  Это значит, что аналитика и компоновщик payload расходились.

### Почему в визуализации «ЦУ прыгал и ничего не строилось»
Потому что это, скорее всего, были не relocates, а **респавны после гибели/исчезновения ЦУ**.

Механика игры:
- ЦУ терраформирует клетку под собой как обычная плантация.
- После достижения клеткой `100%` плантация исчезает.
- Если игрок теряет ЦУ, все плантации рушатся, игрок респавнится заново.
- Для штатного спасения ЦУ надо заранее построить соседнюю плантацию и выполнить `relocateMain`.
- В фазе сервера `ремонт/стройка` идут **до** `переноса ЦУ`, так что можно закончить соседнюю стройку и в тот же ход перевести туда ЦУ.

По логам этого не происходило:
- `relocate_main` не было ни разу.
- ЦУ несколько раз доходил до `hq_remaining_turns = 1`, после чего на следующем наблюдаемом ходе появлялся новый цикл `20`.
- При этом `own` оставался равен 1, то есть сеть так и не разрасталась.

Итог: бот не “переезжал”, а **снова и снова умирал и рождался в новой точке**.

### Почему стройки почти наверняка не могли завершиться
Даже если считать, что `repair_power` повышает силу строительства:
- базовая стройка требует довести `progress` до `50`;
- с одним автором и `CS=5` нужно примерно **10 успешных ходов** в одну и ту же стройку;
- с `repair_power +1` — примерно 9 успешных ходов;
- с `repair_power +2` — примерно 8 успешных ходов.

В логах:
- боевых ходов с `actions > 0` было мало;
- успешных submit с ненулевым command-path — **единицы**;
- максимум подряд на одну и ту же цель проходило **2 успешных хода**, после чего шли `429`, backoff или пустой payload.

То есть стройка физически не успевала дойти до 50 progress.  
Это уже достаточно, чтобы объяснить отсутствие новых плантаций даже без поисков “секретной” логической ошибки.

### Самые вероятные корневые причины
1. **Сетевой/транспортный контур сломан**
   - poll/submit происходят слишком часто;
   - контроллер ловит `429`;
   - после этого сам себе отрубает submit backoff'ом;
   - часть ходов пропускается полностью.

2. **Отсутствует строгий guard “один POST /command на turnNo”**
   - есть `command already submitted this turn`;
   - вероятно, был повторный submit в тот же ход или гонка между воркерами/циклами.

3. **Отсутствует mandatory relocate pipeline**
   - нет отдельного аварийного режима спасения ЦУ;
   - relocate не отправлялся вообще.

4. **Сломан повторяемый commit на стройку**
   - билд в DatsSol по определению требует много одинаковых повторов по одной цели;
   - текущая логика, судя по логам, слишком быстро “устает” от одной и той же цели и начинает отдавать пустой payload.

5. **Перепутаны транспортные и доменные ошибки**
   - `429`, timeout и backoff — это не доказательство, что цель стала плохой;
   - но бот вел себя так, будто команда “не сработала по логике мира”, и менял/бросал задачу.

---

## 2) Не косметика, а правильный порядок фиксов

### Порядок работ
1. **Починить turn loop и rate limiting**
2. **Починить single-flight submit**
3. **Ввести обязательное спасение ЦУ**
4. **Починить repeatable build commit**
5. **После этого включать стратегические режимы**

Пока первые 4 пункта не работают, любые разговоры про “агрессивный режим”, “анти-лидер”, “охоту на бобров” — это украшение трупа.

---

## 3) Обязательные инварианты, которые код не имеет права нарушать

```text
INV-1. На один turnNo не больше одного фактического POST /api/command.
INV-2. На один turnNo не больше одного “боевого” решения.
INV-3. Если own == 1, режим всегда bootstrap/emergency, никакой агрессии.
INV-4. Если до смерти/исчезновения ЦУ <= 3 хода и есть соседняя плантация — relocate обязателен.
INV-5. Если до исчезновения ЦУ <= 6 ходов и соседней плантации нет — build adjacent anchor обязателен.
INV-6. Если top_intent существует, compile stage не может тихо вернуть empty payload без fallback.
INV-7. Повтор одного и того же BUILD/REPAIR/BEAVER path по разным ходам разрешен и обязателен, если свежий мир не доказал невалидность.
INV-8. Transport fail != domain fail.
INV-9. Если submit outcome uncertain, в тот же ход повторно POST не делаем.
INV-10. Любой режим (aggro/defense/etc.) подчиняется HQ emergency rules.
```

---

## 4) Надежный turn loop: как не словить 429 и не умереть от собственной суеты

## 4.1. Что должно быть в рантайме
Один-единственный активный контроллер на токен.

Нужен внешний lease/lock:
- Redis key: `datssol:controller:<token>`
- TTL: 3 сек
- heartbeat: каждые 1 сек
- новый процесс без lease просто не стартует

Это убирает половину шизофрении с `command already submitted this turn`.

## 4.2. Схема polling
Использовать `GET /api/arena` как **источник истины по turnNo**.

Алгоритм:
1. Храним:
   - `last_seen_turn`
   - `last_arena_at_monotonic`
   - `last_next_turn_in`
   - `last_submit_turn`
2. После успешного arena:
   - если `turnNo == last_seen_turn`, ничего не планируем;
   - спим до `nextTurnIn - submit_margin`.
3. Если `turnNo > last_seen_turn`:
   - обновляем state;
   - строим план;
   - один раз отправляем POST;
   - помечаем turn как submitted/uncertain/accepted.

### submit_margin
Рекомендую:
- `submit_margin = clamp(0.12, 0.22, nextTurnIn * 0.2)`

То есть бить не впритык, а чуть заранее.

## 4.3. Ограничения по частоте
Жестко:
- максимум **1 GET /arena** на новый turn;
- максимум **1 дополнительный retry GET** при сетевой ошибке;
- максимум **1 POST /command** на turnNo;
- никаких циклов “пока не примут”.

## 4.4. Что делать при ошибках транспорта
### GET /arena -> 429 / timeout
Это **transport failure**:
- world model не менять;
- task не считать проваленным;
- не перегенерировать цель;
- сделать короткий retry один раз;
- если retry тоже провалился, ждать следующего ожидаемого окна хода.

### POST /command -> 429 / timeout
Это **uncertain submit**:
- возможно, сервер уже принял команду;
- в этот же turnNo **не повторять POST**;
- task пометить `pending_uncertain`;
- на следующем успешном arena проверить, был ли эффект.

### POST /command -> `command already submitted this turn`
Это почти всегда:
- дубль отправки тем же процессом
или
- второй активный контроллер.

Поведение:
- считать ход уже “занятым”;
- не делать второй submit;
- пометить `turn_submit_state = duplicate_detected`;
- поднять аларм в логи.

---

## 5) Как различать transport failure и реальный провал задачи

Это критично.

## 5.1. Состояния задач
Для каждой задачи:
- `NEW`
- `SUBMITTED_ACCEPTED`
- `SUBMITTED_UNCERTAIN`
- `CONFIRMED_PROGRESS`
- `STALLED`
- `BLOCKED`
- `ABANDONED`
- `COMPLETED`

## 5.2. Правила
### Build task
После следующего успешного arena:
- если target появился в `construction` и progress вырос — `CONFIRMED_PROGRESS`;
- если на клетке уже стоит наша новая plantation — `COMPLETED`;
- если target занят чужой completed plantation — `BLOCKED`;
- если progress не вырос, но submit был uncertain — не паниковать, дать еще 1-2 подтвержденных проверки;
- только после **2 свежих наблюдений подряд без ожидаемого эффекта** помечать `STALLED/BLOCKED`.

### Repair task
- если HP target вырос/не упал как ожидалось — `CONFIRMED_PROGRESS`;
- если target умер — `ABANDONED`;
- если author/output пропали — пересборка задачи.

### Beaver task
- если HP beaver уменьшился или цель исчезла — успех/kill;
- если beaver исчез без наших признаков last-hit — `ABANDONED`;
- если submit uncertain — ждать следующего зрения.

### Sabotage task
- если enemy hp уменьшился — ok;
- если enemy исчез и очки/kill не зафиксированы — treat as contested/unknown;
- если enemy ушел из вижна, но last seen fresh — можно держать 1 turn memory, не дольше.

---

## 6) Самая важная логика: mandatory HQ survival

Это не “режим”. Это биологический рефлекс. Без него весь остальной код мусор.

## 6.1. Оценка времени жизни ЦУ
Так как `TS=5` и апгрейда TS нет, у плантации примерно 20 ходов жизни на клетке до `100%`.

Оценивать `hq_remaining_turns` можно так:
- если в `cells` есть клетка ЦУ с progress -> `ceil((100-progress)/5)`
- иначе по возрасту ЦУ на этой клетке:
  - `20 - age_on_current_cell`

## 6.2. Bootstrap rules при own == 1
Если в сети ровно одна плантация:
1. никакой диверсии;
2. никакого бобра;
3. никакой contest-фигни;
4. первая и главная задача — **соседний anchor** для будущего relocate.

### Выбор anchor-клетки
Из 4 ортогонально соседних клеток выбрать ту, у которой максимальный score:

```text
+1000  если клетка ортогонально соседняя с HQ
+200   если ведет в предпочитаемый сектор
+120   если клетка не под видимым бобром
+80    если клетка не под storm nextPosition/radius в ближайшие 2-3 хода
+60    если она помогает сделать будущий 2-wide рост
+25    если boosted (x%7==0 && y%7==0)
-1000  если mountain
-250   если клетка почти наверняка contested enemy construction
-200   если build нельзя успеть завершить до смерти HQ
```

В bootstrap разрешен **только один locked target**.

## 6.3. Commit window для первой стройки
Если цель выбрана и не доказано, что она невозможна:
- слать **тот же BUILD path каждый ход**;
- не переключаться на соседнюю клетку просто потому, что был `429`;
- не подавлять повтор dedupe-механикой.

### Важное правило
`same build path on next turn` — это **нормальная механика игры**, а не признак застревания.

Именно тут ваш текущий код, судя по логам, вел себя как перепуганный голубь.

## 6.4. Когда делать relocate
### Нормальный relocate
Если есть соседняя готовая плантация и:
- `hq_remaining_turns <= 3`
или
- ожидается летальный саботаж/фокус

тогда отправляем:
```json
"relocateMain": [[hqX, hqY], [adjacentPlantX, adjacentPlantY]]
```

### Экстренный relocate в тот же ход, когда достраиваем anchor
Так как у сервера:
- `ремонт/стройка` идут раньше `переноса ЦУ`,
- completed construction становится обычной plantation сразу,

можно делать:
- build adjacent anchor
- **и в том же ходу** relocate на нее

если расчётный progress в этом ходу доводит стройку до 50.

Это обязательный emergency-фоллбек.

## 6.5. После relocate
Сразу на следующем ходу надо снова создавать рядом с новым ЦУ следующий anchor-кандидат.  
У ЦУ всегда должен быть запасной аэродром.

---

## 7) Build planner: не “хочу построить”, а “гарантированно доведу до 50”

## 7.1. Геометрия роста
Базовая форма — не змейка, а **компактная лента / 2-wide ribbon**:
- минимум один запасной путь к ЦУ,
- минимум один запасной сосед для relocate,
- избегать узких 1-клеточных мостов.

Цели роста:
1. bootstrap anchor
2. второй сосед для HQ / 2-wide начало
3. forward node по выбранному сектору
4. side node для утолщения
5. repeat

## 7.2. Scoring frontier cells
Для каждой candidate cell:

```text
S = 0
S += 1000  if adjacent_to_HQ and no_ready_adjacent_anchor
S += 700   if adjacent_to_HQ and ready_adjacent_anchor_count == 1
S += 500   if cell reduces articulation risk / forms 2x2 or 2x3 compact block
S += 300   if cell extends preferred direction vector
S += 160   if boosted cell
S += 120   if close to beaver after planned kill
S += 80    if improves future relocate options
S -= 500   if cell creates single-tile bridge
S -= 400   if visible beaver can hit it and we are not committing anti-beaver plan
S -= 250   if sandstorm path likely crosses before completion
S -= 200   if earthquake now and build won't finish this turn
S -= 1000  if mountain or invalid
```

## 7.3. Сколько строек держать одновременно
Жесткое правило:
- при `own <= 3` держать **1 активную стройку**
- при `4 <= own <= 8` — максимум 2
- при `9+` — максимум `min(4, floor(own/4))`

В вашей текущей ситуации правильный ответ вообще был:  
**одна стройка, пока не появился второй узел**.

## 7.4. Когда задача считается locked
Build task lock активен пока:
- target валиден по свежему миру;
- progress движется или submit был uncertain;
- стройка стратегически важна (anchor / bridge / contested high-value).

Снимать lock можно только если:
- fresh arena показал невозможность;
- стройка blocked 2 подтвержденных хода подряд;
- ЦУ респавнился и мир уже другой;
- появился более высокий emergency (например finish-and-relocate).

## 7.5. Как распределять авторов и output при сети >1
Для каждой цели:
1. собрать возможные output:
   - own connected plantations
   - `chebyshev(output, target) <= actionRange`
2. для каждого output собрать авторов:
   - connected plantations
   - `chebyshev(author, output) <= signalRange`
3. сортировка output:
   - меньшая текущая нагрузка
   - ближе к target
   - не критический HQ-узел, если можно обойтись
4. сортировка авторов:
   - не использован в этом ходу
   - не критически нужен на defense/repair
   - ближе к output

Эффективность команды через output:
```text
effective_power = base_power - output_load[output]
```
где:
- `base_power(build) = 5 + repair_power_level`
- `base_power(repair) = 5 + repair_power_level`
- `base_power(sabotage) = 5`
- `base_power(beaver) = 5`

Если `effective_power <= 0`, такую пару не использовать.

## 7.6. Когда намеренно добивать стройку в 1 ход
Если target можно закрыть сейчас и это:
- anchor для HQ
- contested cell
- critical bridge
- quake turn
- завершение перед storm/beaver pressure

тогда можно перегрузить несколько output и авторов, чтобы достроить немедленно.

---

## 8) Repair planner: кого лечить, а кого отпустить умирать без истерики

## 8.1. Приоритеты ремонта
1. ЦУ
2. adjacent relocate anchors
3. articulation/bridge nodes
4. узлы под фокусом enemy/beaver, которые держат связность
5. почти достроенные critical constructions
6. все остальные

## 8.2. Кого НЕ лечить
Не ремонтировать:
- leaf node, которая не влияет на связность;
- клетку, которой осталось 1-2 хода до auto-complete и исчезновения;
- узел, который все равно не переживет суммарный forecast damage и дешевле отпустить.

## 8.3. Forecast damage
На ход считать:
- `beaver_damage = max(0, 15 - beaver_mitigation*2)` если в зоне бобра
- `earthquake_damage = max(0, 10 - earthquake_mitigation*2)` если quake `turnsUntil=0`
- `sandstorm_damage = 2` если в зоне активной бури
- `enemy_focus_damage` — оценка по видимым enemy и недавним ударам

## 8.4. Правило ремонта
Ремонт делать, если:
```text
hp_after_forecast <= critical_threshold
AND node_value >= build_value_of_best_alternative
```

Пример threshold:
- HQ: 60% MHP
- bridge: 45% MHP
- leaf: 25% MHP

---

## 9) Beaver planner: не ферма мечты, а холодный EV

## 9.1. Когда вообще идти в бобра
Только если:
- HQ safe;
- anchor safe;
- spare_builders >= 1;
- можем либо спокойно добить, либо прийти на burst last-hit.

## 9.2. Когда НЕ идти
- own == 1
- нет relocate anchor
- идет bootstrap
- contested beaver без burst преимущества
- enemy рядом сильнее локально

## 9.3. Last-hit логика
Так как очки за бобра получает тот, кто в последний ход дал лучший урон:
- не надо долго “подтачивать” бобра для всех;
- либо мы его берем secure;
- либо приходим на burst в 1-2 хода;
- либо вообще не трогаем.

## 9.4. Beaver mitigation upgrade
`beaver_damage_mitigation` покупать не рано.  
Порог:
- минимум 20-25% живой сети регулярно стоит под beaver threat
или
- мы сознательно играем через beaver frontier.

Раньше этого апгрейд в экономике чаще мусор.

---

## 10) Sabotage planner: короткий нож, не крестовый поход

## 10.1. Когда включать агрессию
Только если:
- есть spare throughput после обязательных build/repair;
- виден enemy low-HP node;
- это articulation/bridge/anchor;
- kill/cripple делается за 1-2 хода;
- локальный EV > EV очередной стройки.

## 10.2. Кого бить
Приоритет:
1. enemy articulation / bridge
2. low-HP support node
3. enemy near-HQ anchor
4. enemy under beaver/storm pressure
5. enemy contested frontier cell

## 10.3. Не атаковать стройку диверсией
По правилам строящуюся чужую плантацию нельзя саботировать — вместо этого надо строить свою на той же клетке.  
Значит для enemy construction нужен **contest build**, а не sabotage.

---

## 11) Contest planner: как драться за спорную клетку без тупой лоботомии

### Для contested build
Если enemy тоже строит нужную клетку:
- если можем надежно закончить раньше — finish race;
- если не можем — либо abandon,
- либо специально попасть в simultaneous completion, чтобы всем обнулить стройку, если это нам выгодно.

### Для contested beaver
- только burst/lurking play;
- не быть тем дураком, который 5 ходов бесплатно разгоняет ценность last-hit соседу.

---

## 12) Rebase / Recovery mode: если сектор плохой, надо уходить, а не писать мемуары

Триггеры:
- 2 респавна за короткий промежуток;
- горы/бобры/враг делают сектор безнадежным;
- frontier score устойчиво низкий;
- defense costs > expansion value.

Поведение:
- no sabotage unless opens path;
- no beaver greed;
- стройка коридора в более чистый сектор;
- aggressive relocate discipline;
- rebuild в 2-wide compact shape.

---

## 13) Upgrade planner: как реально тратить очки, а не молиться на случай

## 13.1. Формулы derived stats
```text
repair_power = 5 + level(repair_power)
max_hp = 50 + 10 * level(max_hp)
signal_range = 3 + level(signal_range)
vision_range = 3 + 2 * level(vision_range)
decay_speed = 10 - 2 * level(decay_mitigation)
earthquake_damage = 10 - 2 * level(earthquake_mitigation)
beaver_damage = 15 - 2 * level(beaver_damage_mitigation)
```

## 13.2. Базовый приоритет по умолчанию
Для сильной экономической игры:
1. `repair_power`
2. `repair_power`
3. `max_hp`
4. `signal_range`
5. `max_hp`
6. `repair_power`
7. `vision_range`
8. `max_hp`
9. `settlement_limit` (если реально упираемся)
10. `earthquake_mitigation`
11. `beaver_damage_mitigation`
12. `vision_range`
13. `max_hp`
14. `signal_range`
15. `decay_mitigation` или situational

### Почему так
- `repair_power` — это темп строек и ремонта, то есть сердце экономики;
- `max_hp` повышает живучесть сети;
- `signal_range` улучшает логистику автор->output;
- `vision_range` нужен, когда сеть уже есть и нужно читать мир;
- mitigation upgrades — situational, не opening-core;
- `settlement_limit` не нужен, пока вы не умеете стабильно иметь много живых узлов.

## 13.3. Динамическая переоценка апгрейдов
Если хочешь не жесткий order, а scoring:
```text
score(repair_power) += 100 if avg_active_builds > 0.7
score(repair_power) += 60  if own <= 6
score(max_hp)      += 80  if enemy visible or beaver pressure high
score(signal_range)+= 70  if not enough author-output pairs
score(vision_range)+= 60  if sparse map / hunt mode / storm tracking matters
score(settlement_limit)+= 120 if own + active_constructions >= limit - 2
score(earthquake_mitigation)+= 80 if quake is forecast now or network wide
score(beaver_damage_mitigation)+= 80 if many nodes live in beaver zones
score(decay_mitigation)+= 70 if many interrupted constructions / isolation recoveries
```

---

## 14) Manual overrides: только как bias, не как ручное вождение трактора

Нужные override-поля:

```json
{
  "force_mode": "auto | bootstrap | econ | aggro | defense | contest | rebase",
  "sector_bias": {
    "vector": [1, 0],
    "strength": 0.7,
    "ttl": 40
  },
  "target_locks": [
    {"kind": "build", "cell": [x, y], "ttl": 8, "priority_boost": 1000}
  ],
  "forbidden_cells": [[x1,y1],[x2,y2]],
  "beaver_policy": "avoid | opportunistic | hunt",
  "sabotage_policy": "off | opportunistic | aggressive",
  "hq_safety_turns": 4,
  "construction_cap_override": 2,
  "output_load_cap_override": 2
}
```

### Правила override
- всегда через TTL;
- не может ломать HQ emergency;
- не может заставить бота слать невалидный path;
- только повышает/понижает score.

---

## 15) Fallback-логика: чтобы юнит не “застревал”, но и не забывал, что стройка требует повторов

Вот тут нужна аккуратность.  
У вас сейчас, похоже, сделано слишком тупо: раз команда похожа на предыдущую — выкинули.  
Для DatsSol это почти гарантированный суицид.

## 15.1. Разделить repeatable и one-shot задачи
### Repeatable
- BUILD
- REPAIR
- BEAVER_ATTACK
- SABOTAGE pressure

Для них повтор одного и того же path по разным ходам — норма.

### One-shot / event-like
- relocateMain
- switch target
- panic reroute
- contest sync

Для них dedupe нужен жестче.

## 15.2. Правильный anti-stuck
### BUILD
Путь можно банить только если свежий мир показал одно из:
- target invalid;
- target blocked permanently;
- author/output исчез;
- target lost strategic value;
- 2 свежих наблюдения подряд нет прогресса при accepted/uncertain submit.

### REPAIR
Банить если:
- цель погибла;
- heal не нужен;
- author/output invalid.

### RELOCATE
Если relocate один раз не прошел из-за invalid adjacency — пересобрать, не спамить тот же маршрут.

## 15.3. Если compile stage вдруг дал empty payload
Обязательный fallback order:
1. emergency relocate
2. locked bootstrap build
3. safe adjacent build from HQ
4. critical repair
5. upgrade only
6. safe beaver hit
7. safe sabotage

Если после этого payload все еще пуст:
- логировать как `compiler_bug`;
- не считать это “нормальным” ходом.

---

## 16) Рекомендуемый state machine режимов

```text
bootstrap:
  if own <= 1 or no_adjacent_anchor
  goal = build anchor, survive HQ

econ:
  default
  goal = compact growth + stable completions

defense:
  if HQ/bridge under visible threat
  goal = preserve control graph

aggro:
  if spare throughput and killable weak enemy nearby
  goal = cheap tempo denial

contest:
  if shared frontier / enemy construction / beaver race
  goal = deny EV, steal burst

rebase:
  if sector dead or repeated respawns
  goal = leave bad neighborhood and restart compactly
```

### Priority override stack
```text
HQ emergency > transport safety > defense > bootstrap > contest > aggro > econ cosmetics
```

---

## 17) Псевдокод планировщика хода

```python
def plan_turn(snapshot, memory, overrides):
    state = rebuild_world_state(snapshot, memory)
    mode = choose_mode(state, overrides)

    upgrade = choose_upgrade(state, mode)

    # 1. hard emergency
    emergency = maybe_plan_hq_emergency(state)
    if emergency is not None:
        payload = compile_payload(emergency.actions, emergency.relocate, upgrade)
        return ensure_non_empty(payload, state, upgrade)

    # 2. build intents
    intents = []
    intents += build_construction_intents(state, mode, overrides)

    # 3. repair intents
    intents += build_repair_intents(state, mode)

    # 4. beaver intents
    intents += build_beaver_intents(state, mode)

    # 5. sabotage / contest intents
    intents += build_sabotage_and_contest_intents(state, mode)

    # 6. allocate authors and outputs
    actions = allocate_actions(intents, state)

    # 7. maybe relocate if safe and desirable
    relocate = maybe_plan_normal_relocate(state, actions)

    payload = compile_payload(actions, relocate, upgrade)
    payload = apply_payload_fallbacks(payload, state, upgrade)

    return payload
```

---

## 18) Псевдокод compile/allocate without self-sabotage

```python
def allocate_actions(intents, state):
    used_authors = set()
    output_load = defaultdict(int)
    actions = []

    for intent in sorted(intents, key=lambda i: i.priority, reverse=True):
        candidates = []

        for output in candidate_outputs(intent.target, state):
            eff = base_power(intent.kind, state) - output_load[output.id]
            if eff <= 0:
                continue

            for author in candidate_authors(output, state):
                if author.id in used_authors:
                    continue
                if not valid_path(author, output, intent.target, state):
                    continue

                score = intent.priority + path_bonus(author, output, intent.target, state) - output_load[output.id] * 20
                candidates.append((score, eff, author, output))

        if not candidates:
            continue

        # greedy best pair for now
        candidates.sort(reverse=True, key=lambda x: (x[0], x[1]))
        _, eff, author, output = candidates[0]

        actions.append(make_path(author, output, intent.target))
        used_authors.add(author.id)
        output_load[output.id] += 1

        intent.applied_power += eff
        if intent.applied_power >= intent.required_power:
            intent.satisfied = True

    return actions
```

---

## 19) Минимальный набор диагностик, который должен писать бэкенд каждый ход

Без этого вы снова будете гадать по звёздам.

### 19.1. Transport
- `turn_no`
- `arena_get_status`
- `arena_latency_ms`
- `command_post_status`
- `command_latency_ms`
- `submit_state = accepted | uncertain | duplicate | skipped | compiler_bug`

### 19.2. World
- `own_count`
- `connected_count`
- `isolated_count`
- `hq_pos`
- `hq_remaining_turns`
- `adjacent_anchor_count`
- `articulation_count`
- `active_constructions`
- `construction_progress_by_target`

### 19.3. Planning
- `mode`
- `top_5_intents`
- `selected_actions`
- `relocate_planned`
- `upgrade_selected`
- `why_payload_became_empty`

### 19.4. Task tracking
Для каждой locked задачи:
- `task_id`
- `kind`
- `target`
- `state`
- `expected_effect`
- `observed_effect`
- `transport_fail_streak`
- `domain_fail_streak`

---

## 20) Самый короткий actionable чеклист для Codex

### Сначала починить транспорт
- [ ] один активный worker на токен
- [ ] не более 1 POST на turnNo
- [ ] не более 1-2 GET на ход
- [ ] не считать 429 “провалом стратегии”
- [ ] убрать логику, которая после transport fail начинает метаться по целям

### Потом починить HQ survival
- [ ] mandatory bootstrap anchor
- [ ] mandatory relocate при `hq_remaining_turns <= 3`
- [ ] finish-and-relocate same turn
- [ ] всегда держать соседний backup-anchor

### Потом починить build commit
- [ ] repeat same BUILD path allowed across turns
- [ ] target lock до свежего доказательства невалидности
- [ ] empty payload после non-empty intent = bug
- [ ] fallback не должен ронять ход

### Потом включать стратегию
- [ ] compact 2-wide growth
- [ ] defense by articulation nodes
- [ ] opportunistic aggro only with spare throughput
- [ ] beaver only by EV
- [ ] contest only when выгодно

---

## 21) Практический вердикт
Последний запуск проиграл не потому, что “сама стратегия frontier плохая”.  
Он проиграл потому, что:

1. контроллер видел только часть ходов;
2. спамил/ловил rate limit;
3. не делал relocate вообще;
4. не умел дисциплинированно повторять одну и ту же стройку нужное число ходов;
5. местами сам себе вырезал action payload до пустоты, хотя planner еще хотел строить.

То есть сперва надо чинить **механику исполнения стратегии**, а уже потом спорить о тонкостях меты.

Если всё это исправить, базовый победный skeleton такой:
- bootstrap anchor immediately;
- relocate on time;
- grow compact 2-wide;
- commit to builds until confirmed invalid;
- distinguish network failure from world failure;
- attack only when it не ломает темп экономики.