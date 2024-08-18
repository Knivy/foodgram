from django.contrib import admin  # type: ignore
from django.contrib.auth.models import Group  # type: ignore
from rest_framework.authtoken.admin import TokenAdmin  # type: ignore
from rest_framework.authtoken.models import Token  # type: ignore

from .models import Ingredient, Tag, Recipe, RecipeIngredient


TokenAdmin.verbose_name = 'Токен'
TokenAdmin.verbose_name_plural = 'Токены'
Token._meta.verbose_name = 'Токен'
Token._meta.verbose_name_plural = 'Токены'
admin.site.site_header = 'Административная панель'
admin.site.site_title = 'Административная панель'
admin.site.index_title = 'Административная панель'


class RecipeAdmin(admin.ModelAdmin):
    """Регистрация рецептов."""

    list_display = ('name', 'author', 'favorite_count')
    fields = ('name', 'author', 'image', 'text', 'tags')
    list_filter = ('tags',)
    search_fields = ('name', 'author__username')
    verbose_name = 'Рецепт'
    verbose_name_plural = 'Рецепты'
    empty_value_display = '-пусто-'
    actions = ('change_selected',
               'delete_selected')

    def favorite_count(self, recipe):
        """Число добавлений в избранное."""
        return recipe.favorites.count()


class IngredientAdmin(admin.ModelAdmin):
    """Регистрация ингредиентов."""

    list_display = ('name', 'measurement_unit')
    fields = ('name', 'measurement_unit')
    search_fields = ('name',)
    verbose_name = 'Ингредиент'
    verbose_name_plural = 'Ингредиенты'
    actions = ('change_selected',
               'delete_selected')


class TagAdmin(admin.ModelAdmin):
    """Регистрация тегов."""

    list_display = ('name',)
    fields = ('name',)
    search_fields = ('name',)
    verbose_name = 'Тег'
    verbose_name_plural = 'Теги'
    actions = ('change_selected',
               'delete_selected')


class RecipeIngredientAdmin(admin.ModelAdmin):
    """Регистрация ингредиентов в рецепте."""

    list_display = ('recipe', 'ingredient', 'amount')
    fields = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name',)
    verbose_name = 'Ингредиент в рецепте'
    verbose_name_plural = 'Ингредиенты в рецепте'
    actions = ('change_selected',
               'delete_selected')


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(RecipeIngredient, RecipeIngredientAdmin)
admin.site.unregister(Group)
