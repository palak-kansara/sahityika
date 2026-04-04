from django.urls import path
from .views import (
    completed_books, AddBookByISBNView, LoginAPI, BookViewSet, ReadingProgressViewSet, ProfileViewSet, BookCreateAPIView,
    CategoryListAPI, PublisherListAPI, AuthorListAPI
)
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r"books", BookViewSet, basename="book")
router.register(r"reading", ReadingProgressViewSet, basename="reading")
router.register(r"profile", ProfileViewSet, basename="profile")

urlpatterns = [
    # path('books/', book_list),
    path('completed-books/', completed_books),
    path("isbn/", AddBookByISBNView.as_view()),
    path("books/add/", BookCreateAPIView.as_view(), name="book-add"),
    path("books/categories/", CategoryListAPI.as_view(), name="book-categories"),
    path("books/publishers/", PublisherListAPI.as_view(), name="book-publishers"),
    path("author/", AuthorListAPI.as_view({'get': 'list'}), name="author-list"),
    path("login/", LoginAPI.as_view(), name="user_login"),

] +  router.urls
