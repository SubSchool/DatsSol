# Production Rebuild & Secure Deploy Plan

## 2026-03 Corrections (history-preserving)
- ~~Persistent media on SubSchool is mostly egress recordings~~ → SubSchool persistent media now includes broad upload categories under `apps/backend/static/uploads/*`, not recordings only.
- ~~It is enough to back up DB for reliable restore~~ → Reliable restore requires both DB dump and full uploads backup (`apps/backend/static/uploads`).
- ~~File restore can be limited to legacy folders~~ → Restore must include new certificate customization assets (`certificate_assets/logos`, `certificate_assets/signatures`, `branding`) in addition to existing uploads.
- ~~Schema updates may be patched manually during incident response~~ → Production schema updates must be delivered via Alembic migrations and tracked in VCS.
- ~~Service up state implies app readiness~~ → Readiness gate is: DB reachable + migrations at `head` + `/health` + static media checks.

### 2026-03 SubSchool deploy gate (mandatory)
1. Pre-deploy backup:
   - fresh DB dump;
   - archive of `apps/backend/static/uploads`.
2. Deploy and migrate:
   - run `alembic upgrade head` in backend release.
3. Verify API + files:
   - `GET /health` = `200`;
   - check representative files from:
     - `/static/uploads/covers/...`
     - `/static/uploads/avatars/...`
     - `/static/uploads/certificate_assets/logos/...`
     - `/static/uploads/certificate_assets/signatures/...`
     - `/static/uploads/branding/...`
     - `/static/uploads/recordings/...`
4. Only after successful checks continue with post-deploy smoke and traffic validation.

## TL;DR (do this first)
- Fresh OS, create user `dev`, SSH keys only, disable root password/FTP, enable `ufw` allow `22/tcp`, `80/tcp`, `443/tcp`, drop the rest.
- **Egress lockdown:** `ufw default deny outgoing`; allow only `80/tcp`, `443/tcp`, `53/udp` (your resolver). Add Docker MASQUERADE rules for these ports only (see “Egress firewall”).
- Install Docker + `docker compose` plugin + `fail2ban`.
- Restore Postgres volumes (DatedIn, 10kQ, SubSchool) and Caddy data from `server-backup/volumes/*`.
- Restore uploads/static: `server-backup/uploads/SubSchool_uploads`, `DatedIn_uploads`, `10kq_staticfiles`.
- Run Caddy as the only exposed service (80/443). All apps/DB/Redis run on private bridge networks; **no host-network**; **no DB ports published**. Calls выносятся на отдельный VPS (167.114.2.177).
- Rotate every password/secret (DB users, JWT, LiveKit keys, Django/FastAPI secrets, SMTP, OpenAI, etc.).
- Harden containers (cap_drop/no-new-privileges where совместимо, read_only для статик), whitelist `pr.verto.team` по IP RU, включить auditd алерты в Telegram.
- Validate health/SSL per domain, then enable automated backups and updates.
- **Перед любыми действиями на проде сделать свежий бэкап**: `sudo docker exec subschool_db_prod pg_dump -U subschool -d subschool >/home/ubuntu/subschool_dump_$(date +%Y%m%d_%H%M).sql` (аналогично для других БД) и сохранить off-box. Не трогаем тома без резервной копии.

## What we recovered
- Postgres data dirs (ready to mount as volumes):
  - `server-backup/volumes/datedin_db_data` (DatedIn)
  - `server-backup/volumes/db_pgdata_10kq` (10kQ)
  - `server-backup/volumes/subschool_db_data` (SubSchool main)
  - `server-backup/volumes/subschool_subschool_pgdata` (legacy SubSchool)
- Caddy state (certs + autosave): `server-backup/volumes/subschool_caddy_data`, `subschool_caddy_config`; merged config file `server-backup/configs/Caddyfile.merged`.
- Uploads/static:
  - `server-backup/uploads/SubSchool_uploads` (~164 MB) — `backend/static/uploads/*` (covers, recordings, videos, etc.).
  - `server-backup/uploads/DatedIn_uploads` (~62 MB) — `backend/app/uploads/*`.
  - `server-backup/uploads/10kq_staticfiles` (~3.7 MB) — Django collected static.
- We did **not** find `.env` files on the server; regenerate all secrets.

## Access & SSH (new server state)
- Основной сервер: IP `137.74.202.47`, user `ubuntu`, key `~/.ssh/id_ed25519_ovh_subschool`, только по ключу; `ufw` 22/80/443, `fail2ban` включён.
- Calls VPS (отдельный): IP `167.114.2.177`, user `ubuntu`, тот же ключ; пароли отключены.

