import django_filters
from .models import Book, ReadingProgress


class BookFilter(django_filters.FilterSet):
    publisher = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='categories', lookup_expr='icontains')
    language = django_filters.CharFilter(lookup_expr='iexact')
    author = django_filters.CharFilter(field_name='authors__name', lookup_expr='icontains')

    class Meta:
        model = Book
        fields = ['publisher', 'category', 'language', 'author']


class ReadingProgressFilter(django_filters.FilterSet):
    publisher = django_filters.CharFilter(field_name='book__publisher', lookup_expr='icontains')
    category = django_filters.CharFilter(field_name='book__categories', lookup_expr='icontains')
    language = django_filters.CharFilter(field_name='book__language', lookup_expr='iexact')
    author = django_filters.CharFilter(field_name='book__authors__name', lookup_expr='icontains')

    class Meta:
        model = ReadingProgress
        fields = ['publisher', 'category', 'language', 'author']
