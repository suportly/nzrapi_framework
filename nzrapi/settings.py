from .filters import OrderingFilter, QueryParameterFilterBackend, SearchFilter
from .pagination import PageNumberPagination

DEFAULT_PAGINATION_CLASS = PageNumberPagination
DEFAULT_FILTER_BACKENDS = [
    QueryParameterFilterBackend,
    OrderingFilter,
    SearchFilter,
]
