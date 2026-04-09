from rest_framework import permissions

class IsRoleAdmin(permissions.BasePermission):
    """
    Permite el acceso SOLO a los usuarios que tengan el rol 'ADMIN'.
    """
    def has_permission(self, request, view):
        # 1. Verificamos que el usuario haya iniciado sesión
        if not request.user or not request.user.is_authenticated:
            return False
            
        group_name = 'administrador'
        return request.user.groups.filter(name=group_name).exists()