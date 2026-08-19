import React, { useState, useEffect } from 'react';
import axiosClient from '../../api/axiosClient';

import { X } from 'lucide-react';

const ModalAsignarCheque = ({ isOpen, onClose, onSave, movimiento }) => {
  const [chequesDisponibles, setChequesDisponibles] = useState([]);
  const [loadingCheques, setLoadingCheques] = useState(false);
  const [chequeSearch, setChequeSearch] = useState('');

  useEffect(() => {
    if (isOpen && movimiento) {
      fetchCheques();
      setChequeSearch('');
    }
  }, [isOpen, movimiento]);

  const fetchCheques = async () => {
    setLoadingCheques(true);
    try {
      const res = await axiosClient.get('/api/cheques/');
      // Filtrar cheques: no vinculados, y que sean validos para débito o crédito
      const disponibles = res.data.filter(c => 
        !c.movimiento_id && (
          (c.es_propio && c.estado !== 'DEBITADO') ||
          (!c.es_propio && c.is_beneficiario_empresa && c.estado !== 'ACREDITADO')
        )
      );
      setChequesDisponibles(disponibles);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCheques(false);
    }
  };

  const handleAsignarCheque = async (chequeId) => {
    try {
      await axiosClient.post(`/api/cheques/${chequeId}/asignar_movimiento`, {
        movimiento_id: movimiento.id
      });
      onSave(); // Trigger the refresh
    } catch (err) {
      console.error(err);
      alert('Error al asignar el cheque.');
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="modal-content" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto', boxShadow: 'var(--shadow-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0 }}>Asignar Cheque al Movimiento</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={24} /></button>
        </div>
        <div className="modal-body">
          <p>Seleccioná un cheque disponible para asignar a este movimiento de <strong>{formatCurrency(movimiento?.monto)}</strong>.</p>
          
          <div style={{ marginBottom: '15px' }}>
            <input 
              type="text" 
              placeholder="Buscar cheque por número o emisor..." 
              className="form-control"
              value={chequeSearch}
              onChange={e => setChequeSearch(e.target.value)}
            />
          </div>

          {loadingCheques ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>Cargando cheques...</div>
          ) : (
            <div className="table-responsive" style={{ maxHeight: '400px', overflowY: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Número</th>
                    <th>Emisor</th>
                    <th>Propio</th>
                    <th>Fecha de Pago</th>
                    <th style={{ textAlign: 'right' }}>Monto</th>
                    <th style={{ textAlign: 'center' }}>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {chequesDisponibles.filter(c => 
                    c.numero.toLowerCase().includes(chequeSearch.toLowerCase()) || 
                    (c.emisor?.razon_social || '').toLowerCase().includes(chequeSearch.toLowerCase())
                  ).map(c => (
                    <tr key={c.id}>
                      <td>{c.numero}</td>
                      <td>{c.emisor?.razon_social || 'Desconocido'}</td>
                      <td style={{ textAlign: 'center' }}>
                        {c.es_propio ? 'Sí' : 'No'}
                      </td>
                      <td>{c.fecha_pago}</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(c.monto)}</td>
                      <td style={{ textAlign: 'center' }}>
                        <button className="btn-primary" style={{ padding: '4px 8px', fontSize: '12px', width: 'auto' }} onClick={() => handleAsignarCheque(c.id)}>
                          Asignar
                        </button>
                      </td>
                    </tr>
                  ))}
                  {chequesDisponibles.length === 0 && (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '20px' }}>No hay cheques disponibles para asignar.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ModalAsignarCheque;
