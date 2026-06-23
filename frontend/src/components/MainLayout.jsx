import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useEffect } from 'react';
import useAppStore from '../store/useAppStore';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import ChangeMyPasswordModal from './ChangeMyPasswordModal';
import { useAuthStore } from '../store/useAuthStore';

const MainLayout = () => {
  const { fetchAuxiliares, checkApiStatus } = useAppStore();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [showPasswordModal, setShowPasswordModal] = useState(false);

  useEffect(() => {
    checkApiStatus();
    fetchAuxiliares();
  }, [checkApiStatus, fetchAuxiliares]);

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {
      console.error('Logout failed', e);
    }
    logout();
    navigate('/login');
  };

  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginBottom: '24px', gap: '15px' }}>
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
