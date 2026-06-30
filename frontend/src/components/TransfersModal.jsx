import { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const TransfersModal = ({ creditoId, onClose }) => {
  const [transferencias, setTransferencias] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTransferencias = async () => {
      setLoading(true);
      try {
        const res = await axiosClient.get(`/api/v1/creditos/${creditoId}/transferencias`);
        setTransferencias(res.data);
      } catch (error) {
        alert("Error cargando transferencias: " + error.message);
      } finally {
        setLoading(false);
      }
    };
    if (creditoId) {
      fetchTransferencias();
    }
  }, [creditoId]);

  return (
    <div className="modal-overlay" onClick={onClose} style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center',
      alignItems: 'center', zIndex: 9999, animation: 'fadeIn 0.3s'
    }}>
      <div className="modal-content glass-panel" onClick={e => e.stopPropagation()} style={{
        width: '600px', maxWidth: '90%', maxHeight: '80vh', overflowY: 'auto',
        padding: '24px', borderRadius: '12px', background: 'var(--surface-color)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0 }}>Transferencias - Crédito #{creditoId}</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-color)', fontSize: '24px', cursor: 'pointer' }}>&times;</button>
        </div>

        {loading ? (
          <p className="text-center">Cargando transferencias...</p>
        ) : transferencias.length === 0 ? (
          <p className="text-center" style={{ padding: '20px', opacity: 0.7 }}>No hay transferencias asociadas a este crédito.</p>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>CBU</th>
                  <th>CUIT</th>
                  <th>Razón Social</th>
                  <th>Monto</th>
                </tr>
              </thead>
              <tbody>
                {transferencias.map(t => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td>{t.cbu}</td>
                    <td>{t.cuit}</td>
                    <td>{t.razon_social}</td>
                    <td>{formatCurrency(t.monto)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default TransfersModal;
