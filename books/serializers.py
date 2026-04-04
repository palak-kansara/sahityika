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
    added_by = UserSerializer(read_only=True)

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
            "added_by",
        ]
        read_only_fields = ["id", "created_at", "added_by"]
        extra_kwargs = {
            "household": {"read_only": True},
            "published_date": {"required": False, "allow_null": True},
        }

    def get_is_fav(self, instance):
        user = self.context.get("request", None).user
        return user.favourite.filter(book=instance.id).exists()

    def get_read_id(self, instance):
        user = self.context.get("request", None).user
        read_book = user.reading_progress.filter(book=instance.id).first()
        return read_book.id if read_book else None

    def validate(self, attrs):
        if self.instance is None:
            if not attrs.get('isbn_10') and not attrs.get('isbn_13'):
                raise serializers.ValidationError("Either 'isbn_10' or 'isbn_13' is required.")

        request = self.context.get('request')
        if request and request.method == 'POST':
            # Ensure added_by is set from request.user
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                attrs['added_by'] = user
                household = user.profile.household if hasattr(user, 'profile') else None
                if household:
                    raise serializers.ValidationError("User must belong to a household to add a book.")

                attrs['household'] = household
            else:
                raise serializers.ValidationError("Authentication required to add a book.")
        return attrs

    def create(self, validated_data):
        author_names = validated_data.pop('author_names', [])

        # Create household if an id provided (serializer currently expects PK)
        book = Book.objects.create(**validated_data)

        # Handle authors list
        authors = []
        for name in author_names:
            author, _ = Author.objects.get_or_create(name=name)
            authors.append(author)
        if authors:
            book.authors.set(authors)
        return book


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