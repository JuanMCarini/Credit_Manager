import { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const PortfolioLiquidationsPage = () => {
  const [liquidaciones, setLiquidaciones] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchLiquidaciones = async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get('/api/v1/liquidaciones');
      setLiquidaciones(res.data);
    } catch (error) {
      alert("Error cargando liquidaciones: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiquidaciones();
  }, []);

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Liquidaciones de Cartera</h2>
          <p>Listado de liquidaciones y rendiciones asociadas a las carteras de crédito.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', marginBottom: '8px' }}>
          <button className="btn-secondary" onClick={fetchLiquidaciones} disabled={loading} style={{ height: 'fit-content', width: 'fit-content', paddingLeft: '24px', paddingRight: '24px' }}>
            {loading ? 'Actualizando...' : 'Actualizar Datos'}
          </button>
        </div>
      </header>

      <div className="glass-panel" style={{ overflowX: 'auto', maxHeight: 'calc(100vh - 180px)', overflowY: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Cartera ID</th>
              <th>Cuota ID</th>
              <th>Cobranza ID</th>
              <th>Tipo</th>
              <th>Capital</th>
              <th>Interés</th>
              <th>IVA</th>
              <th>Total</th>
              <th>Fecha Pago</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {liquidaciones.length === 0 ? (
              <tr><td colSpan="11" className="text-center empty-state">{loading ? "Cargando..." : "No hay liquidaciones."}</td></tr>
            ) : (
              liquidaciones.map(l => (
                <tr key={l.id}>
                  <td>{l.id}</td>
                  <td>{l.cartera_id}</td>
                  <td>{l.cuota_id}</td>
                  <td>{l.cobranza_id || '-'}</td>
                  <td>{l.tipo_liquidacion}</td>
                  <td>${Number(l.capital).toFixed(2)}</td>
                  <td>${Number(l.interes).toFixed(2)}</td>
                  <td>${Number(l.iva).toFixed(2)}</td>
                  <td>${Number(l.importe_total).toFixed(2)}</td>
                  <td>{l.fecha_pago || '-'}</td>
                  <td>
                    <span className={`status-badge status-${l.cancelada ? 'vendida' : 'pendiente'}`}>
                      {l.cancelada ? 'Cancelada' : 'Pendiente'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default PortfolioLiquidationsPage;
