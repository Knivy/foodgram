from django.contrib import admin  # type: ignore
from django.contrib.auth.admin import UserAdmin  # type: ignore

from users.models import UserWithSubscriptions

UserAdmin.fieldsets += (
    ('Extra Fields', {'fields': ('subscriptions',
                                 'avatar',
                                 'role',
                                 'favorites',
                                 'shopping_cart')}),
)
UserAdmin.list_display += (
    'subscriptions',
    'avatar',
    'role',
    'favorites',
    'shopping_cart',
)
UserAdmin.search_fields = ('email', 'username')
admin.site.register(UserWithSubscriptions, UserAdmin)
