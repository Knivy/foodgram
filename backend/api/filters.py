"""Фильтры."""

from enum import IntEnum

from django_filters import rest_framework as filters  # type: ignore

from recipes.models import Recipe


class FlagsEnum(IntEnum):
    """Перечисление флагов."""

    yes = 1
    no = 0


class RecipeFilter(filters.FilterSet):
    """
    Доступна фильтрация по избранному, автору, списку покупок и тегам.

    Нечувствительно к регистру.
    """

    author = filters.IntegerFilter(field_name='author__id',
                                   lookup_expr='exact')

    class Meta:
        """Настройки фильтра."""

        model = Recipe

    def filter_queryset(self, request, queryset, view):
        """Фильтрация по флагам."""
        if ('is_favorited' in request.GET and
           request.GET['is_favorited'] == FlagsEnum.yes):
            user = request.user
            queryset = queryset.filter(favorites__user=user)
        if ('is_in_shopping_cart' in request.GET and
           request.GET['is_in_shopping_cart'] == FlagsEnum.yes):
            user = request.user
            queryset = queryset.filter(shopping_cart__user=user)
        tags = request.GET.getlist('tags')
        if tags:
            return queryset.filter(tags__in__exact=tags)
        return queryset
