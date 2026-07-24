import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import { Edit, KeyRound, FileText, Trash2 } from 'lucide-react';
import UserFormModal from '../components/UserFormModal';
import UserPasswordModal from '../components/UserPasswordModal';
import UserAuditModal from '../components/UserAuditModal';
import ExportExcelButton from '../components/ExportExcelButton';

const UsersListPage = () => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingActions, setLoadingActions] = useState({});
  const [error, setError] = useState(null);
  
  const [showFormModal, setShowFormModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [usersRes, rolesRes] = await Promise.all([
        axiosClient.get('/api/usuarios'),
        axiosClient.get('/api/usuarios/roles')
      ]);
      setUsers(usersRes.data);
      setRoles(rolesRes.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddClick = () => {
    setSelectedUser(null);
    setShowFormModal(true);
  };

  const handleEditClick = (user) => {
    setSelectedUser(user);
    setShowFormModal(true);
  };

  const handleChangePasswordClick = (user) => {
    setSelectedUser(user);
    setShowPasswordModal(true);
  };

  const handleAuditClick = (user) => {
    setSelectedUser(user);
    setShowAuditModal(true);
  };

  const handleDeleteClick = async (user) => {
    if (window.confirm(`¿Estás seguro de que deseas eliminar al usuario ${user.nombre_completo}?`)) {
      setLoadingActions(prev => ({ ...prev, [`delete-${user.id}`]: true }));
      try {
        await axiosClient.delete(`/api/usuarios/${user.id}`);
        fetchData();
      } catch (err) {
        alert(err.response?.data?.detail || 'Error al eliminar el usuario');
      } finally {
        setLoadingActions(prev => ({ ...prev, [`delete-${user.id}`]: false }));
      }
    }
  };

  const handleModalSuccess = () => {
    setShowFormModal(false);
    setShowPasswordModal(false);
    fetchData();
  };

  return (
    <div className="page-container fade-in">
      <div className="page-header glass-panel">
        <h1 className="page-title">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '10px' }}>
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          Gestión de Usuarios
        </h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <ExportExcelButton 
            data={users.map(u => ({ ...u, rol: u.rol?.nombre }))} 
            filename="usuarios_export" 
          />
          <button className="btn btn-primary" onClick={handleAddClick}>
            Nuevo Usuario
          </button>
        </div>
      </div>

      <div className="content-card glass-panel mt-4">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>Cargando usuarios...</div>
        ) : error ? (
          <div className="feedback-message error">{error}</div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre Completo</th>
                  <th>Email</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th style={{textAlign: 'right'}}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.nombre_completo}</td>
                    <td>{user.email}</td>
                    <td><span className="badge badge-info">{user.rol.nombre}</span></td>
                    <td>
                      <span className={`badge ${user.is_active ? 'badge-success' : 'badge-secondary'}`}>
                        {user.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right', display: 'flex', gap: '5px', justifyContent: 'flex-end', alignItems: 'center' }}>
                      <button className="btn btn-sm btn-secondary" style={{ fontSize: '14px' }} title="Editar Usuario" onClick={() => handleEditClick(user)}>
                        ✏️
                      </button>
                      <button className="btn btn-sm btn-secondary" style={{ fontSize: '14px' }} title="Cambiar Contraseña" onClick={() => handleChangePasswordClick(user)}>
                        🔑
                      </button>
                      <button className="btn btn-sm btn-secondary" style={{ fontSize: '14px' }} title="Ver Auditoría" onClick={() => handleAuditClick(user)}>
                        📄
                      </button>
                      <button className="btn btn-sm btn-secondary" style={{ fontSize: '14px', color: 'var(--error)' }} title="Borrar Usuario" onClick={() => handleDeleteClick(user)} disabled={loadingActions[`delete-${user.id}`]}>
                        {loadingActions[`delete-${user.id}`] ? '⏳' : '🗑️'}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', padding: '20px' }}>No hay usuarios registrados.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showFormModal && (
        <UserFormModal 
          user={selectedUser} 
          roles={roles}
          onClose={() => setShowFormModal(false)} 
          onSuccess={handleModalSuccess} 
        />
      )}

      {showPasswordModal && selectedUser && (
        <UserPasswordModal 
          user={selectedUser} 
          onClose={() => setShowPasswordModal(false)} 
          onSuccess={handleModalSuccess} 
        />
      )}

      {showAuditModal && selectedUser && (
        <UserAuditModal 
          user={selectedUser} 
          onClose={() => setShowAuditModal(false)} 
        />
      )}
    </div>
  );
};

export default UsersListPage;
