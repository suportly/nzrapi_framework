# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - Current Release

### Changed
- Updated test infrastructure to use httpx.AsyncClient with ASGITransport

### Fixed
- Fixed ID parameter type conversion from string to integer in views (`nzrapi/views.py`)
- Fixed PostgreSQL type mismatch errors when querying by ID
- Fixed database schema synchronization by adding drop/recreate logic
- Fixed test async function decorators with `@pytest.mark.asyncio`
- Fixed dependency injection issues in tests by using proper ASGI client setup

### Added
- Enhanced type safety system with automatic parameter validation
- Advanced dependency injection system
- Comprehensive test coverage for type safety features
- Database table recreation logic for schema updates

## [0.2.0] - Previous Release

### Added
- Initial NzrApi framework implementation
- Advanced routing system with type safety
- Database ORM integration with SQLAlchemy
- Security schemes and JWT authentication
- WebSocket support
- Middleware system
- OpenAPI schema generation
- MCP (Model Context Protocol) support
- CLI tools and utilities

### Features
- Modern async framework for AI APIs
- Advanced type safety and validation
- Comprehensive middleware support
- Database migrations and schema management
- Security and authentication systems
- WebSocket real-time communication
- Auto-generated API documentation
- Development and testing utilities