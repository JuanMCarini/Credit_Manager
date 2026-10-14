import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { FilterX } from 'lucide-react';
import axiosClient from '../api/axiosClient';
import ExcelDateFilter from '../components/ExcelDateFilter';
import ExcelListFilter from '../components/ExcelListFilter';
import ExportExcelButton from '../components/ExportExcelButton';
import ProcesosCobranzaSelector from '../components/ProcesosCobranzaSelector';

const PortfolioLiquidationsProcessingPage = () => {
  const [formData, setFormData] = useState({
    identificador: 'CLIENTE ID',
    id_val: '',
    fecha_corte: '',
    fecha_vencimiento_desde: '',
    fecha_vencimiento_hasta: '',
    con_recurso: false,
    procesos_cobranza_id: []
  });
  
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [compradores, setCompradores] = useState([]);
  const [procesos, setProcesos] = useState([]);
  const [filters, setFilters] = useState({
    credito_id: [],
    nro_cuota: '',
    fecha_vencimiento: [],
    cartera_id: '',
    tipo_liquidacion: [],
    fecha_emision_cobranza: []
  });

  const fetchCompradores = useCallback(async () => {
    try {
      const res = await axiosClient.get('/api/v1/liquidaciones/compradores');
      setCompradores(res.data);
      if (res.data.length > 0) {
        setFormData(prev => ({ 
          ...prev, 
          id_val: prev.id_val || res.data[0].id.toString() 
        }));
      }
    } catch (error) {
      console.error("Error fetching compradores:", error);
    }
  }, []);

  const fetchProcesos = useCallback(async () => {
    try {
      const res = await axiosClient.get(`/api/v1/procesos?t=${Date.now()}`);
      // Filter only actual collection processes (MASIVO_CSV, INDIVIDUAL, RECURSO), excluding liquidation processes and reverted/failed ones
      const validProcesos = (res.data || []).filter(p => 
        ['MASIVO_CSV', 'INDIVIDUAL', 'RECURSO'].includes(p.Tipo) &&
        p.Estado !== 'REVERTIDO' &&
        p.Estado !== 'FALLIDO'
      );
      setProcesos(validProcesos);
    } catch (error) {
      console.error("Error fetching procesos:", error);
    }
  }, []);

  useEffect(() => {
    fetchCompradores();
    fetchProcesos();
  }, [fetchCompradores, fetchProcesos]);

  // Keep id_val in sync whenever compradores load
  useEffect(() => {
    if (compradores.length > 0 && !formData.id_val) {
      setFormData(prev => ({ ...prev, id_val: compradores[0].id.toString() }));
    }
  }, [compradores, formData.id_val]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleProcesosChange = (e) => {
    const values = Array.from(e.target.selectedOptions, option => parseInt(option.value));
    setFormData(prev => ({ ...prev, procesos_cobranza_id: values }));
  };

  const initialFilters = {
    credito_id: [],
    nro_cuota: '',
    fecha_vencimiento: [],
    cartera_id: '',
    tipo_liquidacion: [],
    fecha_emision_cobranza: []
  };

  const handlePreview = async (e) => {
    e.preventDefault();
    setLoading(true);
    setPreviewData(null);
    setFilters(initialFilters);

    const targetIdVal = formData.id_val || (compradores.length > 0 ? compradores[0].id.toString() : '');
    if (!targetIdVal) {
      alert("Por favor seleccione un socio comprador.");
      setLoading(false);
      return;
    }

    if (formData.id_val !== targetIdVal) {
      setFormData(prev => ({ ...prev, id_val: targetIdVal }));
    }

    try {
      const payload = {
        ...formData,
        id_val: targetIdVal.includes(',') 
          ? targetIdVal.split(',').map(s => s.trim()) 
          : targetIdVal,
        fecha_corte: formData.fecha_corte || null,
        fecha_vencimiento_desde: formData.fecha_vencimiento_desde || null,
        fecha_vencimiento_hasta: formData.fecha_vencimiento_hasta || null,
        con_recurso: formData.con_recurso,
        procesos_cobranza_id: formData.procesos_cobranza_id && formData.procesos_cobranza_id.length > 0 
          ? formData.procesos_cobranza_id 
          : null
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
    const targetIdVal = formData.id_val || (compradores.length > 0 ? compradores[0].id.toString() : '');
    try {
      const payload = {
        ...formData,
        id_val: targetIdVal.includes(',') 
          ? targetIdVal.split(',').map(s => s.trim()) 
          : targetIdVal,
        fecha_corte: formData.fecha_corte || null,
        fecha_vencimiento_desde: formData.fecha_vencimiento_desde || null,
        fecha_vencimiento_hasta: formData.fecha_vencimiento_hasta || null,
        con_recurso: formData.con_recurso,
        procesos_cobranza_id: formData.procesos_cobranza_id && formData.procesos_cobranza_id.length > 0 
          ? formData.procesos_cobranza_id 
          : null
      };
      await axiosClient.post('/api/v1/liquidaciones/procesar', payload);
      alert("Liquidaciones procesadas exitosamente.");
      setPreviewData(null);
      setFilters(initialFilters);
      // Reset form maintaining first comprador selected
      setFormData({
        identificador: 'CLIENTE ID',
        id_val: compradores.length > 0 ? compradores[0].id.toString() : '',
        fecha_corte: '',
        fecha_vencimiento_desde: '',
        fecha_vencimiento_hasta: '',
        con_recurso: false,
        procesos_cobranza_id: []
      });
      // Refresh processes
      fetchProcesos();
    } catch (error) {
      alert("Error al procesar: " + (error.response?.data?.detail || error.message));
    } finally {
      setProcessing(false);
    }
  };

  const handleFilterChange = (e, field) => {
    setFilters(prev => ({ ...prev, [field]: e.target.value }));
  };

  const matchesPreviewFilter = (item, currentFilters, excludeField = null) => {
    if (excludeField !== 'credito_id' && currentFilters.credito_id.length > 0 && !currentFilters.credito_id.includes(String(item.credito_id))) return false;
    if (excludeField !== 'nro_cuota' && currentFilters.nro_cuota !== '' && !String(item.nro_cuota).includes(currentFilters.nro_cuota)) return false;
    if (excludeField !== 'fecha_vencimiento' && currentFilters.fecha_vencimiento.length > 0 && !currentFilters.fecha_vencimiento.includes(item.fecha_vencimiento)) return false;
    if (excludeField !== 'fecha_emision_cobranza' && currentFilters.fecha_emision_cobranza.length > 0 && !currentFilters.fecha_emision_cobranza.includes(item.fecha_emision_cobranza)) return false;
    if (excludeField !== 'cartera_id' && currentFilters.cartera_id !== '' && !String(item.cartera_id).includes(currentFilters.cartera_id)) return false;
    if (excludeField !== 'tipo_liquidacion' && currentFilters.tipo_liquidacion.length > 0 && !currentFilters.tipo_liquidacion.includes(item.tipo_liquidacion)) return false;
    return true;
  };

  const uniqueTipos = useMemo(() => {
    if (!previewData) return [];
    const subset = previewData.filter(item => matchesPreviewFilter(item, filters, 'tipo_liquidacion'));
    return [...new Set(subset.map(item => item.tipo_liquidacion))];
  }, [previewData, filters]);

  const uniqueCreditos = useMemo(() => {
    if (!previewData) return [];
    const subset = previewData.filter(item => matchesPreviewFilter(item, filters, 'credito_id'));
    return [...new Set(subset.map(item => item.credito_id))].sort((a,b)=>a-b).map(String);
  }, [previewData, filters]);

  const uniqueVencimientos = useMemo(() => {
    if (!previewData) return [];
    const subset = previewData.filter(item => matchesPreviewFilter(item, filters, 'fecha_vencimiento'));
    return [...new Set(subset.map(d => d.fecha_vencimiento))].sort();
  }, [previewData, filters]);

  const uniqueFechasEmisionCobranza = useMemo(() => {
    if (!previewData) return [];
    const subset = previewData.filter(item => matchesPreviewFilter(item, filters, 'fecha_emision_cobranza'));
    return [...new Set(subset.map(d => d.fecha_emision_cobranza).filter(Boolean))].sort();
  }, [previewData, filters]);

  const filteredData = previewData ? previewData.filter(item => matchesPreviewFilter(item, filters)) : [];

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
        <form onSubmit={handlePreview} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', alignItems: 'end' }}>
          
          <div className="form-group">
            <label>Tipo de Identificador</label>
            <select name="identificador" value={formData.identificador} onChange={handleInputChange} required className="form-control" disabled>
              <option value="CLIENTE ID">Socio ID</option>
            </select>
          </div>

          <div className="form-group">
            <label>Socio Comprador</label>
            <select 
              name="id_val" 
              value={formData.id_val || (compradores.length > 0 ? compradores[0].id.toString() : '')} 
              onChange={handleInputChange} 
              required 
              className="form-control"
            >
              {compradores.map(c => (
                <option key={c.id} value={c.id.toString()}>
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
            <label>Tipo de Operación</label>
            <div style={{ display: 'flex', alignItems: 'center', height: '42px' }}>
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

          <div className="form-group">
            <label>Vencimiento Desde (opcional)</label>
            <input type="date" name="fecha_vencimiento_desde" value={formData.fecha_vencimiento_desde} onChange={handleInputChange} className="form-control" />
          </div>

          <div className="form-group">
            <label>Vencimiento Hasta (opcional)</label>
            <input type="date" name="fecha_vencimiento_hasta" value={formData.fecha_vencimiento_hasta} onChange={handleInputChange} className="form-control" />
          </div>

          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Procesos de Cobranza (Opcional)</span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                {procesos.length} proceso{procesos.length !== 1 ? 's' : ''} disponible{procesos.length !== 1 ? 's' : ''}
              </span>
            </label>
            <ProcesosCobranzaSelector 
              procesos={procesos}
              selectedIds={formData.procesos_cobranza_id}
              onChange={(newIds) => setFormData(prev => ({ ...prev, procesos_cobranza_id: newIds }))}
              placeholder="Todos los procesos (Sin filtro - se procesarán todas las cobranzas pendientes)"
            />
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
                onClick={() => setFilters({ credito_id: [], nro_cuota: '', fecha_vencimiento: [], cartera_id: '', tipo_liquidacion: [], fecha_emision_cobranza: [] })}
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
                  <th style={{minWidth: '220px'}}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      Fecha Emisión Cob.
                    </div>
                    {uniqueFechasEmisionCobranza.length > 0 && (
                      <ExcelDateFilter 
                        availableDates={uniqueFechasEmisionCobranza}
                        selectedDates={filters.fecha_emision_cobranza}
                        onChange={(newDates) => setFilters(prev => ({ ...prev, fecha_emision_cobranza: newDates }))}
                      />
                    )}
                  </th>
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
                    <td colSpan="12" className="text-center" style={{ padding: '32px 16px' }}>
                      {previewData.length > 0 ? (
                        <div className="empty-state" style={{ color: '#f59e0b', maxWidth: '640px', margin: '0 auto', textAlign: 'center' }}>
                          <p style={{ margin: '0 0 12px 0', fontSize: '1rem', fontWeight: '500' }}>
                            ⚠️ Se obtuvieron <strong>{previewData.length}</strong> liquidaciones, pero están ocultas por los filtros aplicados en las columnas.
                          </p>
                          <button 
                            type="button"
                            className="btn-secondary" 
                            onClick={() => setFilters(initialFilters)} 
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', margin: '0 auto' }}
                          >
                            <FilterX size={16} /> Limpiar Filtros de Columnas
                          </button>
                        </div>
                      ) : (
                        <div className="empty-state">
                          No se encontraron liquidaciones para los criterios seleccionados. Verifique que existan cobranzas pendientes para este socio y fecha de corte.
                        </div>
                      )}
                    </td>
                  </tr>
                ) : (
                  filteredData.map((l, index) => (
                    <tr key={index}>
                      <td>{l.cuota_id}</td>
                      <td>{l.cartera_id}</td>
                      <td>{l.cobranza_id || '-'}</td>
                      <td>{l.fecha_emision_cobranza || '-'}</td>
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
                  <td colSpan="8" style={{ textAlign: 'right' }}>Totales:</td>
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
