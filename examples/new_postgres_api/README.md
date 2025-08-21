# NzrApi PostgreSQL Example

This is a comprehensive example application built with NzrApi that demonstrates various features including:

- User authentication with JWT
- Role-based access control
- CRUD operations with relationships
- Request validation and serialization
- Database migrations
- API documentation
- Rate limiting
- CORS support
- Request logging
- Health checks

## Features

- **User Management**
  - Registration and authentication
  - Role-based access control (Admin, Manager, Customer)
  - Password hashing

- **Product Catalog**
  - Categories and products
  - Stock management
  - Search and filtering

- **Order System**
  - Shopping cart functionality
  - Order processing workflow
  - Payment integration (stub)

- **API Features**
  - RESTful endpoints
  - Request validation
  - Error handling
  - Pagination and filtering
  - Sorting
  - Search

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
5. Update the `.env` file with your database credentials and other settings

### Database Setup

1. Create a new PostgreSQL database
2. Update the `DATABASE_URL` in `.env`
3. The database tables will be created automatically on first run

### Running the Application

```bash
# Run in development mode with auto-reload
python -m examples.new_postgres_api.main --reload

# Or run with custom host/port
python -m examples.new_postgres_api.main --host 0.0.0.0 --port 8000
```

### Default Admin User

On first run, a default admin user will be created with the following credentials:
- Username: `admin`
- Password: `admin123`

**Important:** Change the default password immediately after first login.

## API Documentation

Once the application is running, you can access the following:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Available Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get access token

### Users

- `GET /api/users` - List all users (admin only)
- `POST /api/users` - Create a new user (admin only)
- `GET /api/users/{user_id}` - Get user details
- `PATCH /api/users/{user_id}` - Update user
- `DELETE /api/users/{user_id}` - Delete user (admin only)

### Categories

- `GET /api/categories` - List all categories
- `POST /api/categories` - Create a new category (admin/manager)
- `GET /api/categories/{category_id}` - Get category details
- `PATCH /api/categories/{category_id}` - Update category (admin/manager)
- `DELETE /api/categories/{category_id}` - Delete category (admin/manager)

### Products

- `GET /api/products` - List all products
- `POST /api/products` - Create a new product (admin/manager)
- `GET /api/products/{product_id}` - Get product details
- `PATCH /api/products/{product_id}` - Update product (admin/manager)
- `DELETE /api/products/{product_id}` - Delete product (admin/manager)

### Orders

- `GET /api/orders` - List user's orders (or all orders for admin)
- `POST /api/orders` - Create a new order
- `GET /api/orders/{order_id}` - Get order details
- `PATCH /api/orders/{order_id}` - Update order status
- `DELETE /api/orders/{order_id}` - Cancel order

### Health Check

- `GET /health` - Application health status

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

This project uses `black` for code formatting and `flake8` for linting.

```bash
# Format code
black .

# Check code style
flake8
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [NzrApi](https://github.com/yourusername/nzrapi)
- Uses [SQLAlchemy](https://www.sqlalchemy.org/) for ORM
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Uvicorn](https://www.uvicorn.org/) as the ASGI server
