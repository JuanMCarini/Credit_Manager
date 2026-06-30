import { useState, useMemo, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { useDebounce } from '../hooks/useDebounce';
import ExcelDateFilter from '../components/ExcelDateFilter';
import ExcelNumberRangeFilter from '../components/ExcelNumberRangeFilter';
import ExportExcelButton from '../components/ExportExcelButton';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const CollectionsListPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const queryParams = new URLSearchParams(location.search);
  const initialProcesoId = queryParams.get('proceso_id') || '';
  const queryClient = useQueryClient();

  // Tab State
  const [activeTab, setActiveTab] = useState(initialProcesoId ? 'cobranzas' : 'cobranzas');

  // --- COBRANZAS STATE ---
  const [page, setPage] = useState(0);
  const limit = 50;
  
  const [filter, setFilter] = useState({ 
    ID: '', 
    ProcesoID: initialProcesoId, 
    CUIL: '', 
    CreditoID: '', 
    Tipo: '',
    FechaVto: [],
    Capital: {},
    Interes: {},
    IVA: {},
    Total: {}
  });
  
  const debouncedFilter = useDebounce(filter, 500);

  // --- PROCESOS STATE ---
  const [procesos, setProcesos] = useState([]);
  const [loadingProcesos, setLoadingProcesos] = useState(false);
  const [filterProcesos, setFilterProcesos] = useState({ ID: '', Tipo: [], Estado: [], Fecha: [] });
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [showTipoFilter, setShowTipoFilter] = useState(false);
  const [showEstadoFilter, setShowEstadoFilter] = useState(false);

  // Edit Modal State for Procesos
  const [isEditing, setIsEditing] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [editFormData, setEditFormData] = useState({ estado: '', descripcion: '' });
  const [feedback, setFeedback] = useState(null);

  const TIPOS_DISPONIBLES = ['INDIVIDUAL', 'MASIVO_CSV'];
  const ESTADOS_DISPONIBLES = ['COMPLETADO', 'REVERTIDO', 'PROCESANDO', 'FALLIDO'];
  const AVAILABLE_FECHAS = useMemo(() => [...new Set(procesos.map(p => p["Fecha Ejecución"]).filter(Boolean))], [procesos]);

  // --- COBRANZAS FETCH ---
  const fetchCobranzas = async ({ queryKey }) => {
    const [_key, pageIndex, filters] = queryKey;
    const f = { ...filters };
    const p = { 
        skip: pageIndex * limit, 
        limit: limit,
        ...(f.ID && { id_cobranza: f.ID }),
        ...(f.ProcesoID && { proceso_id: f.ProcesoID }),
        ...(f.CUIL && { cuil: f.CUIL }),
        ...(f.CreditoID && { credito_id: f.CreditoID }),
        ...(f.Tipo && { tipo: f.Tipo }),
        ...(f.Capital?.min !== undefined && { capital_min: f.Capital.min }),
        ...(f.Capital?.max !== undefined && { capital_max: f.Capital.max }),
        ...(f.Interes?.min !== undefined && { interes_min: f.Interes.min }),
        ...(f.Interes?.max !== undefined && { interes_max: f.Interes.max }),
        ...(f.IVA?.min !== undefined && { iva_min: f.IVA.min }),
        ...(f.IVA?.max !== undefined && { iva_max: f.IVA.max }),
        ...(f.Total?.min !== undefined && { total_min: f.Total.min }),
        ...(f.Total?.max !== undefined && { total_max: f.Total.max }),
        ...(f.FechaVto && f.FechaVto.length > 0 && { vto_dates: f.FechaVto.join(',') }),
    };
    
    const res = await axiosClient.get('/api/v1/cobranzas', { params: p });
    return res.data;
  };

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: ['cobranzas', page, debouncedFilter],
    queryFn: fetchCobranzas,
  });

  const { data: procesosData } = useQuery({
    queryKey: ['procesos_list'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/procesos');
      return res.data;
    }
  });

  const cobranzas = data?.items || [];
  const totalItems = data?.total || 0;
  const availableTipos = data?.available_tipos || ['COMUN', 'ANTICIPO', 'CANCELACION ANTICIPADA', 'BONIFICACION POR CANCELACION ANTICIPADA', 'CUOTA NO COMPRADA', 'PENALTY', 'RECURSO', 'AJUSTE'];
  const availableVtoDates = data?.available_vto_dates || [];
  const totalPages = Math.ceil(totalItems / limit);

  const handleFilterChange = (key, value) => {
    setFilter(prev => ({ ...prev, [key]: value }));
    setPage(0);
  };

  const handleDeleteCobranza = async (id) => {
    if (window.confirm(`¿Estás seguro de que deseas eliminar la cobranza #${id}? Esta acción no se puede deshacer.`)) {
      try {
        await axiosClient.delete(`/api/v1/cobranzas/${id}`);
        queryClient.invalidateQueries({ queryKey: ['cobranzas'] });
        alert('Cobranza eliminada exitosamente.');
      } catch (error) {
        console.error('Error al eliminar cobranza:', error);
        alert(`Error al eliminar cobranza: ${error.response?.data?.detail || error.message}`);
      }
    }
  };

  const totals = useMemo(() => {
    if (data?.global_totals) {
      return data.global_totals;
    }
    return cobranzas.reduce((acc, curr) => ({
      capital: acc.capital + (curr.Capital || 0),
      interes: acc.interes + (curr['Interes'] || 0),
      iva: acc.iva + (curr.IVA || 0),
      total: acc.total + (curr.Total || 0)
    }), { capital: 0, interes: 0, iva: 0, total: 0 });
  }, [cobranzas, data]);

  // --- PROCESOS FETCH ---
  const fetchProcesos = async () => {
    setLoadingProcesos(true);
    try {
      const res = await axiosClient.get('/api/v1/procesos');
      setProcesos(res.data);
    } catch (error) {
      alert("Error cargando procesos: " + error.message);
    } finally {
      setLoadingProcesos(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'procesos' && procesos.length === 0) {
      fetchProcesos();
    }
  }, [activeTab]);

  const handleDeleteProceso = async (id) => {
    if (!window.confirm(`¿Está seguro que desea eliminar el proceso de ingesta #${id} junto con todas sus cobranzas asociadas?`)) return;
    try {
      await axiosClient.delete(`/api/v1/procesos/${id}`);
      alert('Proceso eliminado con éxito.');
      fetchProcesos();
      // Invalidate cobranzas query as they might have been deleted
      queryClient.invalidateQueries({ queryKey: ['cobranzas'] });
    } catch (error) {
      alert("Error eliminando proceso: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleEditOpen = (record) => {
    setEditingRecord(record);
    setEditFormData({
      estado: record.Estado || '',
      descripcion: record['Descripción'] || ''
    });
    setFeedback(null);
    setIsEditing(true);
  };

  const handleEditClose = () => {
    setIsEditing(false);
    setEditingRecord(null);
    setEditFormData({ estado: '', descripcion: '' });
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFeedback(null);
    try {
      await axiosClient.put(`/api/v1/procesos/${editingRecord.ID}`, {
        estado: editFormData.estado,
        descripcion: editFormData.descripcion || null
      });
      setFeedback({ type: 'success', message: 'Proceso actualizado exitosamente.' });
      await fetchProcesos();
      queryClient.invalidateQueries({ queryKey: ['procesos_list'] });
      setTimeout(() => handleEditClose(), 1500);
    } catch (error) {
      setFeedback({ type: 'error', message: error.response?.data?.detail || "Error al actualizar el proceso." });
    }
  };

  const handleSortProcesos = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const handleTipoToggle = (tipo) => {
    setFilterProcesos(prev => {
      const current = prev.Tipo;
      if (current.includes(tipo)) return { ...prev, Tipo: current.filter(e => e !== tipo) };
      return { ...prev, Tipo: [...current, tipo] };
    });
  };

  const handleEstadoToggle = (estado) => {
    setFilterProcesos(prev => {
      const current = prev.Estado;
      if (current.includes(estado)) return { ...prev, Estado: current.filter(e => e !== estado) };
      return { ...prev, Estado: [...current, estado] };
    });
  };

  const filteredAndSortedProcesos = useMemo(() => {
    let result = procesos.filter(p => !p.Tipo.startsWith('LIQUIDACIONES_'));

    if (filterProcesos.ID) result = result.filter(p => String(p.ID).includes(filterProcesos.ID));
    if (filterProcesos.Tipo.length > 0) result = result.filter(p => filterProcesos.Tipo.includes(p.Tipo));
    if (filterProcesos.Estado.length > 0) result = result.filter(p => filterProcesos.Estado.includes(p.Estado));
    if (filterProcesos.Fecha && filterProcesos.Fecha.length > 0) result = result.filter(p => filterProcesos.Fecha.includes(p["Fecha Ejecución"]));

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
  }, [procesos, filterProcesos, sortConfig]);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '5px' }}>↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Listado Global de Cobranzas y Procesos</h2>
          <p>Vista general de las últimas cobranzas, ajustes aplicados y procesos de ingesta.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {activeTab === 'cobranzas' && (
            <ExportExcelButton 
              data={cobranzas} 
              filteredData={cobranzas} 
              filename="cobranzas_export" 
            />
          )}
          {activeTab === 'procesos' && (
            <ExportExcelButton 
              data={procesos} 
              filteredData={filteredAndSortedProcesos} 
              filename="procesos_ingesta_export" 
            />
          )}
        </div>
      </header>

      <div className="tabs-container">
        <button className={`tab-button ${activeTab === 'cobranzas' ? 'active' : ''}`} onClick={() => setActiveTab('cobranzas')}>Cobranzas</button>
        <button className={`tab-button ${activeTab === 'procesos' ? 'active' : ''}`} onClick={() => setActiveTab('procesos')}>Procesos de Ingesta</button>
      </div>

      {activeTab === 'cobranzas' && (
        <>
          <div className="filter-panel glass-panel" style={{ marginBottom: '15px', padding: '15px', display: 'flex', gap: '15px', alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', fontWeight: 'bold' }}>Filtrar por Proceso de Ingesta</label>
              <select 
                value={filter.ProcesoID} 
                onChange={e => handleFilterChange('ProcesoID', e.target.value)}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-base)', color: 'var(--text-primary)' }}
              >
                <option value="">-- Todos los Procesos --</option>
                {procesosData && procesosData.map(p => (
                  <option key={p.ID} value={String(p.ID)}>
                    Lote #{p.ID} - {p.Tipo} ({p.Estado}) - {p["Fecha Ejecución"]}
                  </option>
                ))}
              </select>
              {filter.ProcesoID && procesosData && (() => {
                const selectedProceso = procesosData.find(p => String(p.ID) === String(filter.ProcesoID));
                if (!selectedProceso) return null;
                return (
                  <div style={{ marginTop: '8px', fontSize: '12px', fontWeight: 'bold', display: 'flex', gap: '15px', padding: '6px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Capital: {formatCurrency(selectedProceso.Capital)}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>Interés: {formatCurrency(selectedProceso.Interes)}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>IVA: {formatCurrency(selectedProceso.IVA)}</span>
                    <span style={{ color: 'var(--accent-primary)' }}>Total: {formatCurrency(selectedProceso.Total)}</span>
                  </div>
                );
              })()}
            </div>
            <div style={{ flex: 1 }}>
                <p style={{ fontSize: '12px', opacity: 0.7 }}>
                  Mostrando página {page + 1} de {totalPages || 1}. Total: {totalItems} registros. 
                  {isFetching && <span style={{ marginLeft: '10px', color: 'var(--accent-primary)' }}>Actualizando...</span>}
                </p>
            </div>
          </div>

          <div className="results-container glass-panel">
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>
                      ID
                      <input type="text" placeholder="ID..." value={filter.ID} onChange={e => handleFilterChange('ID', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                    </th>
                    <th>
                      Lote
                    </th>
                    <th>
                      CUIL
                      <input type="text" placeholder="CUIL..." value={filter.CUIL} onChange={e => handleFilterChange('CUIL', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                    </th>
                    <th>
                      Crédito
                      <input type="text" placeholder="Crédito..." value={filter.CreditoID} onChange={e => handleFilterChange('CreditoID', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                    </th>
                    <th>Cuota</th>
                    <th>
                      Fecha Vto
                      <div style={{ marginTop: '5px' }}>
                        <ExcelDateFilter 
                          availableDates={availableVtoDates}
                          selectedDates={filter.FechaVto || []}
                          onChange={dates => handleFilterChange('FechaVto', dates)}
                        />
                      </div>
                    </th>
                    <th>
                      Tipo
                      <details style={{ position: 'relative', marginTop: '5px' }}>
                        <summary style={{ fontSize: '11px', padding: '4px', cursor: 'pointer', background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: '4px', listStyle: 'none', userSelect: 'none' }}>
                          {filter.Tipo ? `${filter.Tipo.split(',').length} seleccionados` : 'Todos...'}
                        </summary>
                        <div style={{ position: 'absolute', top: '100%', left: 0, zIndex: 100, background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', width: '200px', maxHeight: '250px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', textAlign: 'left' }}>
                           {[
                             { val: 'COMUN', label: 'COMUN' },
                             { val: 'ANTICIPO', label: 'ANTICIPO' },
                             { val: 'CANCELACION ANTICIPADA', label: 'CANCELACION ANT.' },
                             { val: 'BONIFICACION POR CANCELACION ANTICIPADA', label: 'BONIFICACION CA' },
                             { val: 'CUOTA NO COMPRADA', label: 'CUOTA NO COMPRADA' },
                             { val: 'PENALTY', label: 'PENALTY' },
                             { val: 'RECURSO', label: 'RECURSO' },
                             { val: 'AJUSTE', label: 'AJUSTE' }
                           ].filter(op => availableTipos.includes(op.val)).map(op => {
                             const currentSelected = filter.Tipo ? filter.Tipo.split(',') : [];
                             const isChecked = currentSelected.includes(op.val);
                             const handleChange = (e) => {
                               let newSelected = [...currentSelected];
                               if (e.target.checked) newSelected.push(op.val);
                               else newSelected = newSelected.filter(v => v !== op.val);
                               handleFilterChange('Tipo', newSelected.join(','));
                             };
                             return (
                               <label key={op.val} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', cursor: 'pointer', fontWeight: 'normal' }}>
                                 <input type="checkbox" checked={isChecked} onChange={handleChange} />
                                 {op.label}
                               </label>
                             );
                           })}
                           {availableTipos.length === 0 && (
                             <div style={{ fontSize: '11px', color: 'var(--text-muted)', padding: '4px' }}>No hay tipos disponibles</div>
                           )}
                        </div>
                      </details>
                    </th>
                    <th>
                      Capital
                      <ExcelNumberRangeFilter selectedRange={filter.Capital} onChange={r => handleFilterChange('Capital', r)} />
                    </th>
                    <th>
                      Interés
                      <ExcelNumberRangeFilter selectedRange={filter.Interes} onChange={r => handleFilterChange('Interes', r)} />
                    </th>
                    <th>
                      IVA
                      <ExcelNumberRangeFilter selectedRange={filter.IVA} onChange={r => handleFilterChange('IVA', r)} />
                    </th>
                    <th>
                      Total Cobrado
                      <ExcelNumberRangeFilter selectedRange={filter.Total} onChange={r => handleFilterChange('Total', r)} />
                    </th>
                    <th>Fecha Pago</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan="13" className="text-center empty-state" style={{ padding: '40px' }}>
                        Cargando datos...
                      </td>
                    </tr>
                  ) : isError ? (
                    <tr>
                      <td colSpan="13" className="text-center empty-state" style={{ padding: '40px', color: 'red' }}>
                        Error cargando datos: {error.message}
                      </td>
                    </tr>
                  ) : cobranzas.length === 0 ? (
                    <tr>
                      <td colSpan="13" className="text-center empty-state" style={{ padding: '40px' }}>
                        No hay cobranzas para mostrar con los filtros actuales.
                      </td>
                    </tr>
                  ) : (
                    cobranzas.map(c => (
                      <tr key={c.ID}>
                        <td>{c.ID}</td>
                        <td>{c["Proceso ID"]}</td>
                        <td>{c["Cliente CUIL"]}</td>
                        <td>{c["Credito ID"]}</td>
                        <td>{c["Cuota Nro"]}</td>
                        <td>{c["Fecha Vencimiento"]}</td>
                        <td>
                           <span className={`status-badge status-${(c.Tipo || '').toLowerCase().replace(/ /g, '-')}`}>
                             {c.Tipo}
                           </span>
                        </td>
                        <td>{formatCurrency(c.Capital)}</td>
                        <td>{formatCurrency(c['Interes'])}</td>
                        <td>{formatCurrency(c.IVA)}</td>
                        <td style={{ fontWeight: 'bold' }}>{formatCurrency(c.Total)}</td>
                        <td>{c["Fecha Emision"]}</td>
                        <td>
                          <button 
                            className="btn-danger" 
                            onClick={() => handleDeleteCobranza(c.ID)}
                            title="Eliminar Cobranza"
                            style={{ padding: '5px 10px', fontSize: '14px', background: 'transparent', color: 'var(--danger-color)' }}
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
                <tfoot style={{ background: 'rgba(255, 255, 255, 0.05)', fontWeight: 'bold' }}>
                  {(() => {
                    let loteRow = null;
                    
                    if (filter.ProcesoID && procesosData) {
                      const selectedProceso = procesosData.find(p => String(p.ID) === String(filter.ProcesoID));
                      if (selectedProceso) {
                        loteRow = (
                          <tr style={{ opacity: 0.8, fontSize: '0.95em' }}>
                            <td colSpan="7" style={{ textAlign: 'right' }}>TOTALES (Lote #{selectedProceso.ID}):</td>
                            <td>{formatCurrency(selectedProceso.Capital)}</td>
                            <td>{formatCurrency(selectedProceso.Interes)}</td>
                            <td>{formatCurrency(selectedProceso.IVA)}</td>
                            <td style={{ color: 'var(--text-muted)' }}>{formatCurrency(selectedProceso.Total)}</td>
                            <td></td>
                            <td></td>
                          </tr>
                        );
                      }
                    }
                    
                    return (
                      <>
                        {loteRow}
                        <tr>
                          <td colSpan="7" style={{ textAlign: 'right' }}>TOTALES (Filtro Actual):</td>
                          <td>{formatCurrency(totals.capital)}</td>
                          <td>{formatCurrency(totals.interes)}</td>
                          <td>{formatCurrency(totals.iva)}</td>
                          <td style={{ color: 'var(--accent-secondary)' }}>{formatCurrency(totals.total)}</td>
                          <td></td>
                          <td></td>
                        </tr>
                      </>
                    );
                  })()}
                </tfoot>
              </table>
            </div>
            
            {/* Paginación */}
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '15px', gap: '10px' }}>
              <button 
                className="btn-secondary" 
                onClick={() => setPage(old => Math.max(old - 1, 0))}
                disabled={page === 0}
                style={{ width: 'auto', padding: '5px 15px' }}
              >
                Anterior
              </button>
              <span>Página {page + 1} de {totalPages || 1}</span>
              <button 
                className="btn-secondary" 
                onClick={() => setPage(old => (old + 1 < totalPages ? old + 1 : old))}
                disabled={page + 1 >= totalPages || totalPages === 0}
                style={{ width: 'auto', padding: '5px 15px' }}
              >
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}

      {activeTab === 'procesos' && (
        <div className="results-container glass-panel">
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '10px' }}>
            <button className="btn-secondary" onClick={fetchProcesos} disabled={loadingProcesos} style={{ width: 'auto', padding: '5px 15px', fontSize: '12px' }}>
              {loadingProcesos ? "Actualizando..." : "Actualizar Datos"}
            </button>
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th onClick={() => handleSortProcesos('ID')} style={{ cursor: 'pointer' }}>
                    ID Lote <SortIcon columnKey="ID" />
                    <input type="text" placeholder="Filtrar ID..." value={filterProcesos.ID} onChange={e => setFilterProcesos({ ...filterProcesos, ID: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                  </th>
                  
                  <th onClick={() => handleSortProcesos('Tipo')} style={{ cursor: 'pointer' }}>
                    Tipo <SortIcon columnKey="Tipo" />
                    <div onClick={e => { e.stopPropagation(); setShowTipoFilter(!showTipoFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                      {filterProcesos.Tipo.length === 0 ? "Todos" : `${filterProcesos.Tipo.length} selec.`}
                    </div>
                    {showTipoFilter && (
                      <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px' }}>
                        {TIPOS_DISPONIBLES.map(est => (
                          <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer' }}>
                            <input type="checkbox" checked={filterProcesos.Tipo.includes(est)} onChange={() => handleTipoToggle(est)} />
                            {est}
                          </label>
                        ))}
                      </div>
                    )}
                  </th>
                  
                  <th onClick={() => handleSortProcesos('Estado')} style={{ cursor: 'pointer' }}>
                    Estado <SortIcon columnKey="Estado" />
                    <div onClick={e => { e.stopPropagation(); setShowEstadoFilter(!showEstadoFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                      {filterProcesos.Estado.length === 0 ? "Todos" : `${filterProcesos.Estado.length} selec.`}
                    </div>
                    {showEstadoFilter && (
                      <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px' }}>
                        {ESTADOS_DISPONIBLES.map(est => (
                          <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer' }}>
                            <input type="checkbox" checked={filterProcesos.Estado.includes(est)} onChange={() => handleEstadoToggle(est)} />
                            {est}
                          </label>
                        ))}
                      </div>
                    )}
                  </th>

                  <th onClick={() => handleSortProcesos('Descripción')} style={{ cursor: 'pointer' }}>
                    Descripción <SortIcon columnKey="Descripción" />
                  </th>

                  <th onClick={() => handleSortProcesos('Fecha Ejecución')} style={{ cursor: 'pointer' }}>
                    Fecha Ejecución <SortIcon columnKey="Fecha Ejecución" />
                    <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                      <ExcelDateFilter 
                        availableDates={AVAILABLE_FECHAS}
                        selectedDates={filterProcesos.Fecha}
                        onChange={dates => setFilterProcesos({ ...filterProcesos, Fecha: dates })}
                      />
                    </div>
                  </th>
                  
                  <th style={{textAlign: 'center'}}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedProcesos.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="text-center empty-state" style={{ padding: '40px' }}>
                      {loadingProcesos ? "Cargando..." : "No hay procesos para mostrar con los filtros actuales."}
                    </td>
                  </tr>
                ) : (
                  filteredAndSortedProcesos.map(p => (
                    <tr key={p.ID}>
                      <td>{p.ID}</td>
                      <td>
                         <span className={`status-badge status-${(p.Tipo || '').toLowerCase().replace(/ /g, '-')}`}>
                           {p.Tipo}
                         </span>
                      </td>
                      <td>
                         <span className={`status-badge status-${(p.Estado || '').toLowerCase()}`}>
                           {p.Estado}
                         </span>
                      </td>
                      <td>{p["Descripción"] || "-"}</td>
                      <td>{p["Fecha Ejecución"]}</td>
                      <td>
                        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
                          <button className="btn-secondary" onClick={() => {
                            setFilter(prev => ({ ...prev, ProcesoID: String(p.ID) }));
                            setPage(0);
                            setActiveTab('cobranzas');
                          }} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Cobranzas del Lote">
                            👁️
                          </button>
                          <button className="btn-secondary" onClick={() => handleEditOpen(p)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Editar Proceso">
                            ✏️
                          </button>
                          <button className="btn-secondary" onClick={() => handleDeleteProceso(p.ID)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar Proceso">
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {isEditing && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
          backdropFilter: 'blur(4px)'
        }}>
          <div className="glass-panel" style={{
            width: '100%', maxWidth: '500px',
            position: 'relative', padding: '32px'
          }}>
            <button onClick={handleEditClose} className="btn-secondary" style={{
              position: 'absolute', top: '16px', right: '16px', padding: '4px 12px'
            }}>X</button>
            <h3 style={{ marginBottom: '24px', fontFamily: 'var(--font-heading)' }}>
              Editar Proceso #{editingRecord?.ID}
            </h3>
            
            {feedback && (
              <div style={{ 
                marginBottom: '20px', padding: '12px', borderRadius: '8px', fontSize: '14px',
                backgroundColor: feedback.type === 'error' ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)', 
                color: feedback.type === 'error' ? 'var(--danger-color)' : 'var(--success-color)' 
              }}>
                {feedback.message}
              </div>
            )}

            <form onSubmit={handleEditSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="form-group">
                <label>Estado del Proceso</label>
                <select 
                  value={editFormData.estado} 
                  onChange={e => setEditFormData({...editFormData, estado: e.target.value})}
                  className="input-field"
                  required
                >
                  <option value="">Seleccione Estado...</option>
                  {ESTADOS_DISPONIBLES.map(est => <option key={est} value={est}>{est}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label>Descripción / Observaciones</label>
                <textarea 
                  value={editFormData.descripcion} 
                  onChange={e => setEditFormData({...editFormData, descripcion: e.target.value})}
                  className="input-field"
                  rows="3"
                  placeholder="Ingrese observaciones sobre este lote de cobranzas..."
                />
              </div>

              <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button type="button" onClick={handleEditClose} className="btn-secondary">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Guardar Cambios
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </section>
  );
};

export default CollectionsListPage;
