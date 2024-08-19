"""Фильтры."""

from enum import IntEnum

from django_filters import rest_framework as filters  # type: ignore

from recipes.models import Recipe, Tag


class RecipeFilter(filters.FilterSet):
    """
    Доступна фильтрация по избранному, автору, списку покупок и тегам.

    Нечувствительно к регистру.
    """

    author = filters.NumberFilter(field_name='author__id',
                                  lookup_expr='exact')
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )

    class Meta:
        """Настройки фильтра."""

        model = Recipe
        fields = ['tags']

    def get_filterset_config(self):
        """Для доступа к запросу."""
        config = super().get_filterset_config()
        config['request'] = self.request
        return config

    def filter_queryset(self, queryset):
        """Фильтрация по флагам."""
        request = self.request
        user = request.user
        auth = user.is_authenticated
        query = request.GET.get('is_favorited')
        if query:
            if query == '1':
                if auth:
                    queryset = queryset.filter(favorites__in=(user,))
                else:
                    return queryset.none()
            elif query == '0':
                if auth:
                    queryset = queryset.exclude(favorites__in=(user,))
                else:
                    return queryset.none()
        query = request.GET.get('is_in_shopping_cart')
        if query:
            if query == '1':
                if auth:
                    queryset = queryset.filter(shopping_cart__in=(user,))
                else:
                    return queryset.none()
            elif query == '0':
                if auth:
                    queryset = queryset.exclude(shopping_cart__in=(user,))
                else:
                    return queryset.none()
        query = request.GET.get('author')
        if query:
            queryset = queryset.filter(author__id=int(query))
        # tags = request.GET.getlist('tags')
        # if tags:
        #     for tag in tags:
        #         queryset = queryset.filter(tags__in__exact=tag)
        tags = request.GET.get('tags')
        if tags:
            tags = tags.split(',')
            queryset = queryset.filter(tags__slug__in=tags).distinct()
            # for tag_slug in tags.split(','):
            #     tag = get_object_or_404(Tag, slug=tag_slug)
            #     queryset = queryset.filter(tags__in=tag)
        query = self.request.GET.get('limit')
        if query:
            queryset = queryset[:int(query)]
        return queryset
