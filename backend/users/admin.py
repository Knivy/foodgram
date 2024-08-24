from django.contrib import admin  # type: ignore
from django.contrib.auth.admin import UserAdmin  # type: ignore

from users.models import UserWithSubscriptions, Subscription

UserAdmin.fieldsets += (
    ('Extra Fields', {'fields': ('subscriptions',
                                 'avatar',
                                 'role',
                                 'favorites',
                                 'shopping_cart')}),
)
UserAdmin.list_display += (
    'avatar',
    'role',
)
UserAdmin.search_fields = ('email', 'username')
UserAdmin.verbose_name = 'Пользователь'
UserAdmin.actions += ('change_selected',
                      'delete_selected')


class SubscriptionAdmin(admin.ModelAdmin):
    """Регистрация списка подписок."""

    list_display = ('user', 'author')
    fields = ('user', 'author')
    search_fields = ('user__username',)
    verbose_name = 'Подписка'
    verbose_name_plural = 'Подписки'
    actions = ('change_selected', 'delete_selected')
    empty_value_display = '-пусто-'


admin.site.register(UserWithSubscriptions, UserAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
