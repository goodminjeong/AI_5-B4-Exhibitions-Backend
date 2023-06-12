from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    PAGE_SIZE = 9

    def get_paginated_response(self, data):
        return [
            ("count", self.page.paginator.count),
            ("next", self.get_next_link()),
            ("previous", self.get_previous_link()),
            ("results", data),
        ]
