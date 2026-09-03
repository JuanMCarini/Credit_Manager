import { useState, useEffect, useMemo } from 'react';
import { FilterX } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { useDebounce } from '../hooks/useDebounce';
import ClientCCModal from '../components/ClientCCModal';
import CreditEditEstadoModal from '../components/CreditEditEstadoModal';
import TransfersModal from '../components/TransfersModal';
import LegajoModal from '../components/LegajoModal';
import ExcelDateFilter from '../components/ExcelDateFilter';
import ExcelNumberRangeFilter from '../components/ExcelNumberRangeFilter';
import ExcelListFilter from '../components/ExcelListFilter';
import ExportExcelButton from '../components/ExportExcelButton';
import { Eye, Edit, Trash2 } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const CreditListPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAuditor = user?.rol === 'Auditor / Solo Lectura';
  const limit = 1000;
  
  const [filter, setFilter] = useState({ ID: [], IdExterno: '', Originador: '', CUIL: '', Capital: {}, Plazo: '', TNA: '', IdTasa: '', Estado: [], Fecha: [], TipoCredito: [], SaldoMora: {}, DiasMora: {} });
  const debouncedFilter = useDebounce(filter, 500);

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

  const fetchCreditos = async ({ queryKey }) => {
    const [_key, fCorte] = queryKey;
    const p = {
      skip: 0,
      limit: 100000,
      fecha_corte: fCorte
    };

    const res = await axiosClient.get('/api/v1/creditos', { params: p });
    return res.data;
  };

  const {
    data,
    isLoading: loading,
    isError,
    error,
    isFetching,
    refetch
  } = useQuery({
    queryKey: ['creditos', fechaCorte],
    queryFn: fetchCreditos,
    keepPreviousData: true
  });

  const creditos = useMemo(() => data?.items || [], [data]);
  const totalItems = data?.total || 0;

  const handleDelete = async (id) => {
    if (!window.confirm(`¿Está seguro que desea eliminar el crédito #${id}?`)) return;
    try {
      await axiosClient.delete(`/api/v1/creditos/${id}`);
      alert('Crédito eliminado con éxito.');
      queryClient.invalidateQueries({ queryKey: ['creditos'] });
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

  const filteredAndSortedCreditos = useMemo(() => {
    let result = [...creditos];
    
    // Filtros locales
    if (filter.ID && filter.ID.length > 0) {
      result = result.filter(c => filter.ID.includes(String(c.ID)));
    }
    if (filter.IdExterno) {
      const q = filter.IdExterno.toLowerCase();
      result = result.filter(c => c["ID Externo"] && String(c["ID Externo"]).toLowerCase().includes(q));
    }
    if (filter.Originador) {
      const q = filter.Originador.toLowerCase();
      result = result.filter(c => c["Socio Originador"] && String(c["Socio Originador"]).toLowerCase().includes(q));
    }
    if (filter.CUIL) {
      const q = filter.CUIL.toLowerCase();
      result = result.filter(c => c["Cliente CUIL"] && String(c["Cliente CUIL"]).toLowerCase().includes(q));
    }
    if (filter.Capital && (filter.Capital.min !== undefined || filter.Capital.max !== undefined)) {
      result = result.filter(c => {
        const val = c.Capital || 0;
        if (filter.Capital.min !== undefined && val < filter.Capital.min) return false;
        if (filter.Capital.max !== undefined && val > filter.Capital.max) return false;
        return true;
      });
    }
    if (filter.Plazo) {
      const q = filter.Plazo;
      result = result.filter(c => c.Plazo && String(c.Plazo) === q);
    }
    if (filter.TNA) {
      const q = filter.TNA;
      result = result.filter(c => c["TNA con IVA"] && String(c["TNA con IVA"]).includes(q));
    }
    if (filter.IdTasa) {
      const q = filter.IdTasa.toLowerCase();
      result = result.filter(c => c["ID Tasa Comision"] && String(c["ID Tasa Comision"]).toLowerCase().includes(q));
    }
    if (filter.TipoCredito && filter.TipoCredito.length > 0) {
      result = result.filter(c => filter.TipoCredito.includes(c["Tipo Crédito"]));
    }
    if (filter.Estado && filter.Estado.length > 0) {
      result = result.filter(c => filter.Estado.includes(c.Estado));
    }
    if (filter.SaldoMora && (filter.SaldoMora.min !== undefined || filter.SaldoMora.max !== undefined)) {
      result = result.filter(c => {
        const val = c["Saldo en Mora"] || 0;
        if (filter.SaldoMora.min !== undefined && val < filter.SaldoMora.min) return false;
        if (filter.SaldoMora.max !== undefined && val > filter.SaldoMora.max) return false;
        return true;
      });
    }
    if (filter.DiasMora && (filter.DiasMora.min !== undefined || filter.DiasMora.max !== undefined)) {
      result = result.filter(c => {
        const val = c["Días de Mora"] || 0;
        if (filter.DiasMora.min !== undefined && val < filter.DiasMora.min) return false;
        if (filter.DiasMora.max !== undefined && val > filter.DiasMora.max) return false;
        return true;
      });
    }
    if (filter.Fecha && filter.Fecha.length > 0) {
      result = result.filter(c => filter.Fecha.includes(c["Fecha Emisión"]));
    }

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
    return [...new Set(creditos.map(c => c.Estado).filter(Boolean))].sort();
  }, [creditos]);

  const AVAILABLE_CREDIT_IDS = useMemo(() => {
    return [...new Set(creditos.map(c => c.ID).filter(Boolean))].sort((a,b)=>a-b).map(String);
  }, [creditos]);

  const AVAILABLE_TIPOS_CREDITO = useMemo(() => {
    return [...new Set(creditos.map(c => c["Tipo Crédito"]).filter(Boolean))].sort();
  }, [creditos]);

  const AVAILABLE_FECHAS_EMISION = useMemo(() => {
    return [...new Set(creditos.map(c => c["Fecha Emisión"]).filter(Boolean))].sort();
  }, [creditos]);

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
          <button className="btn-primary" onClick={() => queryClient.invalidateQueries({ queryKey: ['creditos'] })} disabled={loading || isFetching} style={{ width: 'auto' }}>
            {(loading || isFetching) ? "Actualizando..." : "Actualizar Datos"}
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
                <th onClick={() => handleSort('ID Tasa Comision')} style={{ cursor: 'pointer' }}>
                  ID Tasa <SortIcon columnKey="ID Tasa Comision" />
                  <input type="text" placeholder="Filtrar..." value={filter.IdTasa} onChange={e => setFilter({ ...filter, IdTasa: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
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
                  <td colSpan="14" className="text-center empty-state" style={{ padding: '40px' }}>
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
                    <td>{c["ID Tasa Comision"] || '-'}</td>
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
                        {!isAuditor && (
                          <>
                            <button className="btn-secondary" onClick={() => setEditCredito({ id: c.ID, estado: c.Estado })} style={{ padding: '4px 8px', fontSize: '14px' }} title="Editar Estado">
                              ✏️
                            </button>
                            <button className="btn-secondary" onClick={() => handleDelete(c.ID)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar">
                              🗑️
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="4" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  TOTALES (Mostrando {creditos.length} de {totalItems}):
                </td>
                <td>{formatCurrency(totalCapital)}</td>
                <td colSpan="5"></td>
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
