from rest_framework import serializers
from .models import Book, ReadingProgress, Author, FavouriteBook
from django.contrib.auth.models import User
import re


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name"]

class BookSerializer(serializers.ModelSerializer):
    # READ
    authors = AuthorSerializer(many=True, read_only=True)
    is_fav = serializers.SerializerMethodField()

    # WRITE (accept list of author names)
    author_names = serializers.ListField(
        child=serializers.CharField(max_length=255),
        write_only=True,
        required=False
    )

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "isbn",
            "subtitle",

            "authors",
            "author_names",

            "household",

            "isbn_10",
            "isbn_13",

            "categories",
            "description",

            "page_count",
            "language",

            "publisher",
            "published_date",

            "thumbnail",
            "preview_link",
            "info_link",

            "created_at",
            "is_fav",
        ]
        read_only_fields = ["id", "created_at"]
    
    def get_is_fav(self, instance):
        user = self.context.get("request", None).user
        return user.favourite.filter(book=instance.id).exists()


class ReadingProgressSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = ReadingProgress
        fields = [
            "id",
            "book",
            "book_title",
            "progress_percent",
            "last_updated",
        ]


class ISBNInputSerializer(serializers.Serializer):
    isbn = serializers.CharField(max_length=20)

    def validate_isbn(self, value):
        # Remove hyphens/spaces
        clean_isbn = re.sub(r"[-\s]", "", value)

        if not (len(clean_isbn) in [10, 13] and clean_isbn.isdigit()):
            raise serializers.ValidationError("Invalid ISBN format")

        return clean_isbn