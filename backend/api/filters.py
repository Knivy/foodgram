"""Фильтры."""

from django_filters import rest_framework as filters  # type: ignore

from recipes.models import Recipe, Tag


class RecipeFilter(filters.FilterSet):
    """
    Доступна фильтрация по избранному, автору, списку покупок и тегам.

    Нечувствительно к регистру.
    """

    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart')

    class Meta:
        """Настройки фильтра."""

        model = Recipe
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')

    def get_filterset_config(self):
        """Для доступа к запросу."""
        config = super().get_filterset_config()
        config['request'] = self.request
        return config

    def filter_is_favorited(self, queryset, name, value):
        """Фильтрация по флагу избранное."""
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if not value:
            return queryset.exclude(favorites__in=(user,))
        return queryset.filter(favorites__in=(user,))

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтрация по флагу списка покупок."""
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if not value:
            return queryset.exclude(shopping_cart__in=(user,))
        return queryset.filter(shopping_cart__in=(user,))

    def filter_queryset(self, queryset):
        """Фильтрация по флагам."""
        queryset = super().filter_queryset(queryset)
        query = self.request.GET.get('limit')
        if query:
            queryset = queryset[:int(query)]
        return queryset
