import { useState, useEffect, useMemo } from 'react';
import axiosClient from '../api/axiosClient';
import { Trash2, DollarSign } from 'lucide-react';

const PortfolioLiquidationsPage = () => {
  const [activeTab, setActiveTab] = useState('liquidaciones');
  const [liquidaciones, setLiquidaciones] = useState([]);
  const [procesos, setProcesos] = useState([]);
  const [loading, setLoading] = useState(false);

  const [filter, setFilter] = useState({
    id: '', proceso_id: '', cartera_id: '', cuota_id: '', cobranza_id: '',
    tipo_liquidacion: [], credito_id: '', nro_cuota: '', fecha_vencimiento: '',
    capital: '', interes: '', iva: '', importe_total: '', fecha_pago: '', cancelada: ''
  });

  const [showTipoFilter, setShowTipoFilter] = useState(false);
  const TIPOS_DISPONIBLES = useMemo(() => [...new Set(liquidaciones.map(l => l.tipo_liquidacion).filter(Boolean))], [liquidaciones]);

  const handleTipoToggle = (tipo) => {
    setFilter(prev => {
      const current = prev.tipo_liquidacion;
      if (current.includes(tipo)) {
        return { ...prev, tipo_liquidacion: current.filter(t => t !== tipo) };
      } else {
        return { ...prev, tipo_liquidacion: [...current, tipo] };
      }
    });
  };

  const filteredLiquidaciones = useMemo(() => {
    let result = [...liquidaciones];
    if (filter.id) result = result.filter(l => String(l.id).includes(filter.id));
    if (filter.proceso_id) result = result.filter(l => String(l.proceso_id || '').includes(filter.proceso_id));
    if (filter.cartera_id) result = result.filter(l => String(l.cartera_id || '').includes(filter.cartera_id));
    if (filter.cuota_id) result = result.filter(l => String(l.cuota_id || '').includes(filter.cuota_id));
    if (filter.cobranza_id) result = result.filter(l => String(l.cobranza_id || '').includes(filter.cobranza_id));
    if (filter.tipo_liquidacion.length > 0) result = result.filter(l => filter.tipo_liquidacion.includes(l.tipo_liquidacion));
    if (filter.credito_id) result = result.filter(l => String(l.credito_id || '').includes(filter.credito_id));
    if (filter.nro_cuota) result = result.filter(l => String(l.nro_cuota || '').includes(filter.nro_cuota));
    if (filter.fecha_vencimiento) result = result.filter(l => String(l.fecha_vencimiento || '').includes(filter.fecha_vencimiento));
    if (filter.capital) result = result.filter(l => String(l.capital || '').includes(filter.capital));
    if (filter.interes) result = result.filter(l => String(l.interes || '').includes(filter.interes));
    if (filter.iva) result = result.filter(l => String(l.iva || '').includes(filter.iva));
    if (filter.importe_total) result = result.filter(l => String(l.importe_total || '').includes(filter.importe_total));
    if (filter.fecha_pago) result = result.filter(l => String(l.fecha_pago || '').includes(filter.fecha_pago));
    if (filter.cancelada !== '') {
      const isCancelada = filter.cancelada === 'true';
      result = result.filter(l => l.cancelada === isCancelada);
    }
    return result;
  }, [liquidaciones, filter]);

  const handleFilterChange = (field, value) => setFilter(prev => ({ ...prev, [field]: value }));

  const renderInput = (field, placeholder = 'Filtro...') => (
    <input 
      type="text" 
      placeholder={placeholder} 
      value={filter[field]} 
      onChange={e => handleFilterChange(field, e.target.value)} 
      onClick={e => e.stopPropagation()} 
      style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', boxSizing: 'border-box' }} 
    />
  );


  const fetchLiquidacionesYProcesos = async () => {
    setLoading(true);
    try {
      const [resLiq, resProc] = await Promise.all([
        axiosClient.get(`/api/v1/liquidaciones?t=${new Date().getTime()}`),
        axiosClient.get(`/api/v1/procesos?t=${new Date().getTime()}`)
      ]);
      setLiquidaciones(resLiq.data);
      setProcesos(resProc.data.filter(p => String(p.Tipo).startsWith('LIQUIDACIONES_')));
    } catch (error) {
      alert("Error cargando datos: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProceso = async (procesoId) => {
    if (!window.confirm("¿Estás seguro de que deseas eliminar este proceso? Esto borrará todas las liquidaciones asociadas y no se puede deshacer.")) {
      return;
    }
    try {
      await axiosClient.delete(`/api/v1/procesos/${procesoId}`);
      alert("Proceso eliminado con éxito.");
      fetchLiquidacionesYProcesos();
    } catch (error) {
      alert("Error al eliminar proceso: " + (error.response?.data?.detail || error.message));
    }
  };

  const handlePayProceso = async (procesoId) => {
    const amountStr = window.prompt("Ingrese el monto a pagar (0 para pago total):", "0");
    if (amountStr === null) return;
    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount < 0) {
      alert("Monto inválido.");
      return;
    }
    const fechaPago = window.prompt("Ingrese la fecha de pago (YYYY-MM-DD):", new Date().toISOString().split('T')[0]);
    if (!fechaPago) return;

    try {
      const response = await axiosClient.post(`/api/v1/procesos/${procesoId}/liquidaciones/pagar`, {
        monto: amount,
        fecha_pago: fechaPago
      });
      alert(response.data.message || "Pago registrado con éxito.");
      fetchLiquidacionesYProcesos();
    } catch (error) {
      alert("Error al registrar pago: " + (error.response?.data?.detail || error.message));
    }
  };

  useEffect(() => {
    fetchLiquidacionesYProcesos();
  }, []);

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Liquidaciones de Cartera</h2>
          <p>Listado de liquidaciones y rendiciones asociadas a las carteras de crédito.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', marginBottom: '8px' }}>
          <button className="btn-secondary" onClick={fetchLiquidacionesYProcesos} disabled={loading} style={{ height: 'fit-content', width: 'fit-content', paddingLeft: '24px', paddingRight: '24px' }}>
            {loading ? 'Actualizando...' : 'Actualizar Datos'}
          </button>
        </div>
      </header>

      <div className="tabs-container">
        <button className={`tab-button ${activeTab === 'liquidaciones' ? 'active' : ''}`} onClick={() => setActiveTab('liquidaciones')}>Liquidaciones</button>
        <button className={`tab-button ${activeTab === 'procesos' ? 'active' : ''}`} onClick={() => setActiveTab('procesos')}>Procesos de Liquidaciones</button>
      </div>

      <div className="glass-panel" style={{ overflowX: 'auto', maxHeight: 'calc(100vh - 240px)', overflowY: 'auto' }}>
        {activeTab === 'liquidaciones' ? (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ minWidth: '70px' }}>ID <br/>{renderInput('id', '...')}</th>
                <th style={{ minWidth: '90px' }}>Proceso ID <br/>{renderInput('proceso_id', '...')}</th>
                <th style={{ minWidth: '90px' }}>Cartera ID <br/>{renderInput('cartera_id', '...')}</th>
                <th style={{ minWidth: '90px' }}>Cuota ID <br/>{renderInput('cuota_id', '...')}</th>
                <th style={{ minWidth: '100px' }}>Cobranza ID <br/>{renderInput('cobranza_id', '...')}</th>
                <th style={{ minWidth: '100px', position: 'relative' }}>
                  Tipo <br/>
                  <div 
                    onClick={e => { e.stopPropagation(); setShowTipoFilter(!showTipoFilter); }}
                    style={{ 
                      width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', 
                      background: 'var(--surface-color)', border: '1px solid var(--border-color)', 
                      borderRadius: '4px', textAlign: 'center', cursor: 'pointer', boxSizing: 'border-box'
                    }}
                  >
                    {filter.tipo_liquidacion.length === 0 ? "Todos" : `${filter.tipo_liquidacion.length} selec.`}
                  </div>
                  {showTipoFilter && (
                    <div 
                      onClick={e => e.stopPropagation()} 
                      style={{
                        position: 'absolute', top: '100%', left: 0, zIndex: 100,
                        background: 'var(--surface-color)', border: '1px solid var(--border-color)',
                        borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column',
                        gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px',
                        minWidth: '120px'
                      }}
                    >
                      {TIPOS_DISPONIBLES.map(tipo => (
                        <label key={tipo} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer' }}>
                          <input 
                            type="checkbox" 
                            checked={filter.tipo_liquidacion.includes(tipo)}
                            onChange={() => handleTipoToggle(tipo)}
                          />
                          {tipo}
                        </label>
                      ))}
                    </div>
                  )}
                </th>
                <th style={{ minWidth: '90px' }}>ID Crédito <br/>{renderInput('credito_id', '...')}</th>
                <th style={{ minWidth: '90px' }}>Nro. Cuota <br/>{renderInput('nro_cuota', '...')}</th>
                <th style={{ minWidth: '110px' }}>Vencimiento <br/>{renderInput('fecha_vencimiento', '...')}</th>
                <th style={{ minWidth: '90px' }}>Capital <br/>{renderInput('capital', '...')}</th>
                <th style={{ minWidth: '90px' }}>Interés <br/>{renderInput('interes', '...')}</th>
                <th style={{ minWidth: '90px' }}>IVA <br/>{renderInput('iva', '...')}</th>
                <th style={{ minWidth: '90px' }}>Total <br/>{renderInput('importe_total', '...')}</th>
                <th style={{ minWidth: '110px' }}>Fecha Pago <br/>{renderInput('fecha_pago', '...')}</th>
                <th style={{ minWidth: '100px' }}>
                  Estado <br/>
                  <select 
                    value={filter.cancelada} 
                    onChange={e => handleFilterChange('cancelada', e.target.value)}
                    style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', boxSizing: 'border-box' }}
                  >
                    <option value="">Todos</option>
                    <option value="true">Cancelada</option>
                    <option value="false">Pendiente</option>
                  </select>
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredLiquidaciones.length === 0 ? (
                <tr><td colSpan="16" className="text-center empty-state">{loading ? "Cargando..." : "No hay liquidaciones."}</td></tr>
              ) : (
                filteredLiquidaciones.map(l => (
                  <tr key={l.id}>
                    <td>{l.id}</td>
                    <td>{l.proceso_id || '-'}</td>
                    <td>{l.cartera_id}</td>
                    <td>{l.cuota_id}</td>
                    <td>{l.cobranza_id || '-'}</td>
                    <td>{l.tipo_liquidacion}</td>
                    <td>{l.credito_id || '-'}</td>
                    <td>{l.nro_cuota || '-'}</td>
                    <td>{l.fecha_vencimiento || '-'}</td>
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
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>ID Proceso</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Descripción</th>
                <th>Fecha Ejecución</th>
                <th style={{ width: '80px', textAlign: 'center' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {procesos.length === 0 ? (
                <tr><td colSpan="6" className="text-center empty-state">{loading ? "Cargando..." : "No hay procesos de liquidación."}</td></tr>
              ) : (
                procesos.map(p => (
                  <tr key={p.ID}>
                    <td>{p.ID}</td>
                    <td>{p.Tipo}</td>
                    <td>
                      <span className={`status-badge status-${p.Estado.toLowerCase()}`}>
                        {p.Estado}
                      </span>
                    </td>
                    <td>{p.Descripción}</td>
                    <td>{new Date(p['Fecha Ejecución']).toLocaleString()}</td>
                    <td style={{ textAlign: 'center', display: 'flex', justifyContent: 'center', gap: '8px' }}>
                      {p.Estado !== 'COMPLETADO' && (
                        <>
                          <button 
                            className="btn-secondary" 
                            title="Ingresar Pago"
                            onClick={() => handlePayProceso(p.ID)}
                            style={{ padding: '4px 8px', fontSize: '12px', color: 'var(--primary-color)' }}
                          >
                            <DollarSign size={16} />
                          </button>
                          <button 
                            className="btn-secondary" 
                            title="Eliminar Proceso"
                            onClick={() => handleDeleteProceso(p.ID)}
                            style={{ padding: '4px 8px', fontSize: '12px', color: 'var(--danger-color)' }}
                          >
                            <Trash2 size={16} />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
};

export default PortfolioLiquidationsPage;
