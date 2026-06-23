import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useEffect } from 'react';
import useAppStore from '../store/useAppStore';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import ChangeMyPasswordModal from './ChangeMyPasswordModal';

const MainLayout = () => {
  const { fetchAuxiliares, checkApiStatus } = useAppStore();
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
    // Remove token from local storage if stored there
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px', gap: '10px' }}>
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
