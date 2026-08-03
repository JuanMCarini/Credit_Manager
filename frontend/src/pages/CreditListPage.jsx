import { useState, useEffect, useMemo } from 'react';
import { FilterX } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import axiosClient from '../api/axiosClient';
import ClientCCModal from '../components/ClientCCModal';
import CreditEditEstadoModal from '../components/CreditEditEstadoModal';
import TransfersModal from '../components/TransfersModal';
import LegajoModal from '../components/LegajoModal';
import ExcelDateFilter from '../components/ExcelDateFilter';
import ExcelNumberRangeFilter from '../components/ExcelNumberRangeFilter';
import ExcelListFilter from '../components/ExcelListFilter';
import ExportExcelButton from '../components/ExportExcelButton';
import { Eye, Edit, Trash2 } from 'lucide-react';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const CreditListPage = () => {
  const [creditos, setCreditos] = useState([]);
  const [loading, setLoading] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  
  const [filter, setFilter] = useState({ ID: [], IdExterno: '', Originador: '', CUIL: '', Capital: {}, Plazo: '', TNA: '', Estado: [], Fecha: [], TipoCredito: [], SaldoMora: {}, DiasMora: {} });
  const [sortConfig, setSortConfig] = useState({ key: 'ID', direction: 'desc' });
  const [showEstadoFilter, setShowEstadoFilter] = useState(false);
  const [showTipoCreditoFilter, setShowTipoCreditoFilter] = useState(false);
  const [fechaCorte, setFechaCorte] = useState(() => new Date().toISOString().split('T')[0]);

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
      const res = await axiosClient.get('/api/v1/creditos', { params: { fecha_corte: fechaCorte } });
      setCreditos(res.data);
    } catch (error) {
      alert("Error cargando créditos: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCreditos();
  }, [fechaCorte]);

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
    if (excludeKey !== 'ID' && filter.ID && filter.ID.length > 0) {
      result = result.filter(c => filter.ID.includes(String(c.ID)));
    }
    if (filter.IdExterno) result = result.filter(c => c["ID Externo"] && String(c["ID Externo"]).toLowerCase().includes(filter.IdExterno.toLowerCase()));
    if (filter.Originador) result = result.filter(c => c["Socio Originador"] && String(c["Socio Originador"]).toLowerCase().includes(filter.Originador.toLowerCase()));
    if (filter.CUIL) result = result.filter(c => c["Cliente CUIL"] && c["Cliente CUIL"].includes(filter.CUIL));
    if (filter.Plazo) result = result.filter(c => String(c.Plazo).includes(filter.Plazo));
    if (filter.TNA) result = result.filter(c => String(c["TNA con IVA"]).includes(filter.TNA));
    
    if (excludeKey !== 'TipoCredito' && filter.TipoCredito && filter.TipoCredito.length > 0) {
      result = result.filter(c => filter.TipoCredito.includes(c["Tipo Crédito"]));
    }
    
    if (filter.Capital && typeof filter.Capital === 'object' && Object.keys(filter.Capital).length > 0) {
      result = result.filter(c => {
        if (c.Capital === null || c.Capital === undefined) return false;
        const numVal = Number(c.Capital);
        if (isNaN(numVal)) return false;
        if (filter.Capital.min !== undefined && numVal < filter.Capital.min) return false;
        if (filter.Capital.max !== undefined && numVal > filter.Capital.max) return false;
        return true;
      });
    }

    if (filter.SaldoMora && typeof filter.SaldoMora === 'object' && Object.keys(filter.SaldoMora).length > 0) {
      result = result.filter(c => {
        if (c["Saldo en Mora"] === null || c["Saldo en Mora"] === undefined) return false;
        const numVal = Number(c["Saldo en Mora"]);
        if (isNaN(numVal)) return false;
        if (filter.SaldoMora.min !== undefined && numVal < filter.SaldoMora.min) return false;
        if (filter.SaldoMora.max !== undefined && numVal > filter.SaldoMora.max) return false;
        return true;
      });
    }

    if (filter.DiasMora && typeof filter.DiasMora === 'object' && Object.keys(filter.DiasMora).length > 0) {
      result = result.filter(c => {
        if (c["Días de Mora"] === null || c["Días de Mora"] === undefined) return false;
        const numVal = Number(c["Días de Mora"]);
        if (isNaN(numVal)) return false;
        if (filter.DiasMora.min !== undefined && numVal < filter.DiasMora.min) return false;
        if (filter.DiasMora.max !== undefined && numVal > filter.DiasMora.max) return false;
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
    const dataForFilter = getFilteredData('Estado');
    return [...new Set(dataForFilter.map(c => c.Estado).filter(Boolean))].sort();
  }, [creditos, filter]);

  const AVAILABLE_CREDIT_IDS = useMemo(() => {
    const dataForFilter = getFilteredData('ID');
    return [...new Set(dataForFilter.map(c => c.ID).filter(Boolean))].sort((a,b)=>a-b).map(String);
  }, [creditos, filter]);

  const AVAILABLE_TIPOS_CREDITO = useMemo(() => {
    return [...new Set(filteredAndSortedCreditos.map(c => c["Tipo Crédito"]).filter(Boolean))].sort();
  }, [filteredAndSortedCreditos]);

  const AVAILABLE_FECHAS_EMISION = useMemo(() => {
    return [...new Set(filteredAndSortedCreditos.map(c => c["Fecha Emisión"]).filter(Boolean))].sort();
  }, [filteredAndSortedCreditos]);

  const totalCapital = useMemo(() => {
    return filteredAndSortedCreditos.reduce((acc, c) => acc + (c.Capital || 0), 0);
  }, [filteredAndSortedCreditos]);

  const totalMora = useMemo(() => {
    return filteredAndSortedCreditos.reduce((acc, c) => acc + (c["Saldo en Mora"] || 0), 0);
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
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-color)', opacity: 0.8 }}>Fecha Corte:</span>
            <input 
              type="date" 
              value={fechaCorte} 
              onChange={e => setFechaCorte(e.target.value)} 
              style={{ background: 'transparent', border: 'none', color: 'var(--text-color)', outline: 'none', fontSize: '12px', cursor: 'pointer', colorScheme: 'dark' }}
            />
          </div>
          <button className="btn-primary" onClick={fetchCreditos} disabled={loading} style={{ width: 'auto' }}>
            {loading ? "Actualizando..." : "Actualizar Datos"}
          </button>
          <button 
            className="btn-secondary" 
            onClick={() => setFilter({ ID: [], IdExterno: '', Originador: '', CUIL: '', Capital: {}, Plazo: '', TNA: '', Estado: [], Fecha: [], TipoCredito: [], SaldoMora: {}, DiasMora: {} })}
            title="Limpiar todos los filtros"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <FilterX size={16} /> Limpiar Filtros
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
                <th onClick={() => handleSort('ID')} style={{ cursor: 'pointer', minWidth: '70px' }}>
                  ID <SortIcon columnKey="ID" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelListFilter 
                      availableOptions={AVAILABLE_CREDIT_IDS} 
                      selectedOptions={filter.ID} 
                      onChange={val => setFilter({ ...filter, ID: val })} 
                      title="Filtrar IDs..." 
                    />
                  </div>
                </th>
                <th onClick={() => handleSort('ID Externo')} style={{ cursor: 'pointer' }}>
                  ID Externo <SortIcon columnKey="ID Externo" />
                  <input type="text" placeholder="Filtrar..." value={filter.IdExterno} onChange={e => setFilter({ ...filter, IdExterno: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Socio Originador')} style={{ cursor: 'pointer' }}>
                  Originador <SortIcon columnKey="Socio Originador" />
                  <input type="text" placeholder="Filtrar..." value={filter.Originador} onChange={e => setFilter({ ...filter, Originador: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
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
                <th onClick={() => handleSort('Saldo en Mora')} style={{ cursor: 'pointer' }}>
                  Saldo Mora <SortIcon columnKey="Saldo en Mora" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelNumberRangeFilter 
                      selectedRange={filter.SaldoMora} 
                      onChange={range => setFilter({ ...filter, SaldoMora: range })} 
                    />
                  </div>
                </th>
                <th onClick={() => handleSort('Días de Mora')} style={{ cursor: 'pointer' }}>
                  Días Mora <SortIcon columnKey="Días de Mora" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelNumberRangeFilter 
                      selectedRange={filter.DiasMora} 
                      onChange={range => setFilter({ ...filter, DiasMora: range })} 
                    />
                  </div>
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
                  <td colSpan="13" className="text-center empty-state" style={{ padding: '40px' }}>
                    {loading ? "Cargando..." : "No hay créditos para mostrar con los filtros actuales."}
                  </td>
                </tr>
              ) : (
                filteredAndSortedCreditos.map(c => (
                  <tr key={c.ID}>
                    <td>{c.ID}</td>
                    <td>{c["ID Externo"]}</td>
                    <td>{c["Socio Originador"]}</td>
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
                    <td>{formatCurrency(c["Saldo en Mora"])}</td>
                    <td>{c["Días de Mora"]}</td>
                    <td>{c["Fecha Emisión"]}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'nowrap', alignItems: 'center' }}>
                        <button className="btn-secondary" onClick={() => navigate(`/dashboard-clientes?cuil=${c["Cliente CUIL"]}&credito_id=${c.ID}`)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Dashboard de Cliente">
                          📊
                        </button>
                        <button className="btn-secondary" onClick={() => setCcCuil(c["Cliente CUIL"])} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Cuenta Corriente">
                          👁️
                        </button>
                        <button className="btn-secondary" onClick={() => setViewTransfersCredito(c.ID)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Transferencias">
                          💸
                        </button>
                        <button className="btn-secondary" onClick={() => setViewLegajoCredito({id: c.ID, estado: c.Estado})} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Legajo">
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
                <td colSpan="4" style={{ textAlign: 'right' }}>TOTAL:</td>
                <td>{formatCurrency(totalCapital)}</td>
                <td colSpan="4"></td>
                <td>{formatCurrency(totalMora)}</td>
                <td colSpan="3"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {ccCuil && <ClientCCModal cuil={ccCuil} onClose={() => setCcCuil(null)} />}
      {editCredito && <CreditEditEstadoModal creditoId={editCredito.id} currentEstado={editCredito.estado} onClose={() => setEditCredito(null)} onSuccess={fetchCreditos} />}
      {viewTransfersCredito && <TransfersModal creditoId={viewTransfersCredito} onClose={() => setViewTransfersCredito(null)} />}
      {viewLegajoCredito && <LegajoModal creditoId={viewLegajoCredito.id} creditoEstado={viewLegajoCredito.estado} onClose={() => { setViewLegajoCredito(null); fetchCreditos(); }} />}
    </section>
  );
};

export default CreditListPage;