## Base OS hardening (after reinstall)
- Users: create `dev`, add to `docker` group; disable root SSH password; permit key auth only.
- Firewall inbound: `ufw default deny incoming`, allow `22/tcp`, `80/tcp`, `443/tcp`; add your office IP allow-list for SSH if possible.
- Services: remove FTP daemon; install `fail2ban`; keep unattended upgrades on.
- Time: set timezone UTC; enable chrony/systemd-timesyncd.

## Egress firewall (must-do to stop UDP abuse)
```bash
ufw --force reset
ufw default deny incoming
ufw default deny outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow out 53/udp      # DNS
ufw allow out 80/tcp      # HTTP egress
ufw allow out 443/tcp     # HTTPS egress
ufw --force enable
```
- Docker NAT whitelist (limits containers to the same egress set):
  ```bash
  # /etc/ufw/after.rules append before COMMIT of *nat
  *nat
  :POSTROUTING ACCEPT [0:0]
  -A POSTROUTING -s 172.16.0.0/12 -p tcp --dport 80 -j MASQUERADE
  -A POSTROUTING -s 172.16.0.0/12 -p tcp --dport 443 -j MASQUERADE
  -A POSTROUTING -s 172.16.0.0/12 -p udp --dport 53 -j MASQUERADE
  COMMIT
  ```
- Outbound DNS: point apps/containers to a trusted resolver (e.g., 1.1.1.1/8.8.8.8 or your own).
- Optional: if `pr.verto.team` должен быть приватным — в Caddy ограничить по IP RU‑сервера.
- **Обязательные анти-DDoS правила в DOCKER-USER (накатывать после docker start):**
  ```bash
  iptables -t filter -N DOCKER-USER 2>/dev/null || true
  iptables -t filter -F DOCKER-USER
  # Явно разрешаем DNS egress (udp/tcp 53) и http/https при необходимости:
  iptables -t filter -A DOCKER-USER -p udp --dport 53 -j RETURN
  iptables -t filter -A DOCKER-USER -p tcp --dport 80  -j RETURN
  iptables -t filter -A DOCKER-USER -p tcp --dport 443 -j RETURN
  # Всё остальное UDP дропаем:
  iptables -t filter -A DOCKER-USER -p udp -j LOG --log-prefix \"DOCKER-USER-UDP-DROP \" --log-level 4
  iptables -t filter -A DOCKER-USER -p udp -j DROP
  # Остальные цепочки продолжают работу:
  iptables -t filter -A DOCKER-USER -j RETURN
  ```
  Добавить аналог в `/etc/iptables/rules.v4` или systemd unit, чтобы переживало reboot.

## Docker hardening
- `/etc/docker/daemon.json`:
```json
{
  "icc": false,
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "default-address-pools": [{ "base": "172.30.0.0/16", "size": 24 }]
}
```
`systemctl daemon-reload && systemctl restart docker`
- Compose services: drop privileges where можно:
  - Add `security_opt: ["no-new-privileges:true"]`
  - Add `cap_drop: ["ALL"]` (and selectively add back if требуется)
  - For statик/прокси: `read_only: true` + tmpfs for `/tmp` if нужно.
- No `network_mode: host` anywhere. Only bridge networks.
- Keep volumes minimal; do not mount docker.sock into apps.

### Runtime hardening applied (prod)
- DatedIn API: `cap_drop=ALL`, `no-new-privileges`, код/dist read-only, uploads rw.
- 10kQ API: `cap_drop=ALL`, `no-new-privileges`, код/static read-only.
- 10kQ admin/site nginx: без cap_drop (nginx требует chown temp), read-only контент.
- SubSchool: backend `cap_drop=ALL`/`no-new-privileges`; livekit `cap_drop=ALL`; redis `cap_drop=ALL`; postgres без cap_drop; calls (Next.js) без cap_drop (нужен npm install/build).
- verto-proxy: `cap_drop=ALL`/`no-new-privileges`, без bind-mount (использует собранный образ).
- Caddy: единственный публичный порт 80/443; `pr.verto.team` закрыт для всех, кроме IP RU `79.174.78.142` (остальным 403).
- Новые требования после инцидента 2025-12-16:
  - DOCKER-USER drop для всего UDP (кроме явных ALLOW выше).
  - Отключать IPv6 или зеркально дропать udp6/tcp6 в DOCKER-USER/ufw.
  - `cap_drop` минимум: `NET_RAW`, `NET_ADMIN`, `SYS_ADMIN`, `MKNOD` для всех app-контейнеров; ideal: `cap_drop: ["ALL"]`.
  - `read_only: true` + `tmpfs: /tmp` для фронтов/прокси; запрет писать в `/var`.
  - Не выполнять `npm install`/`pip install` в runtime контейнера. Образы собирать заранее (`npm ci && next build`, `pip install` в image), монтировать только dist/build.
  - UFW включать и проверять статус после reboot (`ufw status numbered`). Логирование UFW — уровень low.

