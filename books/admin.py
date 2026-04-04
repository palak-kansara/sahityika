from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

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

admin.site.register(Book)
admin.site.register(Author)
admin.site.register(Household)
# UserProfile is now edited inline on the User admin, so don't register it separately
admin.site.register(ReadingProgress)
admin.site.register(FavouriteBook)
