from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework import status, permissions
from rest_framework.response import Response
from django.contrib.auth.models import User

from .models import Book, ReadingProgress, Household, FavouriteBook
from .serializers import BookSerializer, ReadingProgressSerializer, ISBNInputSerializer
from .services import FetchBook
from django.contrib.auth import login
from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from rest_framework import decorators, response
from rest_framework.status import HTTP_201_CREATED, HTTP_200_OK
from rest_framework.viewsets import ViewSet


@api_view(['GET'])
def book_list(request):
    books = Book.objects.filter(
        household=request.user.userprofile.household
    )
    serializer = BookSerializer(
        books,
        many=True,
        context={'request': request}
    )
    return Response(serializer.data)


@api_view(['POST'])
def update_reading_progress(request):
    """
    Create or update reading progress for a book
    """
    book_id = request.data.get('book')
    progress = request.data.get('progress_percent')

    obj, created = ReadingProgress.objects.update_or_create(
        user=request.user,
        book_id=book_id,
        defaults={'progress_percent': progress}
    )

    serializer = ReadingProgressSerializer(obj)
    return Response(serializer.data)

@api_view(['GET'])
def my_reading_progress(request):
    progress = ReadingProgress.objects.filter(user=request.user)
    serializer = ReadingProgressSerializer(progress, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def completed_books(request):
    completed = ReadingProgress.objects.filter(
        user=request.user,
        progress_percent=100
    ).count()

    return Response({
        "completed_books": completed
    })


class LoginAPI(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        # 1. Validate username/password using standard DRF serializer
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 2. If valid, get the user object
        user = serializer.validated_data['user']
        
        # 3. Log the user in (Django session) - required for Knox to generate token
        login(request, user)
        
        # 4. Return the Knox token response
        return super(LoginAPI, self).post(request, format=None)


class AddBookByISBNView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = ISBNInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        isbn = serializer.validated_data["isbn"]
        book_data = FetchBook(isbn).fetch_book_data()
        try:
            if not book_data:
                raise Book.DoesNotExist
            household, _ = Household.objects.get_or_create(name='Sahityika Family')
            book_data["household"] = household
            book = Book.create_or_update_book(book_data)
            print(book)
            return Response(
                {
                    "found": True,
                    "book": BookSerializer(book, context={"request": request}).data
                },
                status=status.HTTP_200_OK
            )
        except Book.DoesNotExist:
            return Response(
                {
                    "found": False,
                    "message": "Book not found with this ISBN"
                },
                status=status.HTTP_404_NOT_FOUND
            )


class BookViewSet(ReadOnlyModelViewSet):
    """
    list:
    Return list of books

    retrieve:
    Return single book details
    """
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = [
        "title",
        "subtitle",
        "isbn_10",
        "isbn_13",
        "categories",
        "publisher",
        "authors__name",
    ]

    def get_queryset(self):
        return (
            Book.objects
            .select_related()
            .prefetch_related("authors")
            .order_by("title")
        )

    @decorators.action(detail=True, methods=["POST"], url_path="favourite")
    def favourite(self, request, pk=None):
        book = self.get_object()
        user = request.user
        params = {'book': book, 'user': user}
        favourite = FavouriteBook.objects.filter(**params)
        if favourite.exists():
            favourite.delete()
            message = 'Book is removed from wishlist'
        else:
            favourite = FavouriteBook.objects.create(**params)
            message = 'Book is added to wishlist'

        serializer = self.get_serializer(
            book, context={"request": request}
        )

        return Response(
            {"messge": message, "data": serializer.data}, status=HTTP_200_OK
        )

    @decorators.action(detail=False, methods=["GET"], url_path="favourite")
    def favourite_book_list(self, request, pk=None):
        user = request.user
        params = {'user': user}
        favourite = FavouriteBook.objects.filter(**params)
        books = Book.objects.filter(id__in=favourite.values_list("book"))
        queryset = self.filter_queryset(books)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class FavouriteBookViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = [
        "title",
        "subtitle",
        "isbn_10",
        "isbn_13",
        "categories",
        "publisher",
        "authors__name",
    ]

    def list(self, request):
        books = Book.objects.filter(favourite__user=request.user)
        serializer = BookSerializer(
            books, many=True, context={"request": request}
        )
        return Response(serializer.data)