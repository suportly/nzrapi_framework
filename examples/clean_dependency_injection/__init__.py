"""
Clean Dependency Injection Example

This example demonstrates Clean Architecture principles applied to the nzrapi framework:

1. **Separation of Concerns**: Each layer has a single responsibility
2. **Dependency Injection**: Proper DI with abstractions and interfaces
3. **Clean Architecture**: Clear boundaries between layers
4. **Error Handling**: Structured exceptions and error responses
5. **Configuration**: Centralized settings management
6. **Type Safety**: Full type hints throughout
7. **Testability**: Easy to test due to proper abstractions

Layers:
- Domain: models/ - Business entities and rules
- Repository: repositories/ - Data access layer with abstractions
- Service: services/ - Business logic layer
- API: api/ - HTTP layer (routes, dependencies)
- Config: Configuration management
"""
