"""Контроллеры."""

from rest_framework.permissions import (AllowAny,  # type: ignore
                                        IsAuthenticated)
from rest_framework import viewsets  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from rest_framework.decorators import action  # type: ignore
from rest_framework.response import Response  # type: ignore

from recipes.models import Tag, Recipe, Ingredient
from .serializers import (TagSerializer, RecipeWriteSerializer,
                          RecipeReadSerializer, IngredientSerializer,
                          UserReadSerializer, UserWriteSerializer,
                          PasswordSerializer)
from .permissions import AuthorOnly, ForbiddenPermission


User = get_user_model()


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


class UserViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', 'post')
    queryset = User.objects.all()
    permission_classes = (AllowAny,)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def set_password(self, request):
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action in {'me', 'list', 'retrieve'}:
            return UserReadSerializer
        if self.action == 'set_password':
            return PasswordSerializer
        return UserWriteSerializer
