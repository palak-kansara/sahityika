from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework import status, permissions
from rest_framework.response import Response
from django.contrib.auth.models import User

from .models import Book, ReadingProgress, Household, FavouriteBook, UserProfile, Author
from .serializers import BookSerializer, ReadingProgressSerializer, ISBNInputSerializer, UserProfileSerializer, \
    AuthorSerializer
from .services import FetchBook
from django.contrib.auth import login
from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from rest_framework import decorators
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ViewSet
from rest_framework.generics import CreateAPIView


class ProfileViewSet(ViewSet):
    """ViewSet that returns the authenticated user's profile.

    list: returns the requesting user's profile (mounted at /profile/)
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user

        try:
            profile = user.userprofile
        except UserProfile.DoesNotExist:
            # If no profile exists, return basic user info
            return Response({"user": {"id": user.id, "first_name": user.first_name}})

        serializer = UserProfileSerializer(profile, context={"request": request})
        return Response(serializer.data)


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
            book_data["added_by"] = request.user
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


class BookCreateAPIView(CreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticated]


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
            .order_by("-created_at")
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

    @decorators.action(detail=False, methods=["GET"], url_path="read_list")
    def read_book_list(self, request, pk=None):
        user = request.user
        params = {'user': user}
        favourite = ReadingProgress.objects.filter(**params)
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


class ReadingProgressViewSet(ModelViewSet):
    serializer_class = ReadingProgressSerializer
    permission_classes = [IsAuthenticated]
    search_fields = [
        "book__title",
        "book__subtitle",
        "book__isbn_10",
        "book__isbn_13",
        "book__categories",
        "book__publisher",
        "book__authors__name",
    ]

    def get_queryset(self):
        return (
            ReadingProgress.objects
            .filter(user=self.request.user)
            .select_related("book")
            .prefetch_related("book__authors")
            .order_by("-last_updated")
        )

class AuthorListAPI(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["name"]
    serializer_class = AuthorSerializer

    def get_queryset(self):
        return Author.objects.order_by("name")


class CategoryListAPI(APIView):
    """Return unique categories (split on commas) present in Book.categories."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Book.objects.values_list('categories', flat=True)
        cats = set()
        for val in qs:
            if not val:
                continue
            for part in val.split(','):
                p = part.strip()
                if p:
                    cats.add(p)
        return Response(sorted(cats))


class PublisherListAPI(APIView):
    """Return unique non-empty publishers present in Book.publisher."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Book.objects.values_list('publisher', flat=True).exclude(publisher__isnull=True)
        pubs = {p.strip() for p in qs if p and p.strip()}
        return Response(sorted(pubs))
