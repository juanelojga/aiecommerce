# AI Ecommerce Project

Django-based ecommerce application with PostgreSQL and Redis support.

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Git

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd django-projects
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration settings. The Docker setup uses default ports (8000 for Web, 5432 for Postgres, 6379 for Redis), but you can change these if they conflict with your host machine.

### 3. Start Docker Environment (Recommended)

This project includes a fully containerized development environment using Docker Compose. When started, it will automatically run migrations and create a superuser based on your `.env` file settings.

```bash
# Build and start the containers in the background
docker compose up -d --build

# View logs to ensure everything started correctly
docker compose logs -f
```

The application will be available at `http://localhost:<WEB_PORT>` (default: `8000`).

### Alternative: Local Setup (Without Docker)

If you prefer to run the project locally without Docker:

1. Install [uv](https://docs.astral.sh/uv/) if you haven't already.
2. Install dependencies (creates `.venv/` automatically):
   ```bash
   uv sync
   ```
3. Run migrations and create a superuser:
   ```bash
   uv run python manage.py migrate
   uv run python manage.py createsuperuser
   ```
4. Start the development server:
   ```bash
   uv run python manage.py runserver
   ```

## Common Commands

### Running Commands in Docker

When using the Docker environment, you should run management commands inside the `web` container:

```bash
# Run Django management commands
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# Open a Django shell
docker compose exec web python manage.py shell

# Run tests
docker compose exec web pytest
```

### Dependency Management

Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`. Use uv to add or update them:

```bash
# Add a runtime dependency
uv add <package>

# Add a dev/test dependency
uv add --dev <package>

# Upgrade everything to latest allowed versions
uv lock --upgrade

# Rebuild the Docker container to pick up the new lock
docker compose up -d --build
```

### Docker Commands Quick Reference

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Stop services and remove volumes (WARNING: This deletes your database!)
docker compose down -v

# View logs
docker compose logs -f

# Restart services
docker compose restart

# Rebuild containers
docker compose up -d --build

# Access database container (psql)
docker compose exec db psql -U myproject_user -d myproject_db
```

Project Structure

```
django-projects/
├── aiecommerce/        # Django project settings
├── .venv/              # Virtual environment (uv-managed)
├── docker-compose.yml  # Docker services configuration
├── manage.py           # Django management script
├── pyproject.toml      # Python dependencies + tool config
├── uv.lock             # Fully-pinned dependency lockfile
├── .env                # Environment variables
└── .gitignore          # Git ignore rules
```

## Development Workflow

1. Sync dependencies: `uv sync`
2. Start Docker services: `docker compose up -d`
3. Run migrations: `uv run python manage.py migrate`
4. Start development server: `uv run python manage.py runserver`
5. Make changes and test
6. Add dependencies as needed with `uv add <pkg>` / `uv add --dev <pkg>`

## Troubleshooting

### Database Connection Issues

- Ensure Docker containers are running: `docker-compose ps`
- Check environment variables in file `.env`
- Verify database credentials match in and `.env``docker-compose.yml`

### Port Already in Use

- Change the port in or file `docker-compose.yml``.env`
- Or stop the service using the port

### Migration Errors

- Try resetting migrations (development only!)
- Ensure a database is running
- Check for circular dependencies in models

### Code Quality & Tooling

This project uses Ruff (linting/formatting) and Mypy (static typing). These run automatically on git commit, but you can run them manually:

```bash
# Format code and fix linting errors
uv run ruff format .
uv run ruff check . --fix

# Run type checking
uv run mypy .
```

## Testing

Development dependencies are installed as part of `uv sync`. Run the suite with:

```bash
# Run all tests
uv run pytest

# Run tests for a specific file
uv run pytest aiecommerce/tests/test_models.py
```

## Mercado Libre Integration

For detailed information on setting up and verifying the Mercado Libre integration, see the following guides:

- [HTTPS Setup for Local Development](docs/README_HTTPS.md) - Required for OAuth2 callbacks.
- [Verifying Credentials and Tokens](docs/mercadolibre-verification.md) - Example of how to verify the API handshake.

## API Authentication

All `/api/v1/` endpoints are protected by two security layers:

### 1. API Key (Header-Based)

Every request must include a valid `X-API-KEY` header:

```bash
curl -H "X-API-KEY: your-secret-key" http://localhost:8000/api/v1/...
```

Set the key in your `.env` file:

```dotenv
API_KEY=your-secret-api-key-here
```

- **Missing key**: Falls through to session authentication (for Django admin / browsable API).
- **Invalid key**: Returns `403 Forbidden`.
- **Empty `API_KEY` setting**: All API-key requests are rejected (fail-secure).

### 2. IP Whitelisting

Restrict API access to specific IP addresses or CIDR ranges:

```dotenv
# Single IPs and CIDR ranges, comma-separated
API_ALLOWED_IPS=203.0.113.5,10.0.0.0/8,::1
```

- **Empty list**: All IPs are allowed (convenient for local development).
- Supports IPv4, IPv6, and CIDR notation.

For full details, see [API Authentication Documentation](docs/api-authentication.md).

## License

[Specify your license here]

## Contributing

[Add contribution guidelines here]

## Management Commands: Scraping and Price List

This project includes custom Django management commands to scrape product data and sync price lists.

### 1) Scrape Tecnomega

Fetches product data from Tecnomega and stores raw rows in the database.

- Command:

```bash
python manage.py scrape_tecnomega [--categories <terms...>] [--dry-run]
```

- Arguments:
  - `--categories`: One or more search terms/categories to scrape. Defaults to `notebook` if omitted. Example: `notebook monitor "tarjeta video"`.
  - `--dry-run`: If set, only the first 5 items per category are printed to stdout and nothing is saved to the database.

- Example usages:

```bash
# Example from docs: multiple categories + dry-run
python manage.py scrape_tecnomega --categories notebook monitor "tarjeta video" --dry-run

# Scrape and persist results (no dry-run)
python manage.py scrape_tecnomega --categories notebook monitor

# Use the default category (notebook)
python manage.py scrape_tecnomega
```

- Notes:
  - The command relies on a base URL configured via Django settings `STOCK_LIST_BASE_URL`. Ensure it is set in your environment (e.g., in `.env`) and loaded in `aiecommerce/settings.py`.
  - In `--dry-run` mode, the command logs a preview of up to 5 items per category and does not write to the database.
  - Without `--dry-run`, scraped rows are bulk-inserted as `ProductRawWeb` entries with a shared session ID and the `search_term` set to the category.

### 2) Sync Price List

Synchronizes processed price list information from the scraped data.

- Command:

```bash
python manage.py sync_price_list
```

- Example usage:

```bash
# Run with the active virtual environment
python manage.py sync_price_list
```

- Notes:
  - Ensure you have already scraped data (e.g., via `scrape_tecnomega`) before running this command so there is data to process.
  - Review environment variables in `.env` as required by your setup.

### 3) Enrich Products

Enriches product master records by scraping for missing details (like SKU) and generating structured specifications using AI. For a detailed guide, see the [AI Content Pipeline Documentation](docs/mercadolibre/ai_content_pipeline.md).

- **Command:**

```bash
python manage.py enrich_products [--force] [--delay <seconds>] [--dry-run]
```

- **Arguments:**
  - `--force`: Forces reprocessing of products that already have specs.
  - `--delay`: Delay in seconds between processing each product. Defaults to `0.5`.
  - `--dry-run`: Performs API calls without saving to the database.

- **Example usages:**

```bash
# Enrich all products missing specs
python manage.py enrich_products

# Force reprocessing of all products with a 2-second delay
python manage.py enrich_products --force --delay 2
```

### 4) Refresh Product Images

Discards a single product's current images (DB rows + S3 objects under
`products/<code>/`) and enqueues the high-resolution image pipeline to
rebuild them. Also available as a REST endpoint at
`POST /api/v1/products/{id}/refresh-images/`. See the
[Image Refresh guide](docs/mercadolibre/image_refresh.md) for full details.

- **Command:**

```bash
python manage.py refresh_product_images <product_code>
```

Requires a running Celery worker; the command returns immediately with the
queued task id.
