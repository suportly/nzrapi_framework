from .requests import Request


class BaseFilterBackend:
    def filter_queryset(self, request: Request, view):
        raise NotImplementedError(".filter_queryset() must be implemented.")


class QueryParameterFilterBackend(BaseFilterBackend):
    """
    A filter backend that uses query parameters to filter the queryset.
    It filters based on the `filterset_fields` attribute of the view.
    """

    def filter_queryset(self, request: Request, view) -> dict:
        filter_kwargs = {}
        if hasattr(view, "filterset_fields"):
            for field in view.filterset_fields:
                if value := request.query_params.get(field):
                    filter_kwargs[field] = value
        return filter_kwargs


class SearchFilter(BaseFilterBackend):
    search_param = "search"

    def filter_queryset(self, request: Request, view):
        search_term = request.query_params.get(self.search_param)
        if not search_term or not hasattr(view, "search_fields"):
            return []

        from sqlalchemy import or_

        search_fields = view.search_fields
        model = view.get_model_class()

        search_conditions = []
        for field_name in search_fields:
            field = getattr(model, field_name, None)
            if field:
                search_conditions.append(field.ilike(f"%{search_term}%"))

        if search_conditions:
            return [or_(*search_conditions)]
        return []


class OrderingFilter(BaseFilterBackend):
    """
    A filter backend that handles ordering of the queryset.
    """

    ordering_param = "ordering"

    def filter_queryset(self, request: Request, view):
        params = request.query_params.get(self.ordering_param)
        if not params:
            return []

        fields = [param.strip() for param in params.split(",")]
        ordering_fields = getattr(view, "ordering_fields", [])
        validated_ordering = []

        for field in fields:
            is_desc = field.startswith("-")
            field_name = field[1:] if is_desc else field

            if field_name in ordering_fields:
                column = getattr(view.model_class, field_name, None)
                if column:
                    if is_desc:
                        validated_ordering.append(column.desc())
                    else:
                        validated_ordering.append(column.asc())

        return validated_ordering
