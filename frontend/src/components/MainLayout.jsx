import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useEffect, useRef, useCallback, useState } from 'react';
import useAppStore from '../store/useAppStore';
import { useNavigate } from 'react-router-dom';
import { Menu } from 'lucide-react';
import ChangeMyPasswordModal from './ChangeMyPasswordModal';
import { useAuthStore } from '../store/useAuthStore';
import axiosClient from '../api/axiosClient';

const INACTIVITY_TIME = 30 * 60 * 1000; // 30 minutes
const REFRESH_INTERVAL = 14 * 60 * 1000; // 14 minutes (before backend expiration)
const ACTIVITY_THROTTLE_MS = 1000; // Throttle timer resets for high-frequency events

const MainLayout = () => {
  const { fetchAuxiliares, checkApiStatus, fetchSystemModules } = useAppStore();
  const { user, login, logout } = useAuthStore();
  const navigate = useNavigate();
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [arcaAlertData, setArcaAlertData] = useState(null);

  const timeoutRef = useRef(null);
  const intervalRef = useRef(null);
  const lastActivityRef = useRef(0);
  const handleLogoutRef = useRef(null);

  const handleLogout = useCallback(async (isAuto = false) => {
    const auto = isAuto === true;
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (intervalRef.current) clearInterval(intervalRef.current);
    try {
      await axiosClient.post('/api/auth/logout');
    } catch (e) {
      console.error('Logout failed', e);
    }
    logout();
    if (auto) {
      alert("Su sesión ha expirado por inactividad. Por favor, vuelva a iniciar sesión.");
    }
    navigate('/login');
  }, [logout, navigate]);

  useEffect(() => {
    handleLogoutRef.current = handleLogout;
  }, [handleLogout]);

  const resetInactivityTimer = useCallback((force = false) => {
    const now = Date.now();
    if (!force && now - lastActivityRef.current < ACTIVITY_THROTTLE_MS) {
      return;
    }
    lastActivityRef.current = now;
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      handleLogoutRef.current?.(true);
    }, INACTIVITY_TIME);
  }, []);

  useEffect(() => {
    checkApiStatus();
    fetchAuxiliares();
    fetchSystemModules();

    const dismissed = sessionStorage.getItem('arca_cert_alert_dismissed');
    if (dismissed !== 'true') {
      axiosClient
        .get('/api/v1/system/arca/status')
        .then((res) => {
          if (res.data && res.data.alerta_vencimiento === true) {
            setArcaAlertData(res.data);
          }
        })
        .catch(() => {
          // Ignorar errores silenciosamente al verificar estado de certificado
        });
    }
  }, [checkApiStatus, fetchAuxiliares, fetchSystemModules]);

  const handleDismissArcaAlert = () => {
    sessionStorage.setItem('arca_cert_alert_dismissed', 'true');
    setArcaAlertData(null);
  };

  const handleGoToArcaConfig = () => {
    sessionStorage.setItem('arca_cert_alert_dismissed', 'true');
    setArcaAlertData(null);
    navigate('/configuracion/arca');
  };

  useEffect(() => {
    const events = ['mousemove', 'keydown', 'click', 'scroll'];
    const onActivity = () => resetInactivityTimer(false);
    events.forEach((event) => window.addEventListener(event, onActivity, { passive: true }));

    resetInactivityTimer(true);

    return () => {
      events.forEach((event) => window.removeEventListener(event, onActivity));
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [resetInactivityTimer]);

  useEffect(() => {
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
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [login]);


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
            <button className="btn-secondary" onClick={() => handleLogout(false)}>
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
        {arcaAlertData && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              zIndex: 9999,
              backgroundColor: 'rgba(0, 0, 0, 0.72)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '20px',
            }}
          >
            <div
              className="glass-panel"
              style={{
                maxWidth: '480px',
                width: '100%',
                padding: '28px',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid rgba(245, 158, 11, 0.5)',
                boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)',
              }}
            >
              <h3
                style={{
                  marginTop: 0,
                  marginBottom: '12px',
                  color:
                    arcaAlertData.estado_vigencia === 'VENCIDO'
                      ? '#f87171'
                      : '#fbbf24',
                }}
              >
                {arcaAlertData.estado_vigencia === 'VENCIDO'
                  ? 'Certificado Digital ARCA Vencido'
                  : 'Alerta de Vencimiento de Certificado ARCA'}
              </h3>
              <p
                style={{
                  fontSize: '14px',
                  color: 'var(--text-primary)',
                  lineHeight: '1.5',
                  marginBottom: '12px',
                }}
              >
                {arcaAlertData.estado_vigencia === 'VENCIDO' ? (
                  <>
                    El certificado digital X.509 utilizado para facturación
                    electrónica en ARCA se encuentra <strong>vencido</strong> (
                    {Math.abs(arcaAlertData.dias_restantes ?? 0)} días desde su
                    expiración).
                  </>
                ) : (
                  <>
                    El certificado digital X.509 de ARCA vencerá en{' '}
                    <strong>{arcaAlertData.dias_restantes} días</strong>. Renueve
                    el certificado con anticipación para evitar interrupciones en
                    la emisión de comprobantes electrónicos.
                  </>
                )}
              </p>
              {arcaAlertData.fecha_vencimiento && (
                <p
                  style={{
                    fontSize: '12px',
                    color: 'var(--text-muted)',
                    marginBottom: '20px',
                  }}
                >
                  Fecha de vencimiento:{' '}
                  <strong>
                    {new Date(arcaAlertData.fecha_vencimiento).toLocaleDateString(
                      'es-AR'
                    )}
                  </strong>
                </p>
              )}
              <div
                style={{
                  display: 'flex',
                  gap: '12px',
                  justifyContent: 'flex-end',
                  marginTop: '18px',
                }}
              >
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleDismissArcaAlert}
                >
                  Entendido
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleGoToArcaConfig}
                >
                  Ir a Configuración ARCA
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default MainLayout;
