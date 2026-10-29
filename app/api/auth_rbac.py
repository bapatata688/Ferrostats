from typing import Callable, Optional, Set
from fastapi import Header, HTTPException, status

ROLE_MAP = {
    "ADMIN": "ADMIN",
    "ADMINISTRATOR": "ADMIN",
    "CASHIER": "CASHIER",
    "CAJERO": "CASHIER",
    "WAREHOUSE": "WAREHOUSE",
    "BODEGUERO": "WAREHOUSE",
}

def normalize_role(role_name: Optional[str]) -> str:
    cleaned = (role_name or "ADMIN").upper().strip()
    return ROLE_MAP.get(cleaned, cleaned)

def get_current_user_role(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> str:
    """
    Extracts user role from 'X-User-Role' HTTP header.
    Defaults to 'ADMIN' for local evaluation.
    Valid normalized roles: 'ADMIN', 'CASHIER', 'WAREHOUSE'.
    """
    role = normalize_role(x_user_role)
    if role not in ("ADMIN", "CASHIER", "WAREHOUSE"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unrecognized role '{x_user_role}'. Valid roles: ADMIN, CASHIER (CAJERO), WAREHOUSE (BODEGUERO)"
        )
    return role

def require_role(*allowed_roles: str) -> Callable:
    """
    FastAPI dependency factory enforcing RBAC on each endpoint.
    Supports both English and Spanish role aliases.
    """
    normalized_allowed: Set[str] = {normalize_role(r) for r in allowed_roles}

    def role_checker(
        role: str = Header("ADMIN", alias="X-User-Role")
    ) -> str:
        current_role = normalize_role(role)
        if current_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role '{role}'. Required permissions: {list(normalized_allowed)}"
            )
        return current_role

    return role_checker
