import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const UserAuditModal = ({ user, onClose }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      try {
        const response = await axiosClient.get(`/api/usuarios/${user.id}/auditoria`);
        setLogs(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      } finally {
        setLoading(false);
      }
    };
    
    if (user && user.id) {
      fetchLogs();
    }
  }, [user]);

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
      backdropFilter: 'blur(5px)'
    }}>
      <div className="glass-panel" style={{
        width: '100%', maxWidth: '800px', maxHeight: '90vh', position: 'relative', padding: '24px',
        display: 'flex', flexDirection: 'column'
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none',
          color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px'
        }}>✕</button>
        
        <h2 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)', fontSize: '1.2em' }}>
          Historial de Acciones: {user.nombre_completo}
        </h2>
        
        {error && (
          <div className="feedback-message error" style={{ marginBottom: '15px' }}>
            {error}
          </div>
        )}

        <div style={{ flex: 1, overflowY: 'auto' }} className="table-responsive">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>Cargando historial...</div>
          ) : logs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
              No hay registros de auditoría para este usuario.
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fecha y Hora</th>
                  <th>Acción</th>
                  <th>Método</th>
                  <th>Ruta</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: 'nowrap' }}>{formatDate(log.timestamp)}</td>
                    <td><span className="badge badge-info">{log.accion}</span></td>
                    <td>
                      <span className={`badge ${
                        log.metodo === 'POST' ? 'badge-success' : 
                        log.metodo === 'DELETE' ? 'badge-secondary' : 'badge-primary'
                      }`} style={{ background: log.metodo === 'DELETE' ? 'var(--error)' : undefined }}>
                        {log.metodo}
                      </span>
                    </td>
                    <td style={{ wordBreak: 'break-all' }}>{log.endpoint}</td>
                    <td>{log.direccion_ip || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
};

export default UserAuditModal;
