from django.contrib import admin
from .models import Book, Household, UserProfile, ReadingProgress, Author, FavouriteBook

admin.site.register(Book)
admin.site.register(Author)
admin.site.register(Household)
admin.site.register(UserProfile)
admin.site.register(ReadingProgress)
admin.site.register(FavouriteBook)
