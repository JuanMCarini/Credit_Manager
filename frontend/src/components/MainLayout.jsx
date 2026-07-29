import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useEffect, useRef, useCallback, useState } from 'react';
import useAppStore from '../store/useAppStore';
import { useNavigate } from 'react-router-dom';
import { Menu } from 'lucide-react';
import ChangeMyPasswordModal from './ChangeMyPasswordModal';
import { useAuthStore } from '../store/useAuthStore';
import axiosClient from '../api/axiosClient';

const MainLayout = () => {
  const { fetchAuxiliares, checkApiStatus } = useAppStore();
  const { user, login, logout } = useAuthStore();
  const navigate = useNavigate();
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const timeoutRef = useRef(null);
  const intervalRef = useRef(null);
  const INACTIVITY_TIME = 30 * 60 * 1000; // 30 minutes
  const REFRESH_INTERVAL = 14 * 60 * 1000; // 14 minutes (before 30 min backend expiration)

  const handleLogout = useCallback(async (isAuto = false) => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {
      console.error('Logout failed', e);
    }
    logout();
    if (isAuto === true) {
      alert("Su sesión ha expirado por inactividad. Por favor, vuelva a iniciar sesión.");
    }
    navigate('/login');
  }, [logout, navigate]);

  const handleActivity = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => handleLogout(true), INACTIVITY_TIME);
  }, [handleLogout]);

  useEffect(() => {
    checkApiStatus();
    fetchAuxiliares();
  }, [checkApiStatus, fetchAuxiliares]);

  useEffect(() => {
    const events = ['mousemove', 'keydown', 'click', 'scroll'];
    events.forEach(event => window.addEventListener(event, handleActivity));

    handleActivity();

    intervalRef.current = setInterval(async () => {
      try {
        const response = await axiosClient.post('/api/auth/refresh');
        if (response.data && response.data.access_token) {
          login(response.data.user, response.data.access_token);
        }
      } catch (error) {
        console.error("Error refreshing token", error);
        // If refresh fails, let it be (axios interceptor might catch it on next call or we log out)
      }
    }, REFRESH_INTERVAL);

    return () => {
      events.forEach(event => window.removeEventListener(event, handleActivity));
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [handleActivity, login]);


  return (
    <div className="app-container">
      {isSidebarOpen && <Sidebar />}
      <main className="main-content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <button className="btn-secondary" onClick={() => setIsSidebarOpen(!isSidebarOpen)} style={{ padding: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }} title={isSidebarOpen ? "Ocultar menú" : "Mostrar menú"}>
              <Menu size={20} />
            </button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            {user && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', marginRight: '10px' }}>
                <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{user.nombre || user.nombre_completo}</span>
                <span style={{ fontSize: '0.8em', color: 'var(--text-secondary)' }}>
                  {typeof user.rol === 'string' ? user.rol : user.rol?.nombre || 'Usuario'}
                </span>
              </div>
            )}
            <button className="btn-secondary" onClick={() => setShowPasswordModal(true)}>
              Cambiar Contraseña
            </button>
            <button className="btn-secondary" onClick={handleLogout}>
              Cerrar Sesión
            </button>
          </div>
        </div>
        <Outlet />
        {showPasswordModal && (
          <ChangeMyPasswordModal 
            onClose={() => setShowPasswordModal(false)} 
            onSuccess={() => setShowPasswordModal(false)} 
          />
        )}
      </main>
    </div>
  );
};

export default MainLayout;
