import React, { useState, useEffect } from 'react';
import axiosClient from '../../api/axiosClient';
import CurrencyInput from '../CurrencyInput';
import { X, Check } from 'lucide-react';

const CancelacionModal = ({ isOpen, onClose, onSave, comprobante }) => {
  const [formData, setFormData] = useState({
    importe: 0,
    fecha_cancelacion: new Date().toISOString().substring(0, 10),
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Calculate default amount to pay (remaining balance)
  const remainingBalance = comprobante ? Math.max(0, parseFloat(comprobante.importe_total) - parseFloat(comprobante.importe_cancelado || 0)) : 0;

  useEffect(() => {
    if (isOpen && comprobante) {
      setFormData({
        importe: remainingBalance,
        fecha_cancelacion: new Date().toISOString().substring(0, 10),
      });
      setError('');
    }
  }, [isOpen, comprobante, remainingBalance]);

  const handleChange = (e) => {
    // CurrencyInput provides a mock event with name and value (or passes it directly)
    // We already made it compatible
    let raw = e.target ? e.target.value : e;
    const name = e.target ? e.target.name : 'importe';
    setFormData(prev => ({ ...prev, [name]: raw }));
  };

  const handleDateChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const payload = {
      importe: parseFloat(formData.importe),
      fecha_cancelacion: formData.fecha_cancelacion
    };

    if (isNaN(payload.importe) || payload.importe <= 0) {
      setError('El importe a cancelar debe ser mayor a cero.');
      setLoading(false);
      return;
    }

    if (payload.importe > remainingBalance + 0.05) { // Adding tiny delta for floating point drift
      setError(`El importe no puede ser mayor al saldo pendiente ($ ${remainingBalance.toFixed(2)}).`);
      setLoading(false);
      return;
    }

    try {
      await axiosClient.post(`/api/finanzas/comprobantes/${comprobante.id}/cancelaciones`, payload);
      onSave(); // Refresh list and close
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Error al guardar la cancelación');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !comprobante) return null;

  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="modal-content" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '400px', maxHeight: '90vh', overflowY: 'auto', boxShadow: 'var(--shadow-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0 }}>Registrar Pago</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={24} /></button>
        </div>
        <div>
          {error && <div className="alert alert-error" style={{ marginBottom: '16px', padding: '12px', background: '#ffebee', color: '#c62828', borderRadius: '6px' }}>{error}</div>}
          
          <div style={{ marginBottom: '20px', padding: '12px', backgroundColor: 'var(--surface-color)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: 'var(--text-muted)' }}>
              Comprobante: <strong>{comprobante.tipo_comprobante} {String(comprobante.punto_venta).padStart(4, '0')}-{String(comprobante.numero_comprobante).padStart(8, '0')}</strong>
            </p>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '15px' }}>
              <span>Total:</span>
              <strong>$ {parseFloat(comprobante.importe_total).toFixed(2)}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '15px', marginTop: '4px' }}>
              <span>Abonado:</span>
              <strong>$ {parseFloat(comprobante.importe_cancelado || 0).toFixed(2)}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '16px', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-color)', color: 'var(--primary-color)' }}>
              <span>Saldo Pendiente:</span>
              <strong>$ {remainingBalance.toFixed(2)}</strong>
            </div>
          </div>

          <form id="cancelacion-form" onSubmit={handleSubmit}>
            <div style={{ marginBottom: '16px' }}>
              <label className="form-label" style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>Fecha de Pago</label>
              <input 
                type="date" 
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-color)' }}
                name="fecha_cancelacion" 
                value={formData.fecha_cancelacion} 
                onChange={handleDateChange} 
                required 
              />
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label className="form-label" style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>Importe a Pagar</label>
              <CurrencyInput 
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-color)' }}
                className="form-control" 
                name="importe" 
                value={formData.importe} 
                onChange={(val, e) => handleChange(e || { target: { name: 'importe', value: val }})} 
                required 
              />
            </div>
          </form>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
          <button type="button" onClick={onClose} disabled={loading} style={{ padding: '8px 16px', borderRadius: '6px', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-color)', cursor: 'pointer' }}>
            Cancelar
          </button>
          <button type="submit" form="cancelacion-form" disabled={loading} style={{ padding: '8px 16px', borderRadius: '6px', background: 'var(--primary-color)', color: 'white', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Check size={18} /> Confirmar Pago
          </button>
        </div>
      </div>
    </div>
  );
};

export default CancelacionModal;
