# {{ project_name }}

{{ description }}

This project is built with the **NzrApi Framework**, a modern Python framework for building high-performance APIs.

## Features

- 🚀 **High Performance**: Based on Starlette and Uvicorn for async/await performance.
- 📦 **Simplified Template**: A clean and generic starting point for any API.
- 🛡️ **Production Ready**: Includes rate limiting, optional authentication, and monitoring.
- 🗄️ **Database Integration**: Pre-configured with SQLAlchemy for async database access.
- 🐳 **Docker Ready**: Comes with a `Dockerfile` and `docker-compose.yml` for easy deployment.
- ⚙️ **Easy to Customize**: Designed to be easily extended with your own logic.

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
```

### 2. Configuration

Update `.env` with your settings, such as the `DATABASE_URL`:

```
DATABASE_URL="sqlite+aiosqlite:///./{{ project_name }}.db"
```

### 3. Run the Server

```bash
# Development mode with auto-reload
python main.py

# Or using the nzrapi CLI
nzrapi run --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`.

## API Endpoints

This template includes the following example endpoints:

### Root

- `GET /`

  Returns a welcome message.

### Items

- `GET /items/{item_id}`

  Retrieves a sample item by its ID.

- `POST /items`

  Creates a new item. 

  **Request Body:**
  ```json
  {
    "name": "New Item",
    "description": "A description for the new item."
  }
  ```

## Database Migrations

This template uses Alembic for database migrations, managed via the `nzrapi` CLI.

```bash
# Generate a new migration script
nzrapi migrate -m "Add items table"

# Apply migrations to the database
nzrapi migrate --upgrade

# Rollback the last migration
nzrapi migrate --downgrade -1
```

## Docker Deployment

```bash
# Build the Docker image
docker build -t {{ project_name }} .

# Run the container
docker run -p 8000:8000 --env-file .env {{ project_name }}

# Using Docker Compose (recommended)
docker-compose up -d
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode and auto-reloading. | `false` |
| `DATABASE_URL` | The connection URL for the database. | `sqlite+aiosqlite:///./app.db` |
| `HOST` | The host on which the server will listen. | `0.0.0.0` |
| `PORT` | The port on which the server will listen. | `8000` |
| `RATE_LIMIT_PER_MINUTE` | Max requests per minute. | `60` |
| `RATE_LIMIT_PER_HOUR` | Max requests per hour. | `1000` |
{% if include_auth %}
| `SECRET_KEY` | A secret key for signing JWTs. | Required if auth is enabled. |
{% endif %}

## Monitoring

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)


## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# With coverage
pytest --cov=.
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

- **Documentation**: [NzrApi Framework Docs](https://nzrapi.readthedocs.io)
- **Issues**: [GitHub Issues](https://https://github.com/suportly/nzrapi_framework/issues)
- **Community**: [Discord Server](https://discord.gg/nzrapi)

---

Built with ❤️ using [NzrApi Framework](https://github.com/suportly/nzrapi_framework)
