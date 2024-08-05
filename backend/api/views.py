"""Контроллеры."""

from rest_framework.permissions import (AllowAny,  # type: ignore
                                        IsAuthenticated)
from rest_framework import viewsets  # type: ignore

from recipes.models import Tag, Recipe, Ingredient
from .serializers import (TagSerializer, RecipeWriteSerializer,
                          RecipeReadSerializer, IngredientSerializer)
from .permissions import AuthorOnly, ForbiddenPermission


class BaseReadOnlyViewset(viewsets.ReadOnlyModelViewSet):
    """Базовый вьюсет для чтения."""

    permission_classes = (AllowAny,)
    pagination_class = None


class TagViewSet(BaseReadOnlyViewset):
    """Вьюсет тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(BaseReadOnlyViewset):
    """Вьюсет ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет рецептов."""

    http_method_names = ('get', 'post', 'patch', 'delete')
    queryset = Recipe.objects.all()

    def get_permissions(self):
        """Разрешения."""
        if self.action in {'list', 'retrieve'}:
            self.permission_classes = (AllowAny,)
        elif self.action == 'create':
            self.permission_classes = (IsAuthenticated,)
        elif self.action in {'partial_update', 'destroy'}:
            self.permission_classes = (AuthorOnly,)
        else:
            self.permission_classes = (ForbiddenPermission,)
        return super().get_permissions()

    def get_serializer_class(self):
        """Выбор сериализатора."""
        if self.action in {'list', 'retrieve'}:
            return RecipeReadSerializer
        return RecipeWriteSerializer
