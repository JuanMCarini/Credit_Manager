import React, { useState } from 'react';
import axiosClient from '../api/axiosClient';

const CreditEditEstadoModal = ({ creditoId, currentEstado, onClose, onSuccess }) => {
  const [estado, setEstado] = useState(currentEstado || 'APROBADO');
  const [motivo, setMotivo] = useState('');
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const ESTADOS = ['APROBADO', 'FIRMADO', 'ACTIVO', 'CANCELADO', 'MOROSO', 'RECHAZADO', 'JUDICIAL', 'INCOBRABLE'];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFeedback(null);

    try {
      await axiosClient.patch(`/api/v1/creditos/${creditoId}/estado`, {
        estado,
        motivo: motivo.trim() || null
      });
      onSuccess();
      onClose();
    } catch (err) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || err.message || 'Error al cambiar estado' });
      setSaving(false);
    }
  };

  const isCriticalState = ['RECHAZADO', 'JUDICIAL', 'INCOBRABLE'].includes(estado);

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
      backdropFilter: 'blur(5px)'
    }}>
      <div className="glass-panel" style={{
        width: '100%', maxWidth: '440px', position: 'relative', padding: '24px'
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none',
          color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px'
        }}>✕</button>
        
        <h2 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)' }}>Editar Estado (Crédito #{creditoId})</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>Nuevo Estado</label>
            <select
              value={estado}
              onChange={e => setEstado(e.target.value)}
              required
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
            >
              {ESTADOS.map(est => (
                <option key={est} value={est}>{est}</option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
              Motivo / Observación {isCriticalState && <span style={{ color: 'var(--warning)', fontSize: '12px' }}>(Recomendado para estados legales/críticos)</span>}
            </label>
            <textarea
              value={motivo}
              onChange={e => setMotivo(e.target.value)}
              placeholder="Ej: Derivado a estudio jurídico / Sin bienes ejecutables..."
              rows={3}
              style={{
                width: '100%', padding: '8px 12px', borderRadius: '6px',
                border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)',
                color: 'var(--text-primary)', resize: 'vertical'
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '24px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--error)' }}>
              {feedback?.message || ''}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="button" onClick={onClose} className="btn-secondary" disabled={saving}>
                Cancelar
              </button>
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
