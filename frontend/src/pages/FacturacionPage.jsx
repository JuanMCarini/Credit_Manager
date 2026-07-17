import { useState, useEffect, useCallback } from 'react';
import axiosClient from '../api/axiosClient';

const FacturacionPage = () => {
  const [pendientes, setPendientes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [procesando, setProcesando] = useState(false);
  
  // Para los rangos de fecha de descargas
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');

  const fetchPendientes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get('/api/v1/facturacion/pendientes');
      setPendientes(res.data);
    } catch (error) {
      console.error("Error cargando pendientes:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPendientes();
    
    // Set default dates to current month
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    
    setFechaDesde(firstDay.toISOString().split('T')[0]);
    setFechaHasta(lastDay.toISOString().split('T')[0]);
  }, [fetchPendientes]);

  const handleProcesar = async () => {
    if (!window.confirm(`¿Estás seguro que deseas procesar la facturación de ${pendientes.length} cobranzas?`)) return;
    
    setProcesando(true);
    try {
      const res = await axiosClient.post('/api/v1/facturacion/procesar');
      alert(res.data.message || "Proceso finalizado.");
      fetchPendientes(); // Refresh list
    } catch (error) {
      alert("Error procesando facturas: " + (error.response?.data?.detail || error.message));
    } finally {
      setProcesando(false);
    }
  };

  const downloadFile = (url, filename) => {
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDescargarLibro = () => {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    downloadFile(`${axiosClient.defaults.baseURL}/api/v1/facturacion/libro-iva?${params.toString()}`, 'libro_iva.xlsx');
  };

  const handleDescargarMasivo = () => {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    downloadFile(`${axiosClient.defaults.baseURL}/api/v1/facturacion/descargar-masivo?${params.toString()}`, 'facturas.zip');
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Gestión de Facturación (ARCA)</h2>
        <p>Visualizá cobranzas pendientes de facturar, procesá emisiones automáticas y descargá reportes.</p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '20px', alignItems: 'start' }}>
        
        {/* Panel Izquierdo - Pendientes */}
        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ margin: 0 }}>Cobranzas Pendientes ({pendientes.length})</h3>
            <button 
              className="btn-primary" 
              onClick={handleProcesar} 
              disabled={procesando || pendientes.length === 0}
            >
              {procesando ? 'Procesando...' : 'Procesar Facturación ⚡'}
            </button>
          </div>
          
          <div className="table-responsive" style={{ maxHeight: '400px', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID Cobranza</th>
                  <th>Fecha</th>
                  <th>Tipo</th>
                  <th style={{ textAlign: 'right' }}>Importe Total</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan="4" style={{ textAlign: 'center' }}>Cargando...</td></tr>
                ) : pendientes.length === 0 ? (
                  <tr><td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No hay cobranzas pendientes de facturar.</td></tr>
                ) : (
                  pendientes.map(p => (
                    <tr key={p.id}>
                      <td>#{p.id}</td>
                      <td>{p.fecha}</td>
                      <td>{p.tipo_cobranza}</td>
                      <td style={{ textAlign: 'right' }}>$ {p.importe_total.toFixed(2)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Panel Derecho - Reportes */}
        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}>
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            Reportes y Descargas 📥
          </h3>
          
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Fecha Desde</label>
            <input 
              type="date" 
              className="form-control" 
              value={fechaDesde} 
              onChange={e => setFechaDesde(e.target.value)} 
            />
          </div>
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Fecha Hasta</label>
            <input 
              type="date" 
              className="form-control" 
              value={fechaHasta} 
              onChange={e => setFechaHasta(e.target.value)} 
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <button className="btn-secondary" onClick={handleDescargarLibro} style={{ width: '100%', justifyContent: 'center' }}>
              Descargar Libro IVA (Excel)
            </button>
            <button className="btn-secondary" onClick={handleDescargarMasivo} style={{ width: '100%', justifyContent: 'center' }}>
              Descargar PDFs (ZIP)
            </button>
          </div>
        </div>

      </div>
    </section>
  );
};

export default FacturacionPage;
