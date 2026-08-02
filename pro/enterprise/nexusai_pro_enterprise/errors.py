"""Domain errors for the enterprise layer, mapped to HTTP by the API adapter."""

from __future__ import annotations


class EnterpriseError(Exception):
    """Base error."""


class AuthenticationError(EnterpriseError):
    """Bad credentials, or an invalid/expired token or API key."""


class PermissionDenied(EnterpriseError):
    """The principal lacks the required permission in the given scope."""


class NotFoundError(EnterpriseError):
    """A referenced entity does not exist."""


class ConflictError(EnterpriseError):
    """An entity already exists or a uniqueness constraint was violated."""


class ValidationError(EnterpriseError):
    """Input failed a policy or format check."""
