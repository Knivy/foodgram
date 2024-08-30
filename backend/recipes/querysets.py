"""Аннотирование полей модели."""

from django.db.models.query import QuerySet  # type: ignore
from django.db.models import Value  # type: ignore
from django.db.models import Exists, OuterRef  # type: ignore

from users.models import Favorite, ShoppingCart


class AnnotatedRecipeQuerySet(QuerySet):
    """Аннотированный queryset."""

    def annotate_fields(self, user):
        """Аннотировать queryset."""
        if not user.is_authenticated:
            return self.annotate(
                is_favorited=Value(False),
                is_in_shopping_cart=Value(False),
            )
        return (
            self.select_related('author')
            .prefetch_related('tags', 'ingredients')
            .annotate(
                is_favorited=Exists( 
                    Favorite.objects.filter(recipe=OuterRef('pk'), user=user)
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        recipe=OuterRef('pk'), user=user
                    )
                ),
            )
        )
