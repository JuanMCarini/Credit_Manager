import { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const PortfolioLiquidationsProcessingPage = () => {
  const [formData, setFormData] = useState({
    identificador: 'CLIENTE ID',
    id_val: '',
    fecha_corte: '',
    fecha_vencimiento_desde: '',
    fecha_vencimiento_hasta: ''
  });
  
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [compradores, setCompradores] = useState([]);
  const [filterText, setFilterText] = useState('');

  useEffect(() => {
    const fetchCompradores = async () => {
      try {
        const res = await axiosClient.get('/api/v1/liquidaciones/compradores');
        setCompradores(res.data);
        if (res.data.length > 0) {
          setFormData(prev => ({ ...prev, id_val: res.data[0].id.toString() }));
        }
      } catch (error) {
        console.error("Error fetching compradores:", error);
      }
    };
    fetchCompradores();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handlePreview = async (e) => {
    e.preventDefault();
    setLoading(true);
    setPreviewData(null);
    try {
      const payload = {
        ...formData,
        id_val: formData.id_val.includes(',') 
          ? formData.id_val.split(',').map(s => s.trim()) 
          : formData.id_val,
        fecha_corte: formData.fecha_corte || null,
        fecha_vencimiento_desde: formData.fecha_vencimiento_desde || null,
        fecha_vencimiento_hasta: formData.fecha_vencimiento_hasta || null
      };
      const res = await axiosClient.post('/api/v1/liquidaciones/preview', payload);
      setPreviewData(res.data);
    } catch (error) {
      alert("Error en la previsualización: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleProcess = async () => {
    if (!window.confirm("¿Estás seguro de procesar estas liquidaciones? Esta acción impactará en la base de datos.")) {
      return;
    }
    
    setProcessing(true);
    try {
      const payload = {
        ...formData,
        id_val: formData.id_val.includes(',') 
          ? formData.id_val.split(',').map(s => s.trim()) 
          : formData.id_val,
        fecha_corte: formData.fecha_corte || null,
        fecha_vencimiento_desde: formData.fecha_vencimiento_desde || null,
        fecha_vencimiento_hasta: formData.fecha_vencimiento_hasta || null
      };
      await axiosClient.post('/api/v1/liquidaciones/procesar', payload);
      alert("Liquidaciones procesadas exitosamente.");
      setPreviewData(null);
      // Reset form
      setFormData({
        identificador: 'CLIENTE ID',
        id_val: '',
        fecha_corte: '',
        fecha_vencimiento_desde: '',
        fecha_vencimiento_hasta: ''
      });
    } catch (error) {
      alert("Error al procesar: " + (error.response?.data?.detail || error.message));
    } finally {
      setProcessing(false);
    }
  };

  const filteredData = previewData ? previewData.filter(item => 
    item.cuota_id.toString().includes(filterText) ||
    item.cartera_id.toString().includes(filterText) ||
    item.tipo_liquidacion.toLowerCase().includes(filterText.toLowerCase()) ||
    (item.cobranza_id && item.cobranza_id.toString().includes(filterText))
  ) : [];

  const totalCapital = filteredData.reduce((acc, curr) => acc + Number(curr.capital), 0);
  const totalInteres = filteredData.reduce((acc, curr) => acc + Number(curr.interes), 0);
  const totalIva = filteredData.reduce((acc, curr) => acc + Number(curr.iva), 0);
  const totalGeneral = totalCapital + totalInteres + totalIva;

  const formatMoney = (amount) => {
    return '$ ' + new Intl.NumberFormat('es-AR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(Number(amount));
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <div>
          <h2>Procesar Nuevas Liquidaciones</h2>
          <p>Consulta y genera liquidaciones para socios comerciales en base a la cobranza registrada y los vencimientos.</p>
        </div>
      </header>

      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <form onSubmit={handlePreview} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          
          <div className="form-group">
            <label>Tipo de Identificador</label>
            <select name="identificador" value={formData.identificador} onChange={handleInputChange} required className="form-control" disabled>
              <option value="CLIENTE ID">Socio ID</option>
            </select>
          </div>

          <div className="form-group">
            <label>Socio Comprador</label>
            <select name="id_val" value={formData.id_val} onChange={handleInputChange} required className="form-control">
              {compradores.map(c => (
                <option key={c.id} value={c.id}>
                  {c.razon_social} (CUIT: {c.cuit})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Fecha de Corte (opcional)</label>
            <input type="date" name="fecha_corte" value={formData.fecha_corte} onChange={handleInputChange} className="form-control" />
          </div>

          <div className="form-group">
            <label>Vencimiento Desde (opcional)</label>
            <input type="date" name="fecha_vencimiento_desde" value={formData.fecha_vencimiento_desde} onChange={handleInputChange} className="form-control" />
          </div>

          <div className="form-group">
            <label>Vencimiento Hasta (opcional)</label>
            <input type="date" name="fecha_vencimiento_hasta" value={formData.fecha_vencimiento_hasta} onChange={handleInputChange} className="form-control" />
          </div>

          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
            <button type="submit" className="btn-primary" disabled={loading || processing}>
              {loading ? 'Consultando...' : 'Previsualizar Liquidaciones'}
            </button>
          </div>
        </form>
      </div>

      {previewData && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', gap: '16px', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0, color: 'var(--text-primary)', flexShrink: 0 }}>Resultado de la Previsualización</h3>
            <div style={{ flex: 1, minWidth: '250px', maxWidth: '400px' }}>
              <input 
                type="text" 
                placeholder="Filtrar por Cuota, Cartera, Cobranza o Tipo..." 
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
                className="form-control"
              />
            </div>
            <button className="btn-primary" style={{ backgroundColor: 'var(--success-color)' }} onClick={handleProcess} disabled={processing || previewData.length === 0}>
              {processing ? 'Procesando...' : 'Confirmar y Ejecutar Transacción'}
            </button>
          </div>

          {filteredData.length === 0 ? (
            <div className="empty-state text-center">No se encontraron liquidaciones para mostrar.</div>
          ) : (
            <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
              <table className="data-table" style={{ position: 'relative' }}>
                <thead style={{ position: 'sticky', top: 0, zIndex: 10, backgroundColor: 'var(--bg-panel)' }}>
                  <tr>
                    <th>Cuota ID</th>
                    <th>Cartera ID</th>
                    <th>Cobranza ID</th>
                    <th>Tipo Liquidación</th>
                    <th>Capital</th>
                    <th>Interés</th>
                    <th>IVA</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredData.map((l, index) => (
                    <tr key={index}>
                      <td>{l.cuota_id}</td>
                      <td>{l.cartera_id}</td>
                      <td>{l.cobranza_id || '-'}</td>
                      <td>{l.tipo_liquidacion}</td>
                      <td>{formatMoney(l.capital)}</td>
                      <td>{formatMoney(l.interes)}</td>
                      <td>{formatMoney(l.iva)}</td>
                      <td>{formatMoney(Number(l.capital) + Number(l.interes) + Number(l.iva))}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot style={{ position: 'sticky', bottom: 0, zIndex: 10, backgroundColor: 'var(--bg-panel)', fontWeight: 'bold' }}>
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'right' }}>Totales:</td>
                    <td>{formatMoney(totalCapital)}</td>
                    <td>{formatMoney(totalInteres)}</td>
                    <td>{formatMoney(totalIva)}</td>
                    <td>{formatMoney(totalGeneral)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default PortfolioLiquidationsProcessingPage;