## Docker & network model
- One reverse proxy: Caddy container exposed on host `80/443` only.
- Each product gets its own Docker bridge network (no `--network host` anywhere):
  - `datedin_net`, `tenkq_net`, `subschool_net`, `caddy_net`.
- Databases run in their own networks (`*_db_net`) with **no published ports**. Apps connect via container DNS.
- Caddy joins each app network that it needs to reach (`docker network connect ...`).
- Redis/LiveKit/etc. also stay on internal networks; nothing except Caddy/SSH faces the internet. Calls на основном сервере не запускать — он вынесен на отдельный VPS (см. раздел Calls stack).

## Restore Postgres volumes (on fresh host)
```bash
mkdir -p ~/server-backup
rsync -a <local>/server-backup/ ~/server-backup/   # push backups to server

# Create volumes
for v in datedin_db_data db_pgdata_10kq subschool_db_data subschool_subschool_pgdata subschool_caddy_data subschool_caddy_config; do
  docker volume create $v
done

# Restore each volume from backup (example function)
restore_vol() { vol="$1"; docker run --rm -v ${vol}:/data -v ~/server-backup/volumes/${vol}:/backup busybox sh -c "cd /backup && cp -a . /data"; }
restore_vol datedin_db_data
restore_vol db_pgdata_10kq
restore_vol subschool_db_data
restore_vol subschool_subschool_pgdata
restore_vol subschool_caddy_data
restore_vol subschool_caddy_config
```

## Restore uploads/static
```bash
mkdir -p ~/apps/SubSchool/backend/static/uploads ~/apps/DatedIn/backend/app/uploads ~/apps/10kq/backend/staticfiles
cp -a ~/server-backup/uploads/SubSchool_uploads/. ~/apps/SubSchool/backend/static/uploads/
cp -a ~/server-backup/uploads/DatedIn_uploads/. ~/apps/DatedIn/backend/app/uploads/
cp -a ~/server-backup/uploads/10kq_staticfiles/. ~/apps/10kq/backend/staticfiles/
```

## Secrets to recreate/rotate
- Strong, unique Postgres passwords per DB/user; create non-superuser app roles.
- API secrets: JWT/FastAPI `JWT_SECRET_KEY`, Django `SECRET_KEY`, any refresh/access token keys.
- Third-party keys: LiveKit API key/secret, SMTP/Mail, OpenAI, Google Play, etc.
- CORS/allowed hosts per domain; admin creds; redis password if used.

## Stack-by-stack deploy (secure layout)

### Caddy (shared)
- Run Caddy in `caddy_net`, bind `80/443`, mount restored `subschool_caddy_*` volumes and a host `Caddyfile` (rebuild from `server-backup/configs/Caddyfile.merged`, removing legacy host-net references).
- Ensure each site proxies to container names on their internal networks:
  - `new.datedin.pro` → `datedin_api:8000`
  - `10thousandquestions.com` → `tenkq_site:80`
  - `admin.10thousandquestions.com` → `tenkq_admin:80`
  - `api.10thousandquestions.com` → `tenkq_api:8001`
  - `teacher.subschool.us` / `class.subschool.us` → `subschool_backend:8000` (with `/api`, `/static`, SPA fallback)
- `admin.subschool.us` → `subschool_backend:8000` (`/api`, `/static`, SPA fallback)
  - `call.subschool.us` → `subschool_livekit:7880` (WS) and `subschool_calls:3000`
- Validate: `docker exec caddy caddy validate ...` then reload.

### DatedIn
- Networks: `datedin_net` (app) + connect to `caddy_net`.
- DB: `postgres:16` on `datedin_db_data`, env `POSTGRES_USER=datedin_app`, `POSTGRES_PASSWORD=<strong>`, no `ports:` mapping.
- App: Python 3.11 container, mount repo, env `DATABASE_URL=postgresql+asyncpg://datedin_app:<pwd>@datedin-db:5432/datedin`, `JWT_SECRET_KEY=<rotated>`.
- Volumes: bind uploads dir.
- Health: `/health` via Caddy; admin login via query params.

### 10kQ
- Networks: `tenkq_net` + `caddy_net`.
- DB: `postgres:16` on `db_pgdata_10kq`, user `tenkq_app` with strong password, no published port.
- API: Django/gunicorn on `8001`, env `DATABASE_URL=postgresql://tenkq_app:<pwd>@tenkq-db:5432/tenkq`, `ALLOWED_HOSTS=api.10thousandquestions.com`, proper CORS. Use `gunicorn server.asgi:application --bind 0.0.0.0:8001 --workers 3 -k uvicorn.workers.UvicornWorker` (install `uvicorn[standard]`).
- Static: mount `staticfiles` restored above.
- Admin/marketing SPAs served by nginx containers inside `tenkq_net`; Caddy proxies by name.

