from fastapi import Depends, HTTPException, status

from app.modules.admin.security import get_current_user


def require_roles(*roles: str):
    """
    Dependency to require specific roles for an endpoint.
    
    Usage:
        @router.get("/admin-only")
        def admin_only(current_user: dict = Depends(require_roles("admin"))):
            return {"message": "Welcome admin"}
    
    If no roles are specified, it just requires authentication.
    """
    def role_dependency(current_user: dict = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # If no roles specified, just return authenticated user
        if not roles:
            return current_user
        
        user_roles = set(current_user.get("roles", []))
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(roles)}"
            )
        
        return current_user
    
    return role_dependency