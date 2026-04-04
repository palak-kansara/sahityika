import openpyxl
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.urls import path

from .models import Book, Household, UserProfile, ReadingProgress, Author, FavouriteBook


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

    # Include first_name on the add user form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    # Return inline instances even when adding a new User so admin shows userprofile fields on the add page
    def get_inline_instances(self, request, obj=None):
        inline_instances = []
        for inline_class in self.inlines:
            inline = inline_class(self.model, self.admin_site)
            inline_instances.append(inline)
        return inline_instances


# Unregister default User admin and register custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


class BookAdmin(admin.ModelAdmin):
    readonly_fields = ('added_by',)
    actions = ['export_to_excel']
    change_list_template = 'admin/books/book/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-all/', self.admin_site.admin_view(self.export_all), name='books_book_export_all'),
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change):
        if not obj.added_by:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)

    def export_all(self, request):
        queryset = Book.objects.all()
        return self._build_excel_response(queryset)

    def _build_excel_response(self, queryset):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Books'

        ws.append([
            'ID', 'Title', 'Subtitle', 'Authors', 'Publisher', 'Published Date',
            'ISBN-10', 'ISBN-13', 'Categories', 'Language', 'Page Count',
            'Description', 'Household', 'Added By', 'Created At',
        ])

        for book in queryset.prefetch_related('authors').select_related('household', 'added_by'):
            ws.append([
                book.id,
                book.title,
                book.subtitle,
                ', '.join(a.name for a in book.authors.all()),
                book.publisher,
                str(book.published_date) if book.published_date else '',
                book.isbn_10,
                book.isbn_13,
                book.categories,
                book.language,
                book.page_count,
                book.description,
                str(book.household) if book.household else '',
                str(book.added_by) if book.added_by else '',
                book.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="books.xlsx"'
        wb.save(response)
        return response

    @admin.action(description='Export selected books to Excel')
    def export_to_excel(self, request, queryset):
        return self._build_excel_response(queryset)


admin.site.register(Book, BookAdmin)
admin.site.register(Author)
admin.site.register(Household)
# UserProfile is now edited inline on the User admin, so don't register it separately
admin.site.register(ReadingProgress)
admin.site.register(FavouriteBook)
