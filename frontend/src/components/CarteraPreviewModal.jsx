import { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const CarteraPreviewModal = ({ cartera, onClose, onSuccess, isReadOnly = false }) => {
  const [loading, setLoading] = useState(false);
  const [usarCuotasGuardadas, setUsarCuotasGuardadas] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  const [editData, setEditData] = useState({
    tna: (cartera.tna_descuento * 100).toString(),
    fecha: cartera.fecha_compra,
    nombre: cartera.nombre,
    socio: cartera.socio || '',
    recurso: cartera.recurso,
    iva: cartera.iva,
    mora: false, cuotas_completas: false, emision_desde: '', emision_hasta: '', vto_desde: '', vto_hasta: ''
  });
  
  const [previewData, setPreviewData] = useState(null);
  const [previewTab, setPreviewTab] = useState('resumen');
  const [creditosExcluidos, setCreditosExcluidos] = useState([]);
  
  const [filterCreditos, setFilterCreditos] = useState({});
  const [filterCuotas, setFilterCuotas] = useState({});
  const [filterResumen, setFilterResumen] = useState({});
  const [showPreviewEstadoFilter, setShowPreviewEstadoFilter] = useState(false);
  const [showPreviewIncluidaFilter, setShowPreviewIncluidaFilter] = useState(false);
  const [showPreviewCompradaFilter, setShowPreviewCompradaFilter] = useState(false);

  const fetchPreview = async (usar_guardadas, overrides = {}) => {
    setLoading(true);
    try {

      if (cartera.tipo_operacion === 'COMPRA') {
        const res = await axiosClient.get(`/api/v1/carteras/compra/${cartera.id}/preview`);
        setPreviewData(res.data);
      } else {
        const payload = {
          cartera_id: cartera.id,
          usar_cuotas_guardadas: usar_guardadas,
          creditos_excluidos: overrides.excluidos !== undefined ? overrides.excluidos : creditosExcluidos,
          nombre_cartera: editData.nombre || 'Edicion',
          fecha_venta: overrides.fecha || editData.fecha,
          tna_descuento: parseFloat(overrides.tna || editData.tna) / 100,
          cuit_comprador: '',
          razon_social_comprador: editData.socio || '-',
          mora: editData.mora,
          recurso: editData.recurso,
          iva: editData.iva,
          cuotas_completas: editData.cuotas_completas,
          fecha_emision_desde: editData.emision_desde || null,
          fecha_emision_hasta: editData.emision_hasta || null,
          fecha_vencimiento_desde: editData.vto_desde || null,
          fecha_vencimiento_hasta: editData.vto_hasta || null,
        };
        const res = await axiosClient.post('/api/v1/carteras/venta/preview', payload);
        setPreviewData(res.data);
      }
    } catch (err) {
      alert("Error en previsualización: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPreview(true);
  }, []);

  const handleFilterChange = (field, value) => {
    if (previewTab === 'resumen') setFilterResumen({...filterResumen, [field]: value});
    else if (previewTab === 'creditos') setFilterCreditos({...filterCreditos, [field]: value});
    else setFilterCuotas({...filterCuotas, [field]: value});
  };

  const handleRecalcular = () => fetchPreview(usarCuotasGuardadas);
  
  const handleRegenerar = () => {
    setUsarCuotasGuardadas(false);
    fetchPreview(false);
  };
  
  const handleToggleExcluir = (id) => {
    const newExcluidos = creditosExcluidos.includes(id) ? creditosExcluidos.filter(x => x !== id) : [...creditosExcluidos, id];
    setCreditosExcluidos(newExcluidos);
    fetchPreview(usarCuotasGuardadas, { excluidos: newExcluidos });
  };
  
  const handleGuardarEdicion = async () => {
    setLoading(true);
    try {
      const payload = {
        cartera_id: cartera.id,
        usar_cuotas_guardadas: usarCuotasGuardadas,
        creditos_excluidos: creditosExcluidos,
        nombre_cartera: editData.nombre,
        fecha_venta: editData.fecha,
        tna_descuento: parseFloat(editData.tna) / 100,
        cuit_comprador: '', 
        razon_social_comprador: editData.socio || '-',
        mora: editData.mora,
        recurso: editData.recurso,
        iva: editData.iva,
        cuotas_completas: editData.cuotas_completas,
        fecha_emision_desde: editData.emision_desde || null,
        fecha_emision_hasta: editData.emision_hasta || null,
        fecha_vencimiento_desde: editData.vto_desde || null,
        fecha_vencimiento_hasta: editData.vto_hasta || null,
      };
      await axiosClient.put(`/api/v1/carteras/venta/${cartera.id}`, payload);
      onSuccess();
    } catch (err) {
      alert("Error al guardar edición: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  if (!previewData) {
    return (
      <div style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.8)', zIndex: 1000,
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}>
        <div style={{ color: 'white', fontSize: '20px' }}>Cargando previsualización...</div>
      </div>
    );
  }

  const tipoOperacion = cartera.tipo_operacion;
  
  return (

        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.8)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '10px',
          backdropFilter: 'blur(8px)'
        }}>
          <div className="glass-panel" style={{
            width: '95vw', maxWidth: '1600px', height: '95vh', display: 'flex', flexDirection: 'column', position: 'relative'
          }}>
            <button onClick={onClose} className="btn-secondary" style={{
              position: 'absolute', top: '12px', right: '16px', padding: '4px 12px', zIndex: 10
            }}>X</button>
            
            <div style={{ padding: '12px 24px 0', flexShrink: 0 }}>
              <h3 style={{ marginBottom: '4px', fontFamily: 'var(--font-heading)' }}>
                Simulación de {tipoOperacion === 'VENTA' ? 'Venta' : 'Compra'} de Cartera
              </h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '12px', fontSize: '14px' }}>
                Revise los créditos y cuotas {tipoOperacion === 'VENTA' ? 'que serán cedidos' : 'importados'} antes de confirmar la operación.
              </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '12px' }}>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <label>Nombre de Cartera</label>
                  <input type="text" value={editData.nombre} onChange={e => setEditData({...editData, nombre: e.target.value})} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-color)', color: 'var(--text-color)' }} disabled={isReadOnly} />
                </div>
                <div style={{ flex: 1, minWidth: '100px' }}>
                  <label>TNA (%)</label>
                  <input type="number" value={editData.tna} onChange={e => setEditData({...editData, tna: e.target.value})} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-color)', color: 'var(--text-color)' }} disabled={isReadOnly} />
                </div>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <label>Fecha de Operación</label>
                  <input type="date" value={editData.fecha} onChange={e => setEditData({...editData, fecha: e.target.value})} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-color)', color: 'var(--text-color)' }} disabled={isReadOnly} />
                </div>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
                  {!isReadOnly && <button type="button" className="btn-secondary" onClick={handleRecalcular}>Recalcular</button>}
                  {!isReadOnly && <button type="button" className="btn-secondary" onClick={() => setShowAdvanced(!showAdvanced)}>Filtros Avanzados</button>}
                </div>
              </div>
              {showAdvanced && (
                <div style={{ padding: '12px', background: 'rgba(0,0,0,0.1)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <h4 style={{ marginBottom: '8px', fontSize: '14px' }}>Filtros Avanzados (Re-generar selección)</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '12px' }}>
                    <div className="form-group">
                      <label>Emisión Crédito Desde</label>
                      <input type="date" value={editData.emision_desde} onChange={e => setEditData({...editData, emision_desde: e.target.value})} className="input-field" />
                    </div>
                    <div className="form-group">
                      <label>Emisión Crédito Hasta</label>
                      <input type="date" value={editData.emision_hasta} onChange={e => setEditData({...editData, emision_hasta: e.target.value})} className="input-field" />
                    </div>
                    <div className="form-group">
                      <label>Vencimiento Cuota Desde</label>
                      <input type="date" value={editData.vto_desde} onChange={e => setEditData({...editData, vto_desde: e.target.value})} className="input-field" />
                    </div>
                    <div className="form-group">
                      <label>Vencimiento Cuota Hasta</label>
                      <input type="date" value={editData.vto_hasta} onChange={e => setEditData({...editData, vto_hasta: e.target.value})} className="input-field" />
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px' }}>
                      <div className="toggle-switch">
                        <input type="checkbox" checked={editData.mora} onChange={e => setEditData({...editData, mora: e.target.checked})} />
                        <span className="slider"></span>
                      </div>
                      Incluir Mora
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                      <div className="toggle-switch">
                        <input type="checkbox" checked={editData.cuotas_completas} onChange={e => setEditData({...editData, cuotas_completas: e.target.checked})} />
                        <span className="slider"></span>
                      </div>
                      Cuotas Completas
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                      <div className="toggle-switch">
                        <input type="checkbox" checked={editData.recurso} onChange={e => setEditData({...editData, recurso: e.target.checked})} />
                        <span className="slider"></span>
                      </div>
                      Venta con Recurso
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                      <div className="toggle-switch">
                        <input type="checkbox" checked={editData.iva} onChange={e => setEditData({...editData, iva: e.target.checked})} />
                        <span className="slider"></span>
                      </div>
                      Aplicar IVA
                    </label>
                    <div style={{ flexGrow: 1 }} />
                    <button type="button" className="btn-secondary" onClick={handleRegenerar}>Aplicar y Re-generar</button>
                  </div>
                </div>
              )}
            </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '12px' }}>
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Créditos Involucrados</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold' }}>{previewData.creditos.length}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Cuotas a {tipoOperacion === 'VENTA' ? 'Ceder' : 'Adquirir'}</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold' }}>
                    {tipoOperacion === 'VENTA' ? previewData.cuotas.filter(c => c.incluida).length : previewData.cuotas.filter(c => c.comprada).length}
                  </div>
                </div>
                <div style={{ background: 'var(--accent-glow)', padding: '12px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--accent-primary)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-primary)' }}>Valor Actual (Precio)</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                    {new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(
                      previewData.resumen.reduce((acc, r) => acc + (r.valor_actual || 0), 0)
                    )}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                <button type="button" onClick={() => setPreviewTab('creditos')} className={previewTab === 'creditos' ? 'btn-primary' : 'btn-secondary'} style={{ flex: 1, padding: '6px' }}>Créditos</button>
                <button type="button" onClick={() => setPreviewTab('cuotas')} className={previewTab === 'cuotas' ? 'btn-primary' : 'btn-secondary'} style={{ flex: 1, padding: '6px' }}>Cuotas</button>
                <button type="button" onClick={() => setPreviewTab('resumen')} className={previewTab === 'resumen' ? 'btn-primary' : 'btn-secondary'} style={{ flex: 1, padding: '6px' }}>Vencimientos</button>
              </div>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 16px', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
              {previewTab === 'creditos' && (() => {
                const filtered = previewData.creditos.filter(c => {
                  return Object.keys(filterCreditos).every(key => {
                    const filterVal = filterCreditos[key];
                    if (filterVal === undefined || filterVal === null || filterVal === '' || (Array.isArray(filterVal) && filterVal.length === 0)) return true;
                    if (Array.isArray(filterVal)) {
                      return filterVal.includes(String(c[key] || ''));
                    }
                    return String(c[key] || '').toLowerCase().includes(filterVal.toLowerCase());
                  });
                });
                const totalMonto = filtered.reduce((acc, c) => acc + (tipoOperacion === 'VENTA' ? c.monto_otorgado : c.capital_vendido) || 0, 0);
                const totalCuotas = filtered.reduce((acc, c) => acc + (tipoOperacion === 'VENTA' ? c.total_cuotas : c.plazo) || 0, 0);
                const totalCeder = filtered.reduce((acc, c) => acc + (tipoOperacion === 'VENTA' ? c.cuotas_a_ceder : c.cuotas_compradas) || 0, 0);
                const totalVa = filtered.reduce((acc, c) => acc + (c.valor_actual || 0), 0);
                
                const handleFilterChange = (key, value) => {
                  setFilterCreditos(prev => ({ ...prev, [key]: value }));
                };

                return (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', overflowY: 'auto', flex: 1 }}>
                    <table className="data-table" style={{ width: '100%', fontSize: '13px' }}>
                      <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                        {tipoOperacion === 'VENTA' ? (
                          <tr>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              ID
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.id || ''} onChange={e => handleFilterChange('id', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Cliente
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.cliente || ''} onChange={e => handleFilterChange('cliente', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top', position: 'relative' }}>
                              Estado
                              <div onClick={e => { e.stopPropagation(); setShowPreviewEstadoFilter(!showPreviewEstadoFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                                {!(filterCreditos.estado?.length) ? "Todos" : `${filterCreditos.estado.length} selec.`}
                              </div>
                              {showPreviewEstadoFilter && (
                                <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px', minWidth: '120px' }}>
                                  {Array.from(new Set(previewData.creditos.map(c => c.estado))).filter(Boolean).map(est => (
                                    <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer', margin: 0 }}>
                                      <input type="checkbox" checked={filterCreditos.estado?.includes(est) || false} onChange={() => {
                                        const current = filterCreditos.estado || [];
                                        handleFilterChange('estado', current.includes(est) ? current.filter(x => x !== est) : [...current, est]);
                                      }} />
                                      {est}
                                    </label>
                                  ))}
                                </div>
                              )}
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Monto Orig.
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.monto_otorgado || ''} onChange={e => handleFilterChange('monto_otorgado', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Cuotas
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.total_cuotas || ''} onChange={e => handleFilterChange('total_cuotas', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              A Ceder
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.cuotas_a_ceder || ''} onChange={e => handleFilterChange('cuotas_a_ceder', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Valor Actual
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.valor_actual || ''} onChange={e => handleFilterChange('valor_actual', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                          </tr>
                        ) : (
                          <tr>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              ID Externo
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.id_externo || ''} onChange={e => handleFilterChange('id_externo', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Cliente
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.cliente_nombre || ''} onChange={e => handleFilterChange('cliente_nombre', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Cap. Vendido
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.capital_vendido || ''} onChange={e => handleFilterChange('capital_vendido', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Plazo
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.plazo || ''} onChange={e => handleFilterChange('plazo', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Adquiridas
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.cuotas_compradas || ''} onChange={e => handleFilterChange('cuotas_compradas', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Valor Actual
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.valor_actual || ''} onChange={e => handleFilterChange('valor_actual', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                          </tr>
                        )}
                      </thead>
                      <tbody>
                        {filtered.length === 0 && (
                          <tr><td colSpan="7" style={{ textAlign: 'center', padding: '16px' }}>No hay créditos que coincidan.</td></tr>
                        )}
                        {filtered.map((c, i) => (
                          tipoOperacion === 'VENTA' ? (
                            <tr key={i} style={{ opacity: creditosExcluidos.includes(c.id) ? 0.5 : 1 }}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.id}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.cliente}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.estado}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.monto_otorgado||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.total_cuotas}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.cuotas_a_ceder}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(c.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>
                                {!isReadOnly ? (
                                  <button 
                                    type="button"
                                    onClick={() => handleToggleExcluir(c.id)}
                                    style={{
                                      padding: '4px 8px',
                                      fontSize: '12px',
                                      borderRadius: '4px',
                                      border: '1px solid',
                                      cursor: 'pointer',
                                      transition: 'all 0.2s ease',
                                      backgroundColor: creditosExcluidos.includes(c.id) ? 'var(--bg-panel)' : 'rgba(239, 68, 68, 0.1)',
                                      borderColor: creditosExcluidos.includes(c.id) ? 'var(--border-color)' : 'var(--danger-color)',
                                      color: creditosExcluidos.includes(c.id) ? 'var(--text-secondary)' : 'var(--danger-color)'
                                    }}
                                  >
                                    {creditosExcluidos.includes(c.id) ? 'Incluir' : 'Excluir'}
                                  </button>
                                ) : (
                                  <span style={{ color: creditosExcluidos.includes(c.id) ? 'var(--text-secondary)' : 'var(--danger-color)', fontSize: '12px', fontWeight: 'bold' }}>
                                    {creditosExcluidos.includes(c.id) ? 'Excluido' : 'Incluido'}
                                  </span>
                                )}
                              </td>
                            </tr>
                          ) : (
                            <tr key={i}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.id_externo}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.cliente_nombre}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.capital_vendido||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.plazo}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.cuotas_compradas}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(c.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                            </tr>
                          )
                        ))}
                      </tbody>
                      <tfoot style={{ position: 'sticky', bottom: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 -2px 4px rgba(0,0,0,0.2)' }}>
                        <tr>
                          <td colSpan={tipoOperacion === 'VENTA' ? 3 : 2} style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>Totales:</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalMonto.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'center', padding: '12px', fontWeight: 'bold' }}>{totalCuotas}</td>
                          <td style={{ textAlign: 'center', padding: '12px', fontWeight: 'bold' }}>{totalCeder}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold', color: 'var(--accent-secondary)' }}>${totalVa.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
                );
              })()}

              {previewTab === 'cuotas' && (() => {
                const filtered = previewData.cuotas.filter(c => {
                  return Object.keys(filterCuotas).every(key => {
                    const filterVal = filterCuotas[key];
                    if (filterVal === undefined || filterVal === null || filterVal === '' || (Array.isArray(filterVal) && filterVal.length === 0)) return true;
                    if (Array.isArray(filterVal)) {
                      if (key === 'incluida' || key === 'comprada') return filterVal.includes(c[key] ? 'Sí' : 'No');
                      return filterVal.includes(String(c[key] || ''));
                    }
                    return String(c[key] || '').toLowerCase().includes(filterVal.toLowerCase());
                  });
                });
                const totalCap = filtered.reduce((acc, c) => acc + (c.capital || 0), 0);
                const totalInt = filtered.reduce((acc, c) => acc + (c.interes || 0), 0);
                const totalIva = filtered.reduce((acc, c) => acc + (c.iva || 0), 0);
                const totalTotal = filtered.reduce((acc, c) => acc + (tipoOperacion === 'VENTA' ? c.total_cuota : c.total) || 0, 0);
                const totalVa = filtered.reduce((acc, c) => acc + (c.valor_actual || 0), 0);
                
                const handleFilterChange = (key, value) => {
                  setFilterCuotas(prev => ({ ...prev, [key]: value }));
                };

                return (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', overflowY: 'auto', flex: 1 }}>
                    <table className="data-table" style={{ width: '100%', fontSize: '13px' }}>
                      <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                        {tipoOperacion === 'VENTA' ? (
                          <tr>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Crédito ID
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.credito_id || ''} onChange={e => handleFilterChange('credito_id', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Nro Cuota
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.nro_cuota || ''} onChange={e => handleFilterChange('nro_cuota', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Vencimiento
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.fecha_vencimiento || ''} onChange={e => handleFilterChange('fecha_vencimiento', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Capital
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.capital || ''} onChange={e => handleFilterChange('capital', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Interés
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.interes || ''} onChange={e => handleFilterChange('interes', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              IVA
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.iva || ''} onChange={e => handleFilterChange('iva', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Total Cuota
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.total_cuota || ''} onChange={e => handleFilterChange('total_cuota', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Valor Actual
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.valor_actual || ''} onChange={e => handleFilterChange('valor_actual', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top', position: 'relative' }}>
                              Incluida
                              <div onClick={e => { e.stopPropagation(); setShowPreviewIncluidaFilter(!showPreviewIncluidaFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                                {!(filterCuotas.incluida?.length) ? "Todos" : `${filterCuotas.incluida.length} selec.`}
                              </div>
                              {showPreviewIncluidaFilter && (
                                <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px', minWidth: '80px', textAlign: 'left' }}>
                                  {['Sí', 'No'].map(est => (
                                    <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer', margin: 0 }}>
                                      <input type="checkbox" checked={filterCuotas.incluida?.includes(est) || false} onChange={() => {
                                        const current = filterCuotas.incluida || [];
                                        handleFilterChange('incluida', current.includes(est) ? current.filter(x => x !== est) : [...current, est]);
                                      }} />
                                      {est}
                                    </label>
                                  ))}
                                </div>
                              )}
                            </th>
                          </tr>
                        ) : (
                          <tr>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              ID Ext.
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.credito_id_externo || ''} onChange={e => handleFilterChange('credito_id_externo', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Cuota
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.nro_cuota || ''} onChange={e => handleFilterChange('nro_cuota', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Vencimiento
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.fecha_vencimiento || ''} onChange={e => handleFilterChange('fecha_vencimiento', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Capital
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.capital || ''} onChange={e => handleFilterChange('capital', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Interés
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.interes || ''} onChange={e => handleFilterChange('interes', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              IVA
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.iva || ''} onChange={e => handleFilterChange('iva', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Total
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.total || ''} onChange={e => handleFilterChange('total', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              V. Actual
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.valor_actual || ''} onChange={e => handleFilterChange('valor_actual', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top', position: 'relative' }}>
                              Comprada
                              <div onClick={e => { e.stopPropagation(); setShowPreviewCompradaFilter(!showPreviewCompradaFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                                {!(filterCuotas.comprada?.length) ? "Todos" : `${filterCuotas.comprada.length} selec.`}
                              </div>
                              {showPreviewCompradaFilter && (
                                <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px', minWidth: '80px', textAlign: 'left' }}>
                                  {['Sí', 'No'].map(est => (
                                    <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer', margin: 0 }}>
                                      <input type="checkbox" checked={filterCuotas.comprada?.includes(est) || false} onChange={() => {
                                        const current = filterCuotas.comprada || [];
                                        handleFilterChange('comprada', current.includes(est) ? current.filter(x => x !== est) : [...current, est]);
                                      }} />
                                      {est}
                                    </label>
                                  ))}
                                </div>
                              )}
                            </th>
                          </tr>
                        )}
                      </thead>
                      <tbody>
                        {filtered.length === 0 && (
                          <tr><td colSpan="9" style={{ textAlign: 'center', padding: '16px' }}>No hay cuotas que coincidan.</td></tr>
                        )}
                        {filtered.map((c, i) => (
                          tipoOperacion === 'VENTA' ? (
                            <tr key={i} style={{ opacity: c.incluida ? 1 : 0.5 }}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.credito_id}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.nro_cuota}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.fecha_vencimiento}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.capital||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.interes||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.iva||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.total_cuota||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(c.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.incluida ? 'Sí' : 'No'}</td>
                            </tr>
                          ) : (
                            <tr key={i} style={{ opacity: c.comprada ? 1 : 0.5 }}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.credito_id_externo}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.nro_cuota}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.fecha_vencimiento}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.capital||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.interes||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.iva||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.total||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(c.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.comprada ? 'Sí' : 'No'}</td>
                            </tr>
                          )
                        ))}
                      </tbody>
                      <tfoot style={{ position: 'sticky', bottom: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 -2px 4px rgba(0,0,0,0.2)' }}>
                        <tr>
                          <td colSpan={3} style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>Totales:</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalCap.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalInt.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalIva.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalTotal.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold', color: 'var(--accent-secondary)' }}>${totalVa.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td></td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
                );
              })()}

              {previewTab === 'resumen' && (() => {
                const filtered = previewData.resumen.filter(c => {
                  return Object.keys(filterResumen).every(key => {
                    if (!filterResumen[key]) return true;
                    return String(c[key] || '').toLowerCase().includes(filterResumen[key].toLowerCase());
                  });
                });
                const totalCuotas = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.cantidad : r.cantidad_cuotas) || 0, 0);
                const totalCap = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.capital : r.capital_total) || 0, 0);
                const totalInt = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.interes : r.interes_total) || 0, 0);
                const totalIva = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.iva : r.iva_total) || 0, 0);
                const totalTot = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.total_cuota : r.monto_total) || 0, 0);
                const totalVa = filtered.reduce((acc, r) => acc + (r.valor_actual || 0), 0);
                
                const handleFilterChange = (key, value) => {
                  setFilterResumen(prev => ({ ...prev, [key]: value }));
                };

                return (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', overflowY: 'auto', flex: 1 }}>
                    <table className="data-table" style={{ width: '100%', fontSize: '13px' }}>
                      <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                        <tr>
                          <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                            {tipoOperacion === 'VENTA' ? 'Mes Vto.' : 'Mes'}
                            <input type="text" placeholder="Filtrar..." value={tipoOperacion === 'VENTA' ? (filterResumen.fecha_vencimiento || '') : (filterResumen.mes || '')} onChange={e => handleFilterChange(tipoOperacion === 'VENTA' ? 'fecha_vencimiento' : 'mes', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Cuotas
                            <input type="text" placeholder="Filtrar..." value={tipoOperacion === 'VENTA' ? (filterResumen.cantidad || '') : (filterResumen.cantidad_cuotas || '')} onChange={e => handleFilterChange(tipoOperacion === 'VENTA' ? 'cantidad' : 'cantidad_cuotas', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Capital Total
                            <input type="text" placeholder="Filtrar..." value={tipoOperacion === 'VENTA' ? (filterResumen.capital || '') : (filterResumen.capital_total || '')} onChange={e => handleFilterChange(tipoOperacion === 'VENTA' ? 'capital' : 'capital_total', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Interés Total
                            <input type="text" placeholder="Filtrar..." value={tipoOperacion === 'VENTA' ? (filterResumen.interes || '') : (filterResumen.interes_total || '')} onChange={e => handleFilterChange(tipoOperacion === 'VENTA' ? 'interes' : 'interes_total', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            IVA Total
                            <input type="text" placeholder="Filtrar..." value={tipoOperacion === 'VENTA' ? (filterResumen.iva || '') : (filterResumen.iva_total || '')} onChange={e => handleFilterChange(tipoOperacion === 'VENTA' ? 'iva' : 'iva_total', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Monto Total
                            <input type="text" placeholder="Filtrar..." value={tipoOperacion === 'VENTA' ? (filterResumen.total_cuota || '') : (filterResumen.monto_total || '')} onChange={e => handleFilterChange(tipoOperacion === 'VENTA' ? 'total_cuota' : 'monto_total', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Valor Actual
                            <input type="text" placeholder="Filtrar..." value={filterResumen.valor_actual || ''} onChange={e => handleFilterChange('valor_actual', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.length === 0 && (
                          <tr><td colSpan="7" style={{ textAlign: 'center', padding: '16px' }}>No hay vencimientos que coincidan.</td></tr>
                        )}
                        {filtered.map((r, i) => {
                          const cant = tipoOperacion === 'VENTA' ? r.cantidad : r.cantidad_cuotas;
                          const cap = tipoOperacion === 'VENTA' ? r.capital : r.capital_total;
                          const int = tipoOperacion === 'VENTA' ? r.interes : r.interes_total;
                          const iva = tipoOperacion === 'VENTA' ? r.iva : r.iva_total;
                          const tot = tipoOperacion === 'VENTA' ? r.total_cuota : r.monto_total;
                          return (
                            <tr key={i}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{tipoOperacion === 'VENTA' ? r.fecha_vencimiento : r.mes}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>{cant}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(cap||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(int||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(iva||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(tot||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(r.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot style={{ position: 'sticky', bottom: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 -2px 4px rgba(0,0,0,0.2)' }}>
                        <tr>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>Totales:</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>{totalCuotas}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalCap.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalInt.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalIva.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalTot.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold', color: 'var(--accent-secondary)' }}>${totalVa.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
                );
              })()}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', padding: '16px 32px', borderTop: '1px solid rgba(255,255,255,0.1)', background: 'var(--bg-panel)' }}>
                <button type="button" onClick={onClose} className="btn-secondary">{isReadOnly ? 'Cerrar' : 'Cancelar'}</button>
                {!isReadOnly && (
                  <button type="button" onClick={handleGuardarEdicion} className="btn-primary" disabled={loading || previewData.resumen.length === 0}>
                    {loading ? 'Guardando...' : 'Guardar Cambios'}
                  </button>
                )}
            </div>
          </div>
        </div>
  );
};

export default CarteraPreviewModal;