### SubSchool (основной сервер)
- Networks: `subschool_net` + `caddy_net`.
- DB: `postgres:16` on `subschool_db_data` (and/or `subschool_subschool_pgdata` if needed for legacy), strong creds, no published port. Role used: `subschool_app` / `SuBSch00l_r7Q8vWm` (rotate later).
- Redis: `redis:7-alpine` with password `ReDiS_suB_7v9u4w`, internal only.
- Backend: FastAPI/uvicorn on `8000`, env sample:
  - `DATABASE_URL=postgresql+psycopg://subschool_app:<pwd>@subschool-db:5432/subschool`
  - `JWT_SECRET=<strong>`, `ALLOW_UNAUTH_EGRESS=false`
  - `LIVEKIT_WS_URL=ws://livekit:7880`
  - `LIVEKIT_PUBLIC_WS_URL=wss://call.subschool.us`
  - `LIVEKIT_API_KEY=lk_prod_1`, `LIVEKIT_API_SECRET=lk_SuB_9q2Xr4v6T8y`
  - `CALLS_BASE_URL=https://call.subschool.us`
- Calls на основном сервере не размещаем; используем отдельный VPS для `call.subschool.us`.
- LiveKit server on `7880` (TCP via Caddy), no published UDP; config `livekit/livekit.prod.yaml` updated to use Redis password and new keys. Egress uses `/config/egress.yaml` with same keys/pwd; mount recordings to `backend/static/uploads/recordings`.
- Schema sanity (2026-01-13): finance/subscription enums lowercased + extended (`payout`, `promo_*`, course/module/lesson sales); added `email_verified` on users, `email_tokens`, promo tables, and student balance/transactions/purchases. Reapply this SQL patch if restoring from older dumps before starting backend.
- ~~SPA assets: build teacher/student via Node 20 in `/home/ubuntu/apps/SubSchool/web` (`npm install && npm run build:teacher && npm run build:student`), serve by Caddy mounts:~~
  - ~~`/home/ubuntu/apps/SubSchool/web/dist-teacher` → `/var/www/teacher`~~
  - ~~`/home/ubuntu/apps/SubSchool/web/dist-student` → `/var/www/class`~~
- ~~Admin SPA: `npm run build:admin` → `/home/ubuntu/apps/SubSchool/web/dist-admin` → `/var/www/admin`~~
- Legacy SPA (`apps/web`) остаётся в стеке и собирается контейнером `subschool_web_builder_prod` в docker volumes:
  - `subschool_teacher_site` → `/var/www/teacher`
  - `subschool_class_site` → `/var/www/class`
  - `subschool_admin_site` → `/var/www/admin`
- Новый Nuxt frontend (`apps/web-nuxt`) разворачивается отдельными контейнерами (по одному на портал).
- Target mapping для прода:
  - legacy: `teacher.subschool.us`, `class.subschool.us`, `admin.subschool.us`
  - beta Nuxt: `teacher-beta.subschool.us`, `class-beta.subschool.us`, `admin-beta.subschool.us`
- Caddy handles `/api`, `/static`, `/livekit*`, `/rtc`, `/twirp`, SPA fallback. Ports 7881/7882 NOT published externally; LiveKit reachable only through Caddy TLS on 443.
- Public SSR/SPA split for `class.subschool.us`:
  - SSR catalog: `/`, `/courses*`, `/teachers*`, `/schools*`, `/vacancies*`, `/companies*`, `/profiles*`
  - SPA only: `/login`, `/register` (including localized variants), all private pages (`/dashboard`, `/chats`, etc.)
  - split key: `ss_spa=1` cookie (no cookie -> SSR, cookie -> SPA for catalog paths); `_spa=1` query is a fallback override to force SPA
  - SSR responses must include `Vary: Cookie` and `Cache-Control: private, no-store, no-cache, must-revalidate`

## Post-deploy validation (основной сервер)
- Caddy: `docker exec caddy caddy validate ...`, check certs issued.
- Health checks:
  - `https://new.datedin.pro/health`
  - `https://api.10thousandquestions.com/api/schema/` (or `/health`)
  - `https://teacher.subschool.us/api/health`
  - `wss://call.subschool.us/rtc` WebSocket upgrade succeeds (проверяется на отдельном VPS).
- SubSchool routing smoke:
  - `python3 /home/ubuntu/apps/SubSchool/ops/verify_public_routing.py --class-base https://class.subschool.us --admin-base https://admin.subschool.us`
  - expected: `class /courses` SSR without cookie, SPA with `ss_spa=1` (including quoted cookie form) or `_spa=1`; `/login` and `/register` always SPA; `class /admin/login` returns `404`.
