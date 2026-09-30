from rest_framework.pagination import PageNumberPagination

class Pagination10(PageNumberPagination):
    page_size = 10

class Pagination6(PageNumberPagination):
    page_size = 6

class Pagination4(PageNumberPagination):
    page_size = 4

class Pagination3(PageNumberPagination):
    page_size = 3
