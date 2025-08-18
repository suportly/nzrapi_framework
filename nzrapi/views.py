from typing import Any, Callable, Type

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, Response

from . import settings
from .db.manager import Repository
from .db.models import Model
from .decorators import transactional
from .exceptions import NotFound, PermissionDenied, ValidationError
from .filters import OrderingFilter, SearchFilter
from .pagination import PageNumberPagination
from .permissions import AllowAny
from .requests import Request
from .serializers import BaseSerializer
from .status import status


class APIView:
    permission_classes = [AllowAny]
    request: Request
    kwargs: dict

    @classmethod
    def as_view(cls, **initkwargs) -> Callable:
        async def view(request: Request, **kwargs):
            self = cls(**initkwargs)
            self.request = request
            self.kwargs = kwargs
            return await self.dispatch(request, **kwargs)

        return view

    async def dispatch(self, request: Request, **kwargs) -> Response:
        await self.check_permissions(request)
        try:
            handler = getattr(self, request.method.lower())
        except AttributeError:
            handler = self.http_method_not_allowed
        return await handler(request, **kwargs)

    async def check_permissions(self, request: Any):
        for permission_class in self.permission_classes:
            permission = permission_class()
            if not await permission.has_permission(request, self):
                raise PermissionDenied()

    async def http_method_not_allowed(self, request: Request, **kwargs):
        return JSONResponse({"detail": "Method not allowed"}, status_code=status.HTTP_405_METHOD_NOT_ALLOWED)


class GenericAPIView(APIView):
    model_class: Type[Model] = None
    serializer_class: Type[BaseSerializer] = None
    lookup_field = "id"
    lookup_url_kwarg = None
    pagination_class = settings.DEFAULT_PAGINATION_CLASS
    filter_backends = settings.DEFAULT_FILTER_BACKENDS

    def get_model_class(self) -> Type[Model]:
        assert self.model_class is not None, (
            f"'{self.__class__.__name__}' should either include a `model_class` attribute, "
            f"or override the `get_model_class()` method."
        )
        return self.model_class

    def get_repository(self, session: AsyncSession) -> Repository:
        return Repository(session, self.get_model_class())

    async def get_object(self, session: AsyncSession) -> Model:
        repository = self.get_repository(session)
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        instance = await repository.find_one(filters=filter_kwargs)

        if instance is None:
            raise NotFound()
        return instance

    def get_serializer(self, *args, **kwargs) -> BaseSerializer:
        serializer_class = self.get_serializer_class()
        kwargs.setdefault("context", self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self) -> Type[BaseSerializer]:
        assert self.serializer_class is not None, (
            f"'{self.__class__.__name__}' should either include a `serializer_class` attribute, "
            f"or override the `get_serializer_class()` method."
        )
        return self.serializer_class

    def get_serializer_context(self) -> dict:
        return {"request": self.request}


# --- Mixins ---


class CreateModelMixin:
    get_serializer: Callable[..., BaseSerializer]

    @transactional
    async def post(self, request: Request, session: AsyncSession = None, **kwargs):
        serializer = self.get_serializer(data=await request.json())
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return JSONResponse(e.details["errors"], status_code=status.HTTP_400_BAD_REQUEST)

        await self.perform_create(serializer, session)
        headers = self.get_success_headers(serializer.data)
        return JSONResponse(serializer.data, status_code=status.HTTP_201_CREATED, headers=headers)

    async def perform_create(self, serializer: BaseSerializer, session: AsyncSession):
        await serializer.save(session=session)

    def get_success_headers(self, data: dict) -> dict:
        return {}


class ListModelMixin:
    get_repository: Callable[..., Repository]
    get_serializer: Callable[..., BaseSerializer]
    filter_backends: list
    pagination_class: Type[PageNumberPagination]

    def filter_queryset(self, backends):
        filter_kwargs = {}
        ordering_args = []
        filter_expressions = []

        for backend_class in backends:
            backend = backend_class()
            # Explicitly check for filter types to avoid conflicts
            if isinstance(backend, SearchFilter):
                expressions = backend.filter_queryset(self.request, self)
                if expressions:
                    filter_expressions.extend(expressions)
            elif isinstance(backend, OrderingFilter):
                orders = backend.filter_queryset(self.request, self)
                if orders:
                    ordering_args.extend(orders)
            else:  # Default case for dict-based filters
                result = backend.filter_queryset(self.request, self)
                if isinstance(result, dict):
                    filter_kwargs.update(result)

        return filter_kwargs, ordering_args, filter_expressions

    @transactional
    async def get(self, request: Request, session: AsyncSession = None, **kwargs):
        repository = self.get_repository(session)
        filter_kwargs, ordering_args, filter_expressions = self.filter_queryset(self.filter_backends)

        if self.pagination_class:
            paginator = self.pagination_class(request)
            results = await repository.find(
                filters=filter_kwargs,
                filter_expressions=filter_expressions,
                limit=paginator.limit,
                offset=paginator.offset,
                order_by_args=ordering_args,
            )
            total_count = await repository.count(filters=filter_kwargs, filter_expressions=filter_expressions)
            serializer = self.get_serializer(results, many=True)
            return paginator.get_paginated_response(serializer.data, total_count)

        # No pagination
        results = await repository.find(
            filters=filter_kwargs, filter_expressions=filter_expressions, order_by_args=ordering_args
        )
        serializer = self.get_serializer(results, many=True)
        return JSONResponse(serializer.data)


class RetrieveModelMixin:
    get_object: Callable[..., Any]
    get_serializer: Callable[..., BaseSerializer]

    @transactional
    async def get(self, request: Request, session: AsyncSession = None, **kwargs):
        instance = await self.get_object(session)
        serializer = self.get_serializer(instance)
        return JSONResponse(serializer.data)


class UpdateModelMixin:
    get_object: Callable[..., Any]
    get_serializer: Callable[..., BaseSerializer]

    @transactional
    async def put(self, request: Request, session: AsyncSession = None, **kwargs):
        instance = await self.get_object(session)
        serializer = self.get_serializer(instance, data=await request.json())
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return JSONResponse(e.details["errors"], status_code=status.HTTP_400_BAD_REQUEST)

        await self.perform_update(serializer, session)
        return JSONResponse(serializer.data)

    async def perform_update(self, serializer: BaseSerializer, session: AsyncSession):
        await serializer.save(session=session)


class DestroyModelMixin:
    get_object: Callable[..., Any]
    get_repository: Callable[..., Repository]

    @transactional
    async def delete(self, request: Request, session: AsyncSession = None, **kwargs):
        instance = await self.get_object(session)
        await self.perform_destroy(instance, session)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    async def perform_destroy(self, instance: Any, session: AsyncSession):
        repository = self.get_repository(session)
        await repository.delete(instance)


# --- Concrete Views ---


class CreateAPIView(CreateModelMixin, GenericAPIView):
    pass


class ListAPIView(ListModelMixin, GenericAPIView):
    pass


class ListCreateAPIView(ListModelMixin, CreateModelMixin, GenericAPIView):
    pass


class RetrieveAPIView(RetrieveModelMixin, GenericAPIView):
    pass


class DestroyAPIView(DestroyModelMixin, GenericAPIView):
    pass


class UpdateAPIView(UpdateModelMixin, GenericAPIView):
    pass


class RetrieveUpdateAPIView(RetrieveModelMixin, UpdateModelMixin, GenericAPIView):
    pass


class RetrieveDestroyAPIView(RetrieveModelMixin, DestroyModelMixin, GenericAPIView):
    pass


class RetrieveUpdateDestroyAPIView(RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericAPIView):
    pass
