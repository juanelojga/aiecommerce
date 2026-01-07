# AI Ecommerce Project

Django-based ecommerce application with PostgreSQL and Redis support.

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Git

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url> cd django-projects
```

### 2. Set Up Virtual Environment

Create and activate a virtual environment:
Create virtual environment

```
python3 -m venv venv
```

Activate virtual environment

```
source venv/bin/activate # On Linux/macOS
venv\Scripts\activate # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

- Environment Configuration

Copy the example environment file and configure it:``` bash

```
cp .env.example .env
```

Edit the.env file with your configuration settings.

- Start Docker Services

Start PostgreSQL and Redis containers:

``` bash
docker-compose up -d
```

To stop the services:

``` bash
docker-compose down
```

To view logs:

``` bash
docker-compose logs -f
```

- Run Database Migrations

``` bash
python manage.py migrate
```

- Create Superuser

Create an admin account:

``` bash
python manage.py createsuperuser
```

- Run Development Server

``` bash
python manage.py runserver
```

The application will be available at http://127.0.0.1:8000/
Admin panel: http://127.0.0.1:8000/admin/

Common Commands
Django Management

``` bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run on specific port
python manage.py runserver 8080

# Collect static files
python manage.py collectstatic

# Run Django shell
python manage.py shell
```

Dependency Management
``` bash
# Install new package
pip install <package-name>

# Update requirements.txt
pip freeze > requirements.txt

# Install from requirements.txt
pip install -r requirements.txt
```

Docker Commands
``` bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Rebuild containers
docker-compose up -d --build

# Access database container
docker-compose exec db psql -U $POSTGRES_USER -d $POSTGRES_DB
```

Virtual Environment
``` bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Deactivate virtual environment
deactivate
```

Project Structure
```
django-projects/
├── aiecommerce/        # Django project settings
├── venv/               # Virtual environment
├── docker-compose.yml  # Docker services configuration
├── manage.py           # Django management script
├── requirements.txt    # Python dependencies
├── .env                # Environment variables
└── .gitignore          # Git ignore rules
```

## Development Workflow
1. Activate virtual environment: `source venv/bin/activate`
2. Start Docker services: `docker-compose up -d`
3. Run migrations: `python manage.py migrate`
4. Start development server: `python manage.py runserver`
5. Make changes and test
6. Update requirements if needed: `pip freeze > requirements.txt`

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

``` bash
# Format code and fix linting errors
ruff format .
ruff check . --fix

# Run type checking
mypy .
```

## Testing

To run the test suite, first ensure all development dependencies are installed:

```bash
pip install -r requirements-dev.txt
```

Then, you can execute tests using `pytest`:

```bash
# Run all tests
venv/bin/python -m pytest

# Run tests for a specific file
venv/bin/python -m pytest aiecommerce/tests/test_models.py
```

One last tip for you
Since you installed these packages manually, remember to freeze them into a requirements file so you don't lose track of them:

``` bash
pip freeze > requirements.txt
```

## Mercado Libre Integration

For detailed information on setting up and verifying the Mercado Libre integration, see the following guides:

- [HTTPS Setup for Local Development](docs/README_HTTPS.md) - Required for OAuth2 callbacks.
- [Verifying Credentials and Tokens](docs/mercadolibre-verification.md) - Example of how to verify the API handshake.

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
