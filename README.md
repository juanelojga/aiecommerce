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

## License
[Specify your license here]
## Contributing
[Add contribution guidelines here]