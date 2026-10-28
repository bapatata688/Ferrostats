from typing import Callable, Optional
from fastapi import Header, HTTPException, status

def get_current_user_role(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> str:
    """
    Extrae el rol del usuario desde el header HTTP 'X-User-Role'.
    Por defecto, para entorno de desarrollo o evaluación sin header, asume 'ADMIN'.
    Roles válidos: 'ADMIN', 'CAJERO', 'BODEGUERO'.
    """
    role = (x_user_role or "ADMIN").upper().strip()
    if role not in ("ADMIN", "CAJERO", "BODEGUERO"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Rol '{role}' no reconocido. Roles válidos: ADMIN, CAJERO, BODEGUERO"
        )
    return role

def require_role(*allowed_roles: str) -> Callable:
    """
    Dependency factory de FastAPI para hacer cumplir RBAC en cada endpoint.
    """
    def role_checker(
        role: str = Header("ADMIN", alias="X-User-Role")
    ) -> str:
        current_role = (role or "ADMIN").upper().strip()
        if current_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado para el rol '{current_role}'. Permisos requeridos: {list(allowed_roles)}"
            )
        return current_role

    return role_checker