- Backend smoke tests (manual):
  - from repo root: `./.venv/bin/pytest apps/backend/app/tests/test_front_api_smoke.py`
- UI e2e smoke tests (manual, no CI; run from operator machine):
  - first-time browser install: `cd apps/web && npm run e2e:install`
  - run:
    - `E2E_API_BASE_URL=https://teacher.subschool.us/api E2E_TEACHER_BASE_URL=https://teacher.subschool.us E2E_STUDENT_BASE_URL=https://class.subschool.us E2E_ADMIN_BASE_URL=https://admin.subschool.us E2E_CALLS_BASE_URL=https://call.subschool.us npm run e2e`
- DB reachability: inside each app container, run `pg_isready -h <db-host> -U <user> -d <db>`.
- File mounts: verify a couple of restored uploads are served (e.g., one cover image, one user photo).

## Backups (SubSchool: DB + files)

### Local DB backup (to operator machine)
- Create a compressed custom-format dump from the prod DB and save locally:
  ```bash
  BACKUP_TS=$(date +"%Y-%m-%d_%H%M%S") && \
  ssh -i ~/.ssh/id_ed25519_ovh_subschool -o StrictHostKeyChecking=accept-new ubuntu@137.74.202.47 \
    'set -a; [ -f /home/ubuntu/apps/SubSchool/.env.deploy ] && . /home/ubuntu/apps/SubSchool/.env.deploy; set +a; \
     sudo -n docker exec $(sudo -n docker ps --filter name=subschool_db_prod --format "{{.Names}}" | head -n1) \
     pg_dump -U "${DB_USER:-subschool}" -d "${DB_NAME:-subschool}" -F c' | gzip -c > \
  "/Users/maksimmamchur/Documents/Projects/Production/backups/subschool_prod_${BACKUP_TS}.dump.gz"
  ```
- Restore locally (example): `pg_restore -d <target_db> -F c <dump_file>`

### Off‑site backup storage (FTP in OVH, Roubaix)
- Storage host: `ftpback-rbx2-219.ovh.net` (FTP only, ACL allowlist required).
- Base directory: `/subschool` on the backup storage.
- Scripts on server:
  - `/home/ubuntu/backup_scripts/backup_to_ftp.py` — creates DB dump + uploads archive and pushes to FTP.
  - `/home/ubuntu/backup_scripts/.ftp.env` — credentials (600 perms). **Do not commit**.
  - Local temp directory: `/home/ubuntu/backup_data/tmp`
- What is backed up:
  - DB: `pg_dump -F c` compressed to `*_db.dump.gz`
  - Files: `/home/ubuntu/apps/SubSchool/backend/static/uploads` compressed to `*_files.tar.gz`

### Automation & retention
- Cron (daily at 02:30 server time):
  ```
  30 2 * * * python3 /home/ubuntu/backup_scripts/backup_to_ftp.py >> /home/ubuntu/backup_scripts/backup.log 2>&1
  ```
- Retention policy: keep **last 2** backups. Oldest is deleted **only after** a new backup finishes and uploads successfully.
- Log file: `/home/ubuntu/backup_scripts/backup.log`

### UFW egress rule required for FTP
- Because `ufw default deny outgoing` is enabled, add explicit egress to the FTP host IP:
  ```bash
  sudo ufw allow out to 178.33.60.69 proto tcp
  ```
- Verify TCP 21 from server:
  ```bash
  python3 - <<'PY'
  import socket
  s=socket.socket(); s.settimeout(5)
  s.connect(('178.33.60.69',21))
  print('ftp ok')
  s.close()
  PY
  ```

### Manual run (one‑off backup to FTP)
```bash
python3 /home/ubuntu/backup_scripts/backup_to_ftp.py
```

### Restore from FTP (DB + files)
1) Download the latest backup folder from `/subschool/subschool_YYYYMMDD_HHMMSS/`.
2) DB restore:
   ```bash
   gzip -dc subschool_YYYYMMDD_HHMMSS_db.dump.gz | pg_restore -d subschool -F c
   ```
3) Files restore:
   ```bash
   tar -xzf subschool_YYYYMMDD_HHMMSS_files.tar.gz -C /home/ubuntu/apps/SubSchool/backend/static
   ```
4) Restart backend if needed: `docker compose -f docker-compose.prod.yml up -d --build backend`

## Ongoing safety
- Backups: nightly `pg_dump` + weekly volume snapshot to off-box storage; include uploads; test restores monthly.
- Patching: monthly `apt upgrade`, quarterly Docker base image rebuilds.
- Logging: retain Docker logs, Caddy access logs; optional crowdsec.

