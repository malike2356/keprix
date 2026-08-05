"""Product API route registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


RouteMount = Callable[[object], None]


@dataclass(frozen=True)
class RegisteredRoute:
    name: str
    mount: RouteMount
    product: str


_ROUTES: dict[str, RegisteredRoute] = {}


def register_route(name: str, mount: RouteMount, *, product: str) -> None:
    _ROUTES[name] = RegisteredRoute(name=name, mount=mount, product=product)


def iter_routes() -> list[RegisteredRoute]:
    return list(_ROUTES.values())


def clear_routes_for_tests() -> None:
    _ROUTES.clear()

