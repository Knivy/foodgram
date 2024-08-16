from django.contrib import admin  # type: ignore
from django.contrib.auth.models import Group  # type: ignore

from .models import Ingredient, Tag, Recipe, RecipeIngredient


class RecipeAdmin(admin.ModelAdmin):
    """Регистрация рецептов."""

    list_display = ('name', 'author', 'favorite_count')
    list_filter = ('tags',)
    search_fields = ('name', 'author__username')

    def favorite_count(self, recipe):
        """Число добавлений в избранное."""
        return recipe.favorites.count()


class IngredientAdmin(admin.ModelAdmin):
    """Регистрация ингредиентов."""

    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(RecipeIngredient)
admin.site.unregister(Group)
