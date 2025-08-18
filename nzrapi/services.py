from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    """
    Base class for services.

    Services are used to encapsulate business logic, keeping it separate
    from the views. A service is typically initialized with a database
    session to perform its operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
