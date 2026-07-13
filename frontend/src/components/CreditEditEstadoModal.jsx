import React, { useState } from 'react';
import axiosClient from '../api/axiosClient';

const CreditEditEstadoModal = ({ creditoId, currentEstado, onClose, onSuccess }) => {
  const [estado, setEstado] = useState(currentEstado || 'APROBADO');
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const ESTADOS = ['APROBADO', 'FIRMADO', 'ACTIVO', 'CANCELADO', 'MOROSO', 'RECHAZADO', 'JUDICIAL'];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFeedback(null);

    try {
      await axiosClient.patch(`/api/v1/creditos/${creditoId}/estado`, { estado });
      onSuccess();
      onClose();
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Error al cambiar estado' });
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
      backdropFilter: 'blur(5px)'
    }}>
      <div className="glass-panel" style={{
        width: '100%', maxWidth: '400px', position: 'relative', padding: '24px'
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none',
          color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px'
        }}>✕</button>
        
        <h2 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)' }}>Editar Estado (Crédito #{creditoId})</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Nuevo Estado</label>
            <select value={estado} onChange={e => setEstado(e.target.value)} required>
              {ESTADOS.map(est => (
                <option key={est} value={est}>{est}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '24px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--error)' }}>
              {feedback?.message || ''}
            </div>
            <div>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? "Guardando..." : "Actualizar"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreditEditEstadoModal;