## Calls stack (отдельный VPS 167.114.2.177)
- SSH: `ssh -i ~/.ssh/id_ed25519_ovh_subschool -o StrictHostKeyChecking=accept-new ubuntu@167.114.2.177` (пароли выключены).
- UFW: allow 22/tcp, 80/tcp, 443/tcp, 7881/tcp, 7882/udp; deny inbound default. DOCKER-USER: allow UDP 53 и 7882; лог + DROP остального UDP; RETURN.
- Docker compose в `/home/ubuntu/call-stack`:
  - `redis:7-alpine` (pwd `ReDiS_suB_7v9u4w`).
  - `livekit/livekit-server:v1.9.2` (keys `ss_prod_1` / `lk_SuB_9q2Xr4v6T8y`, ports 7880/7881 tcp, 7882 udp).
  - `meet` (Next.js из `calls/meet`): env `LIVEKIT_URL=wss://call.subschool.us`, `LIVEKIT_API_KEY/SECRET` как выше; команда `npm install --no-audit --no-fund && npm run build && npm run start -- -H 0.0.0.0 -p 3000`.
  - `caddy:2.8`: proxy `call.subschool.us` → `/twirp` `/rtc` → `livekit:7880`, остальное → `meet:3000`; ACME email `maksim@subschool.us`.
- Проверки:
  - `curl -I https://call.subschool.us` → 200
  - `curl -s https://call.subschool.us/api/connection-details?roomName=demo&participantName=test` → JSON с `serverUrl=wss://call.subschool.us`
  - WS probe `wss://call.subschool.us/rtc` (upgrade ok).
- Обновление meet (НЕ использовать `--delete`):
  1) `rsync -az -e "ssh -i ~/.ssh/id_ed25519_ovh_subschool -o StrictHostKeyChecking=accept-new" SubSchool/calls/meet/ ubuntu@167.114.2.177:/home/ubuntu/call-stack/calls/meet`
  2) `ssh ... 'cd /home/ubuntu/call-stack && sudo docker-compose down && sudo docker-compose up -d'`
- Безопасность: не запускать `subschool_calls` на основном сервере; держать UFW/DOCKER-USER правила; SSH только по ключу.
- **Разбор инцидента потери данных (2026-01-10)**:
  - Ошибка: вместо работы с актуальным томом `subschool_db_data` был выполнен restore из старого бэкапа `~/server-backup/volumes/subschool_db_data`, что перезатёр свежие данные (учитель, курс).
  - Причина: отсутствие предварительного pg_dump/снимка перед вмешательством; отсутствие проверки наличия более свежего тома/снапшота; выполнение `docker-compose down` с последующим копированием в том.
  - Как избежать: всегда делать `pg_dump` перед изменениями; перед restore явно сравнивать датировки томов/бэкапов; использовать временный том для проверки бэкапа (mount -> тест) и только потом заменять; при необходимости — LVM/бэкап провайдера.
- Fail2ban (host): `sshd`, `nginx-botsearch`, `nginx-http-auth` включены через `/etc/fail2ban/jail.local` (banaction `iptables-multiport`, `ignoreip=127.0.0.1/8 ::1`, `maxretry` 5/3, `findtime` 10m/5m, bantime 1h SSH, 12h nginx). Проверки:
  ```bash
  systemctl status fail2ban
  fail2ban-client status
  fail2ban-client status sshd
  fail2ban-client status nginx-botsearch
  tail -f /var/log/fail2ban.log
  ```
- Monitoring:
  - basic uptime probes per domain; alert on 5xx and high DB connections.
  - auditd alerts to Telegram (bot token already configured): `/usr/local/bin/audit_exec_alert.sh` + timer `audit-exec-alert.timer` (каждую минуту слать события exec в /tmp|/var/tmp|/dev/shm в chat_id 703707467).
  - (Опционально) добавить rate-limit/fail2ban на Caddy access.

## Test stand (VPS 51.222.136.126)
- Назначение: отдельный тестовый стенд SubSchool, изолированный от прода.
- ~~Хост: `ubuntu@51.222.136.126` (SSH key тот же, что и на проде). Домены: `test-teacher.subschool.us`, `test-class.subschool.us`, `test-admin.subschool.us`, `test-call.subschool.us`, `test-board.subschool.us`.~~
- Хост: `ubuntu@51.222.136.126` (SSH key тот же, что и на проде).
- Актуальные тестовые домены:
  - Nuxt frontend: `test-teacher.subschool.us`, `test-class.subschool.us`, `test-admin.subschool.us`
  - Legacy frontend: `test-old-teacher.subschool.us`, `test-old-class.subschool.us`, `test-old-admin.subschool.us`
  - Shared services: `test-call.subschool.us`, `test-board.subschool.us`
- На первом входе OVH требует смену пароля пользователя `ubuntu` (forced password reset), после чего дальше используем ключ.

