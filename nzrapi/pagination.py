from starlette.requests import Request
from starlette.responses import JSONResponse


class PageNumberPagination:
    limit_query_param = "limit"
    offset_query_param = "offset"
    page_query_param = "page"
    max_limit = 100
    default_limit = 10

    def __init__(self, request: Request):
        self.request = request
        self.page = self.get_page()
        self.limit = self.get_limit()
        self.offset = self.get_offset()

    def get_limit(self) -> int:
        try:
            limit = int(self.request.query_params.get(self.limit_query_param, self.default_limit))
        except (ValueError, TypeError):
            limit = self.default_limit

        if limit <= 0:
            return self.default_limit

        return min(limit, self.max_limit)

    def get_page(self) -> int:
        try:
            page = int(self.request.query_params.get(self.page_query_param, 1))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        return page

    def get_offset(self) -> int:
        return (self.page - 1) * self.limit

    def get_paginated_response(self, data, total_count) -> JSONResponse:
        return JSONResponse({"count": total_count, "page": self.page, "limit": self.limit, "results": data})
