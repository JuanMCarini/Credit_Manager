import { NavLink } from 'react-router-dom';
import useAppStore from '../store/useAppStore';

const Sidebar = () => {
  const { apiStatus } = useAppStore();

  const isOnline = apiStatus.includes('Conectado');

  return (
    <aside className="sidebar glass-panel">
      <div className="logo-container">
        <h1 className="logo-text">Credit<span>Manager</span></h1>
        <p className="logo-subtext">Core Engine API</p>
      </div>

      <nav className="nav-menu">
        <NavLink to="/simulation" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
          Simular Cuotas
        </NavLink>
        <NavLink to="/balances" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
          Reportes de Saldos
        </NavLink>
        <NavLink to="/clientes" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          Listado de Clientes
        </NavLink>
        <NavLink to="/creditos" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="5" width="20" height="14" rx="2" ry="2" />
            <line x1="2" y1="10" x2="22" y2="10" />
          </svg>
          Listado de Créditos
        </NavLink>
        <NavLink to="/alta-cliente" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="8.5" cy="7" r="4" />
            <line x1="20" y1="8" x2="20" y2="14" />
            <line x1="23" y1="11" x2="17" y2="11" />
          </svg>
          Alta de Cliente
        </NavLink>
        <NavLink to="/alta-credito" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
            <path d="M12 14v4" />
            <path d="M10 16h4" />
          </svg>
          Alta de Crédito
        </NavLink>
        <NavLink to="/auxiliares" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="3" y1="9" x2="21" y2="9" />
            <line x1="9" y1="21" x2="9" y2="9" />
          </svg>
          Tablas Auxiliares
        </NavLink>
        <NavLink to="/acciones" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
          Acciones del Sistema
        </NavLink>
      </nav>

      <div className="sidebar-footer" style={{ marginTop: 'auto' }}>
        <div className="status-indicator">
          <span className={`status-dot ${isOnline ? 'online' : 'offline'}`}></span>
          <span>{apiStatus}</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
