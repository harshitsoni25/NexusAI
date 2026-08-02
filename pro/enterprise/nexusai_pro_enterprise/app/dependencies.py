"""FastAPI dependencies for the enterprise API.

Authenticate the caller from either a Bearer token or an ``X-API-Key`` header into a
``Principal``, and provide a permission guard factory. These are standalone — mounting
this API does not touch the Community engine or the existing Pro API.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from ..domain.models import Principal
from ..domain.permissions import Permission
from ..errors import AuthenticationError, PermissionDenied
from .container import EnterpriseContainer


def get_container(request: Request) -> EnterpriseContainer:
    container: EnterpriseContainer | None = getattr(request.app.state, "enterprise", None)
    if container is None:  # pragma: no cover
        raise RuntimeError("enterprise container not initialised")
    return container


ContainerDep = Annotated[EnterpriseContainer, Depends(get_container)]


def current_principal(
    container: ContainerDep,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> Principal:
    try:
        if x_api_key:
            return container.auth.authenticate_api_key(x_api_key)
        if authorization and authorization.lower().startswith("bearer "):
            return container.auth.authenticate_token(authorization[7:])
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")


PrincipalDep = Annotated[Principal, Depends(current_principal)]


def require(permission: Permission) -> Callable[..., Principal]:
    """Return a dependency that enforces ``permission`` for the current principal."""

    def _guard(principal: PrincipalDep, container: ContainerDep) -> Principal:
        try:
            container.authorizer.require(principal, permission)
        except PermissionDenied as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return principal

    return _guard
