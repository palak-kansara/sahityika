from rest_framework import serializers
from .models import Book, ReadingProgress, Author, FavouriteBook, Household, UserProfile
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

class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ["id", "name"]


class UserProfileSerializer(serializers.ModelSerializer):
    household = HouseholdSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ["id", "full_name", "household"]


class BookSerializer(serializers.ModelSerializer):
    # READ
    authors = AuthorSerializer(many=True, read_only=True)
    is_fav = serializers.SerializerMethodField()
    read_id = serializers.SerializerMethodField()

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
            "read_id",
        ]
        read_only_fields = ["id", "created_at"]
    
    def get_is_fav(self, instance):
        user = self.context.get("request", None).user
        return user.favourite.filter(book=instance.id).exists()

    def get_read_id(self, instance):
        user = self.context.get("request", None).user
        read_book = user.reading_progress.filter(book=instance.id).first()
        return read_book.id if read_book else None



class ReadingProgressSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
        source="book",
        write_only=True
    )

    class Meta:
        model = ReadingProgress
        fields = [
            "id",
            "book",
            "book_id",
            "pages_read",
            "progress_percent",
            "last_updated",
        ]
        read_only_fields = ["progress_percent", "last_updated"]

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user
        book = attrs.get("book")

        # Only check on create
        if self.instance is None:
            read_book = ReadingProgress.objects.filter(
                user=user,
                book=book)
            if read_book.exists():
                raise serializers.ValidationError(
                    "Book already in reading list"
                )
        attrs["user"] = user
        return attrs



class ISBNInputSerializer(serializers.Serializer):
    isbn = serializers.CharField(max_length=20)

    def validate_isbn(self, value):
        # Remove hyphens/spaces
        clean_isbn = re.sub(r"[-\s]", "", value)

        if not (len(clean_isbn) in [10, 13] and clean_isbn.isdigit()):
            raise serializers.ValidationError("Invalid ISBN format")

        return clean_isbn