import React, { useState, useEffect } from 'react';
import axiosClient from '../../api/axiosClient';
import CurrencyInput from '../CurrencyInput';
import { X, Trash2, Edit2, Check } from 'lucide-react';

const CancelacionesListModal = ({ isOpen, onClose, comprobante, onSave }) => {
  const [cancelaciones, setCancelaciones] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ importe: 0, fecha_cancelacion: '' });

  useEffect(() => {
    if (isOpen && comprobante) {
      fetchCancelaciones();
    } else {
      setCancelaciones([]);
      setError('');
      setEditingId(null);
    }
  }, [isOpen, comprobante]);

  const fetchCancelaciones = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await axiosClient.get(`/api/finanzas/comprobantes/${comprobante.id}/cancelaciones`);
      setCancelaciones(res.data);
    } catch (err) {
      console.error(err);
      setError('Error al cargar los pagos.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Está seguro de eliminar este pago?')) return;
    try {
      await axiosClient.delete(`/api/finanzas/cancelaciones/${id}`);
      fetchCancelaciones();
      onSave(); // Refresh parent to update balances
    } catch (err) {
      console.error(err);
      alert('Error al eliminar el pago');
    }
  };

  const handleEditClick = (canc) => {
    setEditingId(canc.id);
    setEditForm({ 
      importe: parseFloat(canc.importe), 
      fecha_cancelacion: canc.fecha_cancelacion 
    });
  };

  const handleEditCancel = () => {
    setEditingId(null);
  };

  const handleEditSave = async (id) => {
    try {
      await axiosClient.put(`/api/finanzas/cancelaciones/${id}`, {
        importe: parseFloat(editForm.importe),
        fecha_cancelacion: editForm.fecha_cancelacion
      });
      setEditingId(null);
      fetchCancelaciones();
      onSave(); // Refresh parent to update balances
    } catch (err) {
      console.error(err);
      alert('Error al actualizar el pago');
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  if (!isOpen || !comprobante) return null;

  const totalAbonado = cancelaciones.reduce((acc, c) => acc + parseFloat(c.importe || 0), 0);
  const totalComprobante = parseFloat(comprobante.importe_total || 0);

  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="modal-content" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto', boxShadow: 'var(--shadow-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0 }}>Historial de Pagos</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={24} /></button>
        </div>
        
        <div style={{ marginBottom: '20px', padding: '12px', backgroundColor: 'var(--surface-color)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: 'var(--text-muted)' }}>
            Comprobante: <strong>{comprobante.tipo_comprobante} {String(comprobante.punto_venta).padStart(4, '0')}-{String(comprobante.numero_comprobante).padStart(8, '0')}</strong>
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '15px' }}>
            <span>Total:</span>
            <strong>{formatCurrency(totalComprobante)}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '15px', marginTop: '4px' }}>
            <span>Abonado:</span>
            <strong>{formatCurrency(totalAbonado)}</strong>
          </div>
          
          {(totalAbonado > totalComprobante) && (
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '15px', marginTop: '4px', color: 'var(--danger-color)' }}>
              <span>Abonado de más:</span>
              <strong>{formatCurrency(totalAbonado - totalComprobante)}</strong>
            </div>
          )}
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>{error}</div>}

        <div className="table-responsive">
          <table className="data-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'center' }}>Fecha</th>
                <th style={{ textAlign: 'center' }}>Ref. Banco</th>
                <th style={{ textAlign: 'right' }}>Importe</th>
                <th style={{ textAlign: 'center', width: '100px' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="4" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : cancelaciones.length === 0 ? (
                <tr><td colSpan="4" style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>No hay pagos registrados.</td></tr>
              ) : (
                cancelaciones.map(canc => {
                  const isEditing = editingId === canc.id;
                  
                  return (
                    <tr key={canc.id}>
                      <td style={{ textAlign: 'center' }}>
                        {isEditing ? (
                          <input 
                            type="date" 
                            className="form-control" 
                            style={{ padding: '4px' }}
                            value={editForm.fecha_cancelacion}
                            onChange={(e) => setEditForm({...editForm, fecha_cancelacion: e.target.value})}
                          />
                        ) : (
                          canc.fecha_cancelacion
                        )}
                      </td>
                      <td style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                        {canc.movimiento_info ? (
                          <span title={`Movimiento Bancario #${canc.movimiento_info.id}`}>
                            {canc.movimiento_info.cuenta_nombre} (#{canc.movimiento_info.id})
                          </span>
                        ) : canc.movimiento_id ? (
                          <span title="Movimiento Bancario asociado">#{canc.movimiento_id}</span>
                        ) : '-'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {isEditing ? (
                          <CurrencyInput
                            className="form-control"
                            style={{ padding: '4px', textAlign: 'right' }}
                            value={editForm.importe}
                            onChange={(val) => setEditForm({...editForm, importe: val})}
                          />
                        ) : (
                          formatCurrency(canc.importe)
                        )}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                          {isEditing ? (
                            <>
                              <button className="btn-secondary" onClick={() => handleEditSave(canc.id)} title="Guardar" style={{ padding: '4px 8px' }}>
                                ✔️
                              </button>
                              <button className="btn-secondary" onClick={handleEditCancel} title="Cancelar" style={{ padding: '4px 8px' }}>
                                ❌
                              </button>
                            </>
                          ) : (
                            <>
                              <button className="btn-secondary" onClick={() => handleEditClick(canc)} title="Editar" style={{ padding: '4px 8px' }}>
                                ✏️
                              </button>
                              <button className="btn-secondary" onClick={() => handleDelete(canc.id)} title="Eliminar" style={{ padding: '4px 8px', color: 'var(--danger-color)' }}>
                                🗑️
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CancelacionesListModal;
