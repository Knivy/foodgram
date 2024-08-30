"""Аннотирование полей модели."""

from django.db.models.query import QuerySet  # type: ignore
from django.db.models import Case, When, BooleanField, Value  # type: ignore


class AnnotatedRecipeQuerySet(QuerySet):
    """Аннотированный queryset."""

    def annotate_fields(self, user):
        """Аннотировать queryset."""
        if not user.is_authenticated:
            return self.annotate(
                is_favorited=Value(False),
                is_in_shopping_cart=Value(False),
            )
        return self.annotate(
            is_favorited=Case(
                When(favorites__in=(user,), then=True),
                default=False,
                output_field=BooleanField()
            ),
            is_in_shopping_cart=Case(
                When(shopping_cart__in=(user,), then=True),
                default=False,
                output_field=BooleanField()
            ),
        )
