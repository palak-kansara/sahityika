from django.urls import path
from .views import (
    completed_books, AddBookByISBNView, LoginAPI, BookViewSet, ReadingProgressViewSet, ProfileViewSet
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
    path("login/", LoginAPI.as_view(), name="user_login"),

] +  router.urls
