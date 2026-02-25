from django.urls import path
from .views import (
    book_list,
    update_reading_progress,
    my_reading_progress,
    completed_books, AddBookByISBNView, LoginAPI, BookViewSet
)
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r"books", BookViewSet, basename="book")

urlpatterns = [
    # path('books/', book_list),
    path('progress/', update_reading_progress),
    path('my-progress/', my_reading_progress),
    path('completed-books/', completed_books),
    path("isbn/", AddBookByISBNView.as_view()),
    path("login/", LoginAPI.as_view(), name="user_login"),
    
] +  router.urls