### Развёртывание
1) Установить Docker Engine + Compose plugin:
```bash
ssh -i ~/.ssh/id_ed25519_ovh_subschool ubuntu@51.222.136.126
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
2) Синхронизировать стеки:
- main stack: `/home/ubuntu/apps/SubSchool` (backend/web/public-ssr/livekit/ops + `.env`/`.env.deploy` + `docker-compose.prod.yml`)
- calls/board stack: `/home/ubuntu/call-stack`
3) Переключить домены на test:
- в `/home/ubuntu/apps/SubSchool/.env` и `.env.deploy`: `TEACHER_DOMAIN`, `CLASS_DOMAIN`, `CALL_DOMAIN`, `LIVEKIT_*`, `CALLS_BASE_URL`, `TEACHER_APP_URL`, `STUDENT_APP_URL`, `BOARD_BASE_URL` -> `test-*`
- в `/home/ubuntu/apps/SubSchool/ops/Caddyfile`: заменить прод-домены на `test-*`; добавить site block для `test-board` (proxy к `board`/`board-room`).
- в `/home/ubuntu/call-stack/livekit.yaml`: `node_ip=51.222.136.126`, webhook -> `https://test-teacher.subschool.us/api/livekit/webhook`
- в `/home/ubuntu/call-stack/docker-compose.yml`: `LIVEKIT_URL=wss://test-call.subschool.us`, `NEXT_PUBLIC_BACKEND_URL=https://test-teacher.subschool.us/api`
4) Поднять сервисы:
```bash
cd /home/ubuntu/call-stack
sudo docker compose up -d --build redis livekit egress meet board-room board

cd /home/ubuntu/apps/SubSchool
sudo docker compose -f docker-compose.prod.yml --env-file .env.deploy up -d --build

# Caddy main stack должен видеть livekit/meet/board из call-stack сети
sudo docker network connect call-stack_default subschool_caddy_prod || true
sudo docker exec subschool_caddy_prod caddy validate --config /etc/caddy/Caddyfile
sudo docker exec subschool_caddy_prod caddy reload --config /etc/caddy/Caddyfile
```

### Обновление двух фронтов на test (отдельно)
- Legacy (`apps/web`, домены `test-old-*`):
```bash
rsync -az -e "ssh -i ~/.ssh/id_ed25519_ovh_subschool -o StrictHostKeyChecking=accept-new" \
  apps/web/ ubuntu@51.222.136.126:/home/ubuntu/apps/SubSchool/web/

ssh -i ~/.ssh/id_ed25519_ovh_subschool -o StrictHostKeyChecking=accept-new ubuntu@51.222.136.126 '
  cd /home/ubuntu/apps/SubSchool &&
  sudo docker restart subschool_web_builder_prod &&
  sleep 5 &&
  sudo docker exec subschool_caddy_prod caddy validate --config /etc/caddy/Caddyfile &&
  sudo docker exec subschool_caddy_prod caddy reload --config /etc/caddy/Caddyfile
'
```
- Nuxt (`apps/web-nuxt`, домены `test-*`):
```bash
pnpm -C apps/web-nuxt build

rsync -az --delete -e "ssh -i ~/.ssh/id_ed25519_ovh_subschool -o StrictHostKeyChecking=accept-new" \
  apps/web-nuxt/.output/ ubuntu@51.222.136.126:/home/ubuntu/apps/SubSchool/apps/web-nuxt/.output/

ssh -i ~/.ssh/id_ed25519_ovh_subschool -o StrictHostKeyChecking=accept-new ubuntu@51.222.136.126 '
  sudo docker restart subschool_frontend_nuxt_teacher_test subschool_frontend_nuxt_class_test subschool_frontend_nuxt_admin_test
'
```
- Важно: Caddy routing должен одновременно содержать 6 frontend-hosts (`test-*` и `test-old-*`), где:
  - `test-*` -> Nuxt containers (`subschool_frontend_nuxt_*_test:3000`)
  - `test-old-*` -> legacy static roots (`/var/www/teacher|class|admin`)

### Проверки и тесты
- Smoke по доменам:
```bash
for d in test-teacher.subschool.us test-class.subschool.us test-admin.subschool.us test-old-teacher.subschool.us test-old-class.subschool.us test-old-admin.subschool.us test-call.subschool.us test-board.subschool.us; do
  curl -sS -o /dev/null -w "%{http_code} %{url_effective}\n" "https://$d/"
done
```
- Backend tests (в контейнере backend):
```bash
sudo docker exec subschool_backend_prod sh -lc "pip install --no-cache-dir pytest && cd /app && pytest app/tests -q"
```
Ожидаемо: `128 passed`.
- E2E seed на сервере (данные чистить не нужно для test):
```bash
cd /home/ubuntu/apps/SubSchool
sudo docker run --rm --network subschool_default -v /home/ubuntu/apps/SubSchool/backend:/app -w /app -e DATABASE_URL="postgresql+psycopg://subschool:subschool@db:5432/subschool" python:3.11-bullseye sh -lc "pip install --no-cache-dir -r requirements.txt >/tmp/pip_seed.log 2>&1 && python scripts/seed_e2e_ui.py"
```
- Full Playwright e2e запускать из локального репозитория с test-domain env (`E2E_*_BASE_URL` на `https://test-*`).

