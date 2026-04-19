### Задание
Развернуть полноценное веб-приложение с обратным прокси: Nginx → Flask → PostgreSQL + Redis.
Приложение пишется самостоятельно, используется кастомный Dockerfile.
## Что реализовать
1. compose.yaml с четырьмя сервисами:
  - nginx — reverse proxy, порт 80
  - app — Flask-приложение (кастомный Dockerfile на python:3.11-slim)
  - postgres — PostgreSQL 15
  - redis — Redis 7 (кэш)
2. Flask-приложение (app/app.py) — три эндпоинта:
  - GET /  — HTML-страница, выводит имя приложения из переменной APP_NAME
  - GET /visits  — JSON {"total": N, "cached": true/false}  (Redis кэширует на 10 сек)
  - GET /health  — JSON {"status": "ok", "db": "connected", "redis": "connected"}
3. Две изолированные сети:
  - frontend — nginx + app
  - backend — app + postgres + redis  (postgres и redis недоступны снаружи)
5. Именованный том для данных PostgreSQL.
6. Healthcheck для postgres (pg_isready) и redis (redis-cli ping):
app использует depends_on с condition: service_healthy для обоих.
7. .env-файл для всех паролей и настроек:
```
POSTGRES_DB=appdb
POSTGRES_USER=app_user
POSTGRES_PASSWORD=...
REDIS_URL=redis://redis:6379/0
APP_NAME=MyApp
```
## Структура репозитория
```
variant-2/
├── compose.yaml
├── .env.example
├── .gitignore
├── nginx/
│   └── nginx.conf
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── screenshots/
│   ├── main_page.png
│   ├── visits_fresh.png
│   ├── visits_cached.png
│   └── compose_ps.png
└── README.md
```
Команды проверки
``` bash
curl http://localhost/          →  HTML-страница
curl http://localhost/visits    →  {"total": N, "cached": false}
curl http://localhost/visits    →  {"total": N, "cached": true}   (повторный, <10 сек)
curl http://localhost/health    →  {"status":"ok","db":"connected","redis":"connected"}
docker compose ps               →  все 4 контейнера running/healthy
docker network ls               →  видны две отдельные сети
docker compose down && docker compose up -d
curl http://localhost/visits    →  счётчик сохранился (том работает)
```
