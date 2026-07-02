import React from 'react';
import { X } from 'lucide-react';

const ClientViewModal = ({ client, onClose }) => {
  if (!client) return null;

  // Exclude keys that we might not want to show directly or are redundant
  const excludeKeys = ['Apellido y Nombre'];
  
  const entries = Object.entries(client).filter(([key]) => !excludeKeys.includes(key));

  const formatValue = (key, value) => {
    if (value === null || value === '') return '-';
    if (key === 'Remuneración' && !isNaN(value)) {
      return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value);
    }
    return value;
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1000, animation: 'fadeIn 0.3s ease' }}>
      <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()} style={{ width: '600px', maxWidth: '90%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
        <div className="modal-header" style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, color: 'var(--text-color)' }}>Datos Completos del Cliente</h3>
          <button className="btn-secondary" onClick={onClose} style={{ padding: '4px 8px' }}>
            <X size={18} />
          </button>
        </div>
        
        <div className="modal-body" style={{ padding: '24px', overflowY: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {entries.map(([key, value]) => (
              <div key={key} style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-color)', opacity: 0.7, fontWeight: 'bold', marginBottom: '4px' }}>
                  {key}
                </span>
                <span style={{ fontSize: '14px', color: 'var(--text-color)', background: 'rgba(255,255,255,0.05)', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                  {formatValue(key, value)}
                </span>
              </div>
            ))}
          </div>
        </div>
        
        <div className="modal-footer" style={{ padding: '16px 24px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-secondary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClientViewModal;