## Production dual-frontend plan (без применения на текущем шаге)
- Прод сейчас не трогаем, но целевая схема уже фиксируется:
  - legacy frontend: `teacher.subschool.us`, `class.subschool.us`, `admin.subschool.us`
  - nuxt beta frontend: `teacher-beta.subschool.us`, `class-beta.subschool.us`, `admin-beta.subschool.us`
  - calls/board общие: `call.subschool.us`, `board.subschool.us` (или текущий board host)
- Релизный порядок для проду:
  1) обновить `apps/web` и пересобрать legacy assets (`subschool_web_builder_prod`);
  2) обновить `apps/web-nuxt`, развернуть `.output`, перезапустить `subschool_frontend_nuxt_*`;
  3) обновить Caddy (добавить `*-beta` site blocks), `caddy validate` + `caddy reload`;
  4) smoke по legacy + beta + API + calls + board;
  5) e2e на beta доменах.

## Current env secrets to seed (rotate for prod)

### 10kQ
- `OPENAI_API_KEY=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`
- `CORS_ALLOWED_ORIGINS=http://127.0.0.1:5188,http://localhost:5188` (в прод: `https://10thousandquestions.com,https://admin.10thousandquestions.com`)
- `SENDPULSE_CLIENT_ID=f7a50dc079e75e92c0d7ec3e29bc3667`
- `SENDPULSE_CLIENT_SECRET=e1be4dd7d4d60257e8669d5b5c7a1026`
- `MAIL_FROM_EMAIL=maksim@subschool.us`
- `MAIL_FROM_NAME=Maksim`
- `DEBUG=1` (в прод поставить `0`)
- DB: заменить дефолт на сильный пароль, юзер `tenkq_app`, хост `tenkq-db:5432` (внутренняя сеть, без публикации порта).

### DatedIn
- `JWT_SECRET_KEY=b0197f1e7b0c4c8dbd928d9b3d5e6f19` (ротация на прод)
- `DATABASE_URL=postgresql+asyncpg://datedin_app:DaT3dIn_p8N4R2vM@datedin-db:5432/datedin`
- `CORS_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]` (в прод: `https://new.datedin.pro`)
- `AZURE_TRANSLATOR_KEY=4iUiH6mmBxFCfsRnxIkqec8YYariderzCDNx3eQ9nKPDSkVyFEIKJQQJ99BIACmepeSXJ3w3AAAbACOGnHfZ`
- `AZURE_TRANSLATOR_REGION=uksouth`
- `AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com`

### SubSchool
- `DATABASE_URL=postgresql+psycopg://subschool_app:SuBSch00l_New_p9X7s2VdQ@subschool-db:5432/subschool`
- `REDIS_URL=redis://:ReDiS_suB_7v9u4w@redis:6379/0`
- `LIVEKIT_API_KEY=lk_prod_1`, `LIVEKIT_API_SECRET=lk_SuB_9q2Xr4v6T8y`
- `LIVEKIT_WS_URL=ws://livekit:7880`, `LIVEKIT_PUBLIC_WS_URL=wss://call.subschool.us`
- `CALLS_BASE_URL=https://call.subschool.us`
- PayPal (prod): `PAYPAL_ENV=live`, `PAYPAL_CLIENT_ID=AbtPq-jqho1uU6qar3dd0aN4HwXrAEctlcYalcUMQ5A3GW9BX8tjar6WnTyTIfOTdMLSNUcaxdag8jtA`, `PAYPAL_SECRET=EBBpYOWeeqVjjrj2AyVTFf7L6VRqmX315RovCx0eno3S3cqg9DL_UBzC1Nj0rs2IUoyBm3Iojcu-78wp`, return/cancel `https://teacher.subschool.us/finances`.
- SendPulse (email): `SENDPULSE_ID=f7a50dc079e75e92c0d7ec3e29bc3667`, `SENDPULSE_SECRET=e1be4dd7d4d60257e8669d5b5c7a1026`, `EMAIL_FROM_NAME=Maksim`, `EMAIL_FROM_EMAIL=maksim@subschool.us`.
- Всё на внутренних сетях без публикации портов.

**Важно:** секреты сюда занесены для оперирования, но перед стартом ротация на прод-значения обязательна; `.env` храним только на сервере, наружу не публикуем DB порты.
