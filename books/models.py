from django.db import models
from django.contrib.auth.models import User


class Household(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)

    authors = models.ManyToManyField(
        Author,
        related_name="books",
        blank=True
    )

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="books",
        null=True,
        blank=True
    )

    isbn_10 = models.CharField(max_length=10, blank=True)
    isbn_13 = models.CharField(max_length=13, blank=True)

    categories = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma separated categories"
    )

    description = models.TextField(blank=True)

    page_count = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=10, blank=True)

    publisher = models.CharField(max_length=255, blank=True)
    published_date = models.DateField(null=True, blank=True)

    thumbnail = models.URLField(blank=True)
    preview_link = models.URLField(blank=True)
    info_link = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    def isbn(self):
        return self.isbn_10 or self.isbn_13

    @classmethod
    def create_or_update_book(cls, data):
        # Prefer ISBN-13 for uniqueness
        lookup = {}
        if data["isbn_13"]:
            lookup["isbn_13"] = data["isbn_13"]
        elif data["isbn_10"]:
            lookup["isbn_10"] = data["isbn_10"]
        else:
            lookup["title"] = data["title"]

        book, created = Book.objects.update_or_create(
            **lookup,
            defaults={
                "title": data["title"],
                "subtitle": data["subtitle"],
                "isbn_10": data["isbn_10"],
                "isbn_13": data["isbn_13"],
                "categories": data["categories"],
                "description": data["description"],
                "page_count": data["page_count"],
                "language": data["language"],
                "publisher": data["publisher"],
                "published_date": data["published_date"],
                "thumbnail": data["thumbnail"],
                "preview_link": data["preview_link"],
                "info_link": data["info_link"],
                "household": data["household"]
            },
        )

        # Handle authors (M2M)
        authors = []
        for name in data["authors"]:
            author, _ = Author.objects.get_or_create(name=name)
            authors.append(author)

        book.authors.set(authors)

        return book


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    household = models.ForeignKey(
        Household,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.user.username

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip()


class ReadingProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reading_progress")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reading_progress")
    pages_read = models.PositiveIntegerField(default=0)
    progress_percent = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'book')

    def save(self, *args, **kwargs):
        if self.book.page_count:
            self.progress_percent = int(
                (self.pages_read / self.book.page_count) * 100
            )
        else:
            self.progress_percent = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.progress_percent}%)"


class FavouriteBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favourite")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="favourite")

    def __str__(self):
         return f"{self.user.username} - {self.book.title}"