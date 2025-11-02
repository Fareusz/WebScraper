
  

# WebScraper — simple Django scraper + API

  

This repository contains a small Django project that scrapes article pages (using Selenium + BeautifulSoup), stores them in PostgreSQL, and exposes a simple REST API.

  

This README includes only the essentials to get the project running and to use the scraper and API.

  

## Prerequisites

  

- Docker (Docker Desktop on Windows/Mac, or Docker Engine on Linux)

- Docker Compose (V2; included with Docker Desktop)

- Git (to clone the repository)

  

## Install project dependencies (optional, for local dev)

  

If you want to run the project without Docker (local development) do the following:

  

```powershell

# create and activate a virtual environment

python -m venv .venv

.venv\Scripts\Activate.ps1 # PowerShell on Windows

# or for bash/mac

source .venv/bin/activate

  

# install dependencies

pip install -r requirements.txt

```

  

Note: The project is intended to run inside Docker; the steps above are optional.

  

## Run with Docker (recommended)

  

1. Build and start services:

  

```powershell

docker compose up --build -d

```

  

2. Verify services are running:

  

```powershell

docker compose ps

```

  

3. Check the health endpoint:

  

```powershell

curl http://localhost:8000/health/

```

  

4. Stop the services:

  

```powershell

docker compose down

```

  

## Run locally (without Docker)

  

1. Configure environment variables if you want to use Postgres; otherwise settings fall back to SQLite.

2. Run migrations and start the dev server:

  

```powershell

cd scraper

python manage.py migrate

python manage.py runserver

```

  

## How to run the scraper

  

The project includes a management command that reads `websites.json` and scrapes articles from each URL.

  

Run it inside the running `web` container:

  

```powershell

docker compose exec web python manage.py scrape_articles

```

  

Or run locally (if dependencies are installed):

  

```powershell

python manage.py scrape_articles

```

  

The command will use Selenium + Chrome (inside the container) where required and save extracted articles to the database.

  

## API endpoints (examples)

  

1) Health

  

```http

GET /health/

```
Example Response: 
```json
{"status": "healthy", "django_version": "5.2.7", "debug": false, "database": "postgresql"}
```

2) List articles

  

```http

GET /articles/

GET /articles/?source=domain.com

```

Example Response: JSON array of article objects (id, title, body, plain_body, published_at, url).

  

3) Article detail

  

```http

GET /articles/{id}/

```

  

Example:

  

```powershell

curl http://localhost:8000/articles/1/

```

  

## Problems and limitations

  

- Scraping is brittle: selectors may not be effective as sites change.

- JavaScript-heavy sites require a real browser (Selenium) which increases resource usage.

- Respect robots.txt and site terms; scraping some sites may be disallowed.

- No built-in rate limiting
