import { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import axiosClient from '../api/axiosClient';
import ClientCCModal from '../components/ClientCCModal';
import CreditEditEstadoModal from '../components/CreditEditEstadoModal';
import TransfersModal from '../components/TransfersModal';
import LegajoModal from '../components/LegajoModal';
import ExcelDateFilter from '../components/ExcelDateFilter';
import ExcelNumberRangeFilter from '../components/ExcelNumberRangeFilter';
import ExportExcelButton from '../components/ExportExcelButton';
import { Eye, Edit, Trash2 } from 'lucide-react';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const CreditListPage = () => {
  const [creditos, setCreditos] = useState([]);
  const [loading, setLoading] = useState(false);
  const location = useLocation();
  
  const [filter, setFilter] = useState({ ID: '', CUIL: '', Capital: {}, Plazo: '', TNA: '', Estado: [], Fecha: [], TipoCredito: [] });
  const [sortConfig, setSortConfig] = useState({ key: 'ID', direction: 'desc' });
  const [showEstadoFilter, setShowEstadoFilter] = useState(false);
  const [showTipoCreditoFilter, setShowTipoCreditoFilter] = useState(false);

  const [ccCuil, setCcCuil] = useState(null);
  const [editCredito, setEditCredito] = useState(null);
  const [viewTransfersCredito, setViewTransfersCredito] = useState(null);
  const [viewLegajoCredito, setViewLegajoCredito] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const cuilParam = params.get('cuil');
    if (cuilParam) setFilter(prev => ({ ...prev, CUIL: cuilParam }));
  }, [location.search]);

  const fetchCreditos = async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get('/api/v1/creditos');
      setCreditos(res.data);
    } catch (error) {
      alert("Error cargando créditos: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCreditos();
  }, []);

  const handleDelete = async (id) => {
    if (!window.confirm(`¿Está seguro que desea eliminar el crédito #${id}?`)) return;
    try {
      await axiosClient.delete(`/api/v1/creditos/${id}`);
      alert('Crédito eliminado con éxito.');
      fetchCreditos();
    } catch (error) {
      alert("Error eliminando crédito: " + error.message);
    }
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const handleEstadoToggle = (estado) => {
    setFilter(prev => {
      const current = prev.Estado;
      if (current.includes(estado)) return { ...prev, Estado: current.filter(e => e !== estado) };
      return { ...prev, Estado: [...current, estado] };
    });
  };

  const handleTipoCreditoToggle = (tipo) => {
    setFilter(prev => {
      const current = prev.TipoCredito;
      if (current.includes(tipo)) return { ...prev, TipoCredito: current.filter(e => e !== tipo) };
      return { ...prev, TipoCredito: [...current, tipo] };
    });
  };

  const getFilteredData = (excludeKey = null) => {
    let result = [...creditos];
    if (filter.ID) result = result.filter(c => c.ID === parseInt(filter.ID, 10));
    if (filter.CUIL) result = result.filter(c => c["Cliente CUIL"] && c["Cliente CUIL"].includes(filter.CUIL));
    if (filter.Plazo) result = result.filter(c => String(c.Plazo).includes(filter.Plazo));
    if (filter.TNA) result = result.filter(c => String(c["TNA con IVA"]).includes(filter.TNA));
    
    if (excludeKey !== 'TipoCredito' && filter.TipoCredito && filter.TipoCredito.length > 0) {
      result = result.filter(c => filter.TipoCredito.includes(c["Tipo Crédito"]));
    }
    
    if (filter.Capital && typeof filter.Capital === 'object') {
      result = result.filter(c => {
        if (c.Capital === null || c.Capital === undefined) return false;
        const numVal = Number(c.Capital);
        if (isNaN(numVal)) return false;
        if (filter.Capital.min !== undefined && numVal < filter.Capital.min) return false;
        if (filter.Capital.max !== undefined && numVal > filter.Capital.max) return false;
        return true;
      });
    }

    if (excludeKey !== 'Estado' && filter.Estado && filter.Estado.length > 0) {
      result = result.filter(c => filter.Estado.includes(c.Estado));
    }
    
    if (excludeKey !== 'Fecha' && filter.Fecha && filter.Fecha.length > 0) {
      result = result.filter(c => filter.Fecha.includes(c["Fecha Emisión"]));
    }

    return result;
  };

  const filteredAndSortedCreditos = useMemo(() => {
    let result = getFilteredData();
    if (sortConfig.key) {
      result.sort((a, b) => {
        let valA = a[sortConfig.key] ?? '';
        let valB = b[sortConfig.key] ?? '';
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [creditos, filter, sortConfig]);

  const ESTADOS_DISPONIBLES = useMemo(() => {
    return [...new Set(filteredAndSortedCreditos.map(c => c.Estado).filter(Boolean))].sort();
  }, [filteredAndSortedCreditos]);

  const AVAILABLE_TIPOS_CREDITO = useMemo(() => {
    return [...new Set(filteredAndSortedCreditos.map(c => c["Tipo Crédito"]).filter(Boolean))].sort();
  }, [filteredAndSortedCreditos]);

  const AVAILABLE_FECHAS_EMISION = useMemo(() => {
    return [...new Set(filteredAndSortedCreditos.map(c => c["Fecha Emisión"]).filter(Boolean))].sort();
  }, [filteredAndSortedCreditos]);

  const totalCapital = useMemo(() => {
    return filteredAndSortedCreditos.reduce((acc, c) => acc + (c.Capital || 0), 0);
  }, [filteredAndSortedCreditos]);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '5px' }}>↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Listado Global de Créditos</h2>
          <p>Vista general de todos los créditos de la base de datos.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn-primary" onClick={fetchCreditos} disabled={loading} style={{ width: 'auto' }}>
            {loading ? "Actualizando..." : "Actualizar Datos"}
          </button>
          <ExportExcelButton 
            data={creditos} 
            filteredData={filteredAndSortedCreditos} 
            filename="creditos_export" 
          />
        </div>
      </header>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('ID')} style={{ cursor: 'pointer' }}>
                  ID <SortIcon columnKey="ID" />
                  <input type="number" placeholder="Filtrar..." value={filter.ID} onChange={e => setFilter({ ...filter, ID: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Cliente CUIL')} style={{ cursor: 'pointer' }}>
                  Cliente CUIL <SortIcon columnKey="Cliente CUIL" />
                  <input type="text" placeholder="Filtrar CUIL..." value={filter.CUIL} onChange={e => setFilter({ ...filter, CUIL: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Capital')} style={{ cursor: 'pointer' }}>
                  Capital Originado <SortIcon columnKey="Capital" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelNumberRangeFilter 
                      selectedRange={filter.Capital} 
                      onChange={range => setFilter({ ...filter, Capital: range })} 
                    />
                  </div>
                </th>
                <th onClick={() => handleSort('Plazo')} style={{ cursor: 'pointer' }}>
                  Plazo <SortIcon columnKey="Plazo" />
                  <input type="text" placeholder="Filtrar..." value={filter.Plazo} onChange={e => setFilter({ ...filter, Plazo: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('TNA con IVA')} style={{ cursor: 'pointer' }}>
                  TNA <SortIcon columnKey="TNA con IVA" />
                  <input type="text" placeholder="Filtrar..." value={filter.TNA} onChange={e => setFilter({ ...filter, TNA: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Tipo Crédito')} style={{ cursor: 'pointer' }}>
                  Tipo Crédito <SortIcon columnKey="Tipo Crédito" />
                  <div onClick={e => { e.stopPropagation(); setShowTipoCreditoFilter(!showTipoCreditoFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                    {filter.TipoCredito.length === 0 ? "Todos" : `${filter.TipoCredito.length} selec.`}
                  </div>
                  {showTipoCreditoFilter && (
                    <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px' }}>
                      {AVAILABLE_TIPOS_CREDITO.map(tipo => (
                        <label key={tipo} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer' }}>
                          <input type="checkbox" checked={filter.TipoCredito.includes(tipo)} onChange={() => handleTipoCreditoToggle(tipo)} />
                          {tipo}
                        </label>
                      ))}
                    </div>
                  )}
                </th>
                <th onClick={() => handleSort('Estado')} style={{ cursor: 'pointer' }}>
                  Estado <SortIcon columnKey="Estado" />
                  <div onClick={e => { e.stopPropagation(); setShowEstadoFilter(!showEstadoFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                    {filter.Estado.length === 0 ? "Todos" : `${filter.Estado.length} selec.`}
                  </div>
                  {showEstadoFilter && (
                    <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px' }}>
                      {ESTADOS_DISPONIBLES.map(est => (
                        <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer' }}>
                          <input type="checkbox" checked={filter.Estado.includes(est)} onChange={() => handleEstadoToggle(est)} />
                          {est}
                        </label>
                      ))}
                    </div>
                  )}
                </th>
                <th onClick={() => handleSort('Fecha Emisión')} style={{ cursor: 'pointer' }}>
                  Fecha Emisión <SortIcon columnKey="Fecha Emisión" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelDateFilter 
                      availableDates={AVAILABLE_FECHAS_EMISION}
                      selectedDates={filter.Fecha}
                      onChange={dates => setFilter({ ...filter, Fecha: dates })}
                    />
                  </div>
                </th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedCreditos.length === 0 ? (
                <tr>
                  <td colSpan="9" className="text-center empty-state" style={{ padding: '40px' }}>
                    {loading ? "Cargando..." : "No hay créditos para mostrar con los filtros actuales."}
                  </td>
                </tr>
              ) : (
                filteredAndSortedCreditos.map(c => (
                  <tr key={c.ID}>
                    <td>{c.ID}</td>
                    <td>{c["Cliente CUIL"]}</td>
                    <td>{formatCurrency(c.Capital)}</td>
                    <td>{c.Plazo}</td>
                    <td>{(c["TNA con IVA"] * 100).toFixed(2)}%</td>
                    <td>{c["Tipo Crédito"]}</td>
                    <td>
                       <span className={`status-badge status-${(c.Estado || 'activo').toLowerCase()}`}>
                         {c.Estado}
                       </span>
                    </td>
                    <td>{c["Fecha Emisión"]}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'nowrap', alignItems: 'center' }}>
                        <button className="btn-secondary" onClick={() => setCcCuil(c["Cliente CUIL"])} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Cuenta Corriente">
                          👁️
                        </button>
                        <button className="btn-secondary" onClick={() => setViewTransfersCredito(c.ID)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Transferencias">
                          💸
                        </button>
                        <button className="btn-secondary" onClick={() => setViewLegajoCredito(c.ID)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Legajo">
                          📁
                        </button>
                        <button className="btn-secondary" onClick={() => setEditCredito({ id: c.ID, estado: c.Estado })} style={{ padding: '4px 8px', fontSize: '14px' }} title="Editar Estado">
                          ✏️
                        </button>
                        <button className="btn-secondary" onClick={() => handleDelete(c.ID)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar">
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot style={{ background: 'rgba(255, 255, 255, 0.05)', fontWeight: 'bold' }}>
              <tr>
                <td colSpan="2" style={{ textAlign: 'right' }}>TOTAL:</td>
                <td>{formatCurrency(totalCapital)}</td>
                <td colSpan="6"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {ccCuil && <ClientCCModal cuil={ccCuil} onClose={() => setCcCuil(null)} />}
      {editCredito && <CreditEditEstadoModal creditoId={editCredito.id} currentEstado={editCredito.estado} onClose={() => setEditCredito(null)} onSuccess={fetchCreditos} />}
      {viewTransfersCredito && <TransfersModal creditoId={viewTransfersCredito} onClose={() => setViewTransfersCredito(null)} />}
      {viewLegajoCredito && <LegajoModal creditoId={viewLegajoCredito} onClose={() => { setViewLegajoCredito(null); fetchCreditos(); }} />}
    </section>
  );
};

export default CreditListPage;
