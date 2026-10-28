import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../store/useAuthStore';

const ProtectedRoute = ({ allowedRoles }) => {
  const { user, token } = useAuthStore();

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  // Permitir siempre al Administrador o a roles específicos
  const userRole = typeof user.rol === 'object' ? user.rol?.nombre : user.rol;
  const hasAccess = userRole === 'Administrador' || allowedRoles.includes(userRole);

  if (!hasAccess) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
