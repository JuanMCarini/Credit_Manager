import React, { useState, useEffect, useMemo } from 'react';
import { X, Check } from 'lucide-react';
import axiosClient from '../../api/axiosClient';

const MovimientoPagoModal = ({ isOpen, onClose, onSave, movimiento }) => {
  const [comprobantes, setComprobantes] = useState([]);
  const [selectedComprobanteIds, setSelectedComprobanteIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchComprobantes();
      setSelectedComprobanteIds([]);
      setError('');
    }
  }, [isOpen]);

  const fetchComprobantes = async () => {
    setFetching(true);
    try {
      const res = await axiosClient.get('/api/finanzas/comprobantes');
      const data = res.data.filter(c => {
        const montoMov = parseFloat(movimiento.monto);
        if (montoMov < 0) {
          // If negative movement, we can select any comprobante that has importe_cancelado > 0
          return parseFloat(c.importe_cancelado || 0) > 0;
        } else {
          // If positive movement, we can only select comprobantes that are not fully paid
          return c.estado !== 'pagado';
        }
      }).sort((a, b) => {
        const dateA = a.fecha_vencimiento ? new Date(a.fecha_vencimiento) : new Date(8640000000000000); // Max date if no vencimiento
        const dateB = b.fecha_vencimiento ? new Date(b.fecha_vencimiento) : new Date(8640000000000000);
        return dateA - dateB;
      });
      setComprobantes(data);
    } catch (err) {
      console.error(err);
      setError('Error al cargar comprobantes.');
    } finally {
      setFetching(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  const toggleComprobante = (id) => {
    setSelectedComprobanteIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (selectedComprobanteIds.length === 0) {
      setError('Debe seleccionar al menos un comprobante.');
      return;
    }
    
    setLoading(true);
    setError('');

    let remainingSaldo = movimiento.saldo_disponible > 0 ? movimiento.saldo_disponible : Math.abs(parseFloat(movimiento.monto));

    // Get selected and sort by expiration date ascending (oldest first)
    const selected = comprobantes
      .filter(c => selectedComprobanteIds.includes(c.id))
      .sort((a, b) => {
        const dateA = a.fecha_vencimiento ? new Date(a.fecha_vencimiento) : new Date(8640000000000000);
        const dateB = b.fecha_vencimiento ? new Date(b.fecha_vencimiento) : new Date(8640000000000000);
        return dateA - dateB;
      });

    try {
      for (const c of selected) {
        if (remainingSaldo <= 0) break;

        let amountToPay = 0;
        const montoMov = parseFloat(movimiento.monto);
        
        if (montoMov < 0) {
          // Si el movimiento es negativo, estamos revirtiendo pagos.
          // El límite es lo que ya se pagó (importe_cancelado)
          const amountPaid = parseFloat(c.importe_cancelado || 0);
          amountToPay = Math.min(remainingSaldo, amountPaid);
        } else {
          // Si es positivo, estamos pagando el comprobante.
          // El límite es el saldo pendiente.
          const saldoComprobante = Math.max(0, parseFloat(c.importe_total) - parseFloat(c.importe_cancelado || 0));
          amountToPay = Math.min(remainingSaldo, saldoComprobante);
        }
        
        // If we found an amount to pay/revert
        if (amountToPay > 0) {
          const payload = {
            importe: amountToPay,
            fecha_cancelacion: movimiento.fecha,
            movimiento_id: movimiento.id
          };
          
          await axiosClient.post(`/api/finanzas/comprobantes/${c.id}/cancelaciones`, payload);
          remainingSaldo -= amountToPay;
        }
      }
      onSave(); // Refresca lista y cierra
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Error al registrar los pagos.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !movimiento) return null;

  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="modal-content" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '500px', maxHeight: '90vh', overflowY: 'auto', boxShadow: 'var(--shadow-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0 }}>Vincular a Comprobante</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={24} /></button>
        </div>
        
        <div>
          {error && <div className="alert alert-error" style={{ marginBottom: '16px', padding: '12px', background: '#ffebee', color: '#c62828', borderRadius: '6px' }}>{error}</div>}
          
          <div style={{ marginBottom: '20px', padding: '12px', backgroundColor: 'var(--surface-color)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: 'var(--text-muted)' }}>
              Detalle del Movimiento Bancario
            </p>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '15px', marginBottom: '4px' }}>
              <span>Fecha:</span>
              <strong>{movimiento.fecha}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '15px', marginBottom: '4px' }}>
              <span>Descripción:</span>
              <strong>{movimiento.descripcion || '-'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '16px', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border-color)', color: 'var(--primary-color)' }}>
              <span>Saldo Disponible a Imputar:</span>
              <strong>{formatCurrency(movimiento.saldo_disponible !== undefined ? movimiento.saldo_disponible : movimiento.monto)}</strong>
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '20px' }}>
              <label className="form-label" style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>Seleccionar Comprobantes Pendientes</label>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                Se distribuirá el saldo disponible a los comprobantes seleccionados, ordenados por vencimiento (el más antiguo primero).
              </div>
              {fetching ? (
                <div style={{ padding: '8px', color: 'var(--text-muted)' }}>Cargando comprobantes...</div>
              ) : (
                <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {comprobantes.length === 0 && <div style={{ color: 'var(--text-muted)', padding: '8px' }}>No hay comprobantes pendientes.</div>}
                  {comprobantes.map(c => {
                    const numStr = `${c.tipo_comprobante} ${String(c.punto_venta).padStart(4, '0')}-${String(c.numero_comprobante).padStart(8, '0')}`;
                    const saldo = Math.max(0, parseFloat(c.importe_total) - parseFloat(c.importe_cancelado || 0));
                    const isSelected = selectedComprobanteIds.includes(c.id);
                    return (
                      <label key={c.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '8px', backgroundColor: isSelected ? 'rgba(var(--primary-rgb), 0.05)' : 'transparent', borderRadius: '4px', cursor: 'pointer', border: isSelected ? '1px solid var(--primary-color)' : '1px solid transparent' }}>
                        <input 
                          type="checkbox" 
                          checked={isSelected}
                          onChange={() => toggleComprobante(c.id)}
                          style={{ marginTop: '4px' }}
                        />
                        <div>
                          <div style={{ fontWeight: '500' }}>{numStr} | {c.proveedor?.razon_social}</div>
                          <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Vence: {c.fecha_vencimiento || 'Sin fecha'} | Saldo: {formatCurrency(saldo)}</div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
              <button type="button" className="btn btn-outline" onClick={onClose} disabled={loading}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading || selectedComprobanteIds.length === 0} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={18} /> {loading ? 'Procesando...' : 'Registrar Pagos'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default MovimientoPagoModal;
