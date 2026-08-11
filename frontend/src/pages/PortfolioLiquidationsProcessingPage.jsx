import { useState, useEffect, useMemo } from 'react';
import { FilterX } from 'lucide-react';
import axiosClient from '../api/axiosClient';
import ExcelDateFilter from '../components/ExcelDateFilter';
import ExcelListFilter from '../components/ExcelListFilter';
import ExportExcelButton from '../components/ExportExcelButton';

const PortfolioLiquidationsProcessingPage = () => {
  const [formData, setFormData] = useState({
    identificador: 'CLIENTE ID',
    id_val: '',
    fecha_corte: '',
    fecha_vencimiento_desde: '',
    fecha_vencimiento_hasta: '',
    con_recurso: false
  });
  
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [compradores, setCompradores] = useState([]);
  const [filters, setFilters] = useState({
    credito_id: [],
    nro_cuota: '',
    fecha_vencimiento: [],
    cartera_id: '',
    tipo_liquidacion: []
  });

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
        fecha_vencimiento_hasta: formData.fecha_vencimiento_hasta || null,
        con_recurso: formData.con_recurso
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
        fecha_vencimiento_hasta: formData.fecha_vencimiento_hasta || null,
        con_recurso: formData.con_recurso
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
        fecha_vencimiento_hasta: '',
        con_recurso: false
      });
    } catch (error) {
      alert("Error al procesar: " + (error.response?.data?.detail || error.message));
    } finally {
      setProcessing(false);
    }
  };

  const handleFilterChange = (e, field) => {
    setFilters(prev => ({ ...prev, [field]: e.target.value }));
  };

  const uniqueTipos = previewData ? [...new Set(previewData.map(item => item.tipo_liquidacion))] : [];
  const uniqueCreditos = previewData ? [...new Set(previewData.map(item => item.credito_id))].sort((a,b)=>a-b).map(String) : [];

  const uniqueVencimientos = useMemo(() => {
    if (!previewData) return [];
    return [...new Set(previewData.map(d => d.fecha_vencimiento))].sort();
  }, [previewData]);

  const filteredData = previewData ? previewData.filter(item => {
    return (
      (filters.credito_id.length === 0 || filters.credito_id.includes(String(item.credito_id))) &&
      (filters.nro_cuota === '' || String(item.nro_cuota).includes(filters.nro_cuota)) &&
      (filters.fecha_vencimiento.length === 0 || filters.fecha_vencimiento.includes(item.fecha_vencimiento)) &&
      (filters.cartera_id === '' || String(item.cartera_id).includes(filters.cartera_id)) &&
      (filters.tipo_liquidacion.length === 0 || filters.tipo_liquidacion.includes(item.tipo_liquidacion))
    );
  }) : [];

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

          <div className="form-group">
            <label>Tipo de Operación</label>
            <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
              <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', gap: '8px', fontSize: '14px', color: 'var(--text-primary)' }}>
                <div className="toggle-switch">
                  <input 
                    type="checkbox" 
                    checked={formData.con_recurso} 
                    onChange={(e) => setFormData(prev => ({ ...prev, con_recurso: e.target.checked }))}
                  />
                  <span className="slider"></span>
                </div>
                {formData.con_recurso ? 'Operaciones Con Recurso' : 'Operaciones Sin Recurso'}
              </label>
            </div>
          </div>

          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
            <button type="submit" className="btn-primary" disabled={loading || processing}>
              {loading ? '⏳ Consultando...' : 'Previsualizar Liquidaciones'}
            </button>
          </div>
        </form>
      </div>

      {previewData && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', gap: '16px', flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0, color: 'var(--text-primary)', flexShrink: 0 }}>Resultado de la Previsualización</h3>
            
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <button 
                className="btn-secondary" 
                onClick={() => setFilters({ credito_id: [], nro_cuota: '', fecha_vencimiento: [], cartera_id: '', tipo_liquidacion: [] })}
                title="Limpiar todos los filtros"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', height: '100%', padding: '0 12px' }}
              >
                <FilterX size={16} /> Limpiar Filtros
              </button>
              <ExportExcelButton 
                data={previewData} 
                filteredData={filteredData} 
                filename="preview_liquidaciones_export" 
              />
              <button 
                className="btn-primary" 
              style={{ 
                background: 'linear-gradient(135deg, #10b981, #059669)', 
                color: 'white', 
                fontWeight: 'bold', 
                padding: '12px 28px', 
                fontSize: '1.05rem',
                boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)',
                border: 'none',
                borderRadius: '8px',
                transition: 'all 0.3s ease',
                cursor: processing || previewData.length === 0 ? 'not-allowed' : 'pointer',
                opacity: processing || previewData.length === 0 ? 0.6 : 1
              }} 
              onClick={handleProcess} 
              disabled={processing || previewData.length === 0}
              onMouseOver={(e) => {
                if (!processing && previewData.length > 0) {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 6px 20px rgba(16, 185, 129, 0.6)';
                }
              }}
              onMouseOut={(e) => {
                if (!processing && previewData.length > 0) {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 4px 15px rgba(16, 185, 129, 0.4)';
                }
              }}
            >
              {processing ? '⏳ Procesando...' : '🚀 Confirmar y Ejecutar Transacciones'}
            </button>
            </div>
          </div>

          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            <table className="data-table" style={{ position: 'relative' }}>
              <thead style={{position: 'sticky', top: 0, zIndex: 10, backgroundColor: 'var(--bg-panel)'}}>
                <tr>
                  <th>Cuota ID</th>
                  <th>
                    Cartera ID
                    <input type="text" placeholder="Filtrar..." value={filters.cartera_id} onChange={(e) => handleFilterChange(e, 'cartera_id')} style={{ display: 'block', width: '100%', marginTop: '4px', padding: '4px', fontSize: '0.8rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-primary)', borderRadius: '4px' }} />
                  </th>
                  <th>Cobranza ID</th>
                  <th>
                    Tipo Liquidación
                    {uniqueTipos.length > 0 && (
                      <div style={{ marginTop: '5px' }}>
                        <ExcelListFilter 
                          availableOptions={uniqueTipos}
                          selectedOptions={filters.tipo_liquidacion}
                          onChange={(newTypes) => setFilters(prev => ({ ...prev, tipo_liquidacion: newTypes }))}
                          title="Filtrar Tipos..."
                        />
                      </div>
                    )}
                  </th>
                  <th>
                    Crédito ID
                    {uniqueCreditos.length > 0 && (
                      <div style={{ marginTop: '5px' }}>
                        <ExcelListFilter 
                          availableOptions={uniqueCreditos}
                          selectedOptions={filters.credito_id}
                          onChange={(newIds) => setFilters(prev => ({ ...prev, credito_id: newIds }))}
                          title="Filtrar IDs..."
                        />
                      </div>
                    )}
                  </th>
                  <th>
                    Nro Cuota
                    <input type="text" placeholder="Filtrar..." value={filters.nro_cuota} onChange={(e) => handleFilterChange(e, 'nro_cuota')} style={{ display: 'block', width: '100%', marginTop: '4px', padding: '4px', fontSize: '0.8rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-primary)', borderRadius: '4px' }} />
                  </th>
                  <th style={{minWidth: '220px'}}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      Vencimiento
                    </div>
                    {uniqueVencimientos.length > 0 && (
                      <ExcelDateFilter 
                        availableDates={uniqueVencimientos}
                        selectedDates={filters.fecha_vencimiento}
                        onChange={(newDates) => setFilters(prev => ({ ...prev, fecha_vencimiento: newDates }))}
                      />
                    )}
                  </th>
                  <th>Capital</th>
                  <th>Interés</th>
                  <th>IVA</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {filteredData.length === 0 ? (
                  <tr>
                    <td colSpan="11" className="text-center" style={{ padding: '32px 0' }}>
                      <div className="empty-state">No se encontraron liquidaciones con esos filtros.</div>
                    </td>
                  </tr>
                ) : (
                  filteredData.map((l, index) => (
                    <tr key={index}>
                      <td>{l.cuota_id}</td>
                      <td>{l.cartera_id}</td>
                      <td>{l.cobranza_id || '-'}</td>
                      <td>{l.tipo_liquidacion}</td>
                      <td>{l.credito_id}</td>
                      <td>{l.nro_cuota}</td>
                      <td>{l.fecha_vencimiento}</td>
                      <td>{formatMoney(l.capital)}</td>
                      <td>{formatMoney(l.interes)}</td>
                      <td>{formatMoney(l.iva)}</td>
                      <td>{formatMoney(Number(l.capital) + Number(l.interes) + Number(l.iva))}</td>
                    </tr>
                  ))
                )}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan="7" style={{ textAlign: 'right' }}>Totales:</td>
                  <td>{formatMoney(totalCapital)}</td>
                  <td>{formatMoney(totalInteres)}</td>
                  <td>{formatMoney(totalIva)}</td>
                  <td>{formatMoney(totalGeneral)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </section>
  );
};

export default PortfolioLiquidationsProcessingPage;
