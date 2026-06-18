import { useState, useEffect, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import axiosClient from '../api/axiosClient';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const CollectionsListPage = () => {
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const initialProcesoId = queryParams.get('proceso_id') || '';

  const [cobranzas, setCobranzas] = useState([]);
  const [procesos, setProcesos] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const [filter, setFilter] = useState({ ID: '', ProcesoID: initialProcesoId, CUIL: '', CreditoID: '', CuotaNro: '', Tipo: [], Total: '', Fecha: { start: '', end: '' } });
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [showTipoFilter, setShowTipoFilter] = useState(false);

  const getFilteredData = (excludeKey = null) => {
    let result = [...cobranzas];
    if (excludeKey !== 'ID' && filter.ID) result = result.filter(c => String(c.ID).includes(filter.ID));
    if (excludeKey !== 'ProcesoID' && filter.ProcesoID) result = result.filter(c => String(c["Proceso ID"]) === filter.ProcesoID);
    if (excludeKey !== 'CUIL' && filter.CUIL) result = result.filter(c => c["Cliente CUIL"] && c["Cliente CUIL"].includes(filter.CUIL));
    if (excludeKey !== 'CreditoID' && filter.CreditoID) result = result.filter(c => String(c["Crédito ID"]).includes(filter.CreditoID));
    if (excludeKey !== 'CuotaNro' && filter.CuotaNro) result = result.filter(c => String(c["Cuota Nro"]).includes(filter.CuotaNro));
    if (excludeKey !== 'Tipo' && filter.Tipo.length > 0) result = result.filter(c => filter.Tipo.includes(c.Tipo));
    if (excludeKey !== 'Total' && filter.Total) result = result.filter(c => String(c.Total).includes(filter.Total));
    if (excludeKey !== 'Fecha' && filter.Fecha.start) result = result.filter(c => c["Fecha Emisión"] >= filter.Fecha.start);
    if (excludeKey !== 'Fecha' && filter.Fecha.end) result = result.filter(c => c["Fecha Emisión"] <= filter.Fecha.end);
    return result;
  };

  const TIPOS_DISPONIBLES = useMemo(() => {
    const data = getFilteredData('Tipo');
    return [...new Set(data.map(c => c.Tipo))].filter(Boolean).sort();
  }, [cobranzas, filter]);

  const procesosDisponibles = useMemo(() => {
    const data = getFilteredData('ProcesoID');
    const idsEnCobranzas = new Set(data.map(c => String(c["Proceso ID"])));
    return procesos.filter(p => idsEnCobranzas.has(String(p.ID)));
  }, [procesos, cobranzas, filter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [resCobranzas, resProcesos] = await Promise.all([
        axiosClient.get('/api/v1/cobranzas'),
        axiosClient.get('/api/v1/procesos')
      ]);
      setCobranzas(resCobranzas.data);
      setProcesos(resProcesos.data);
    } catch (error) {
      alert("Error cargando datos: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const handleTipoToggle = (tipo) => {
    setFilter(prev => {
      const current = prev.Tipo;
      if (current.includes(tipo)) return { ...prev, Tipo: current.filter(e => e !== tipo) };
      return { ...prev, Tipo: [...current, tipo] };
    });
  };

  const filteredAndSortedCobranzas = useMemo(() => {
    let result = getFilteredData(null);

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
  }, [cobranzas, filter, sortConfig]);

  const totals = useMemo(() => {
    return filteredAndSortedCobranzas.reduce((acc, curr) => ({
      capital: acc.capital + (curr.Capital || 0),
      interes: acc.interes + (curr['Interés'] || 0),
      iva: acc.iva + (curr.IVA || 0),
      total: acc.total + (curr.Total || 0)
    }), { capital: 0, interes: 0, iva: 0, total: 0 });
  }, [filteredAndSortedCobranzas]);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '5px' }}>↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Listado Global de Cobranzas</h2>
          <p>Vista general de las últimas cobranzas y ajustes aplicados.</p>
        </div>
        <button className="btn-primary" onClick={fetchData} disabled={loading} style={{ width: 'auto' }}>
          {loading ? "Actualizando..." : "Actualizar Datos"}
        </button>
      </header>

      <div className="filter-panel glass-panel" style={{ marginBottom: '15px', padding: '15px', display: 'flex', gap: '15px', alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', fontWeight: 'bold' }}>Filtrar por Proceso de Ingesta</label>
          <select 
            value={filter.ProcesoID} 
            onChange={e => setFilter({ ...filter, ProcesoID: e.target.value })}
            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-base)', color: 'var(--text-primary)' }}
          >
            <option value="">-- Todos los Procesos --</option>
            {procesosDisponibles.map(p => (
              <option key={p.ID} value={String(p.ID)}>
                Lote #{p.ID} - {p.Tipo} ({p.Estado}) - {p["Fecha Ejecución"]}
              </option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1 }}>
            <p style={{ fontSize: '12px', opacity: 0.7 }}>Mostrando {filteredAndSortedCobranzas.length} registros. (Max 5000 en memoria)</p>
        </div>
      </div>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('ID')} style={{ cursor: 'pointer' }}>
                  ID <SortIcon columnKey="ID" />
                  <input type="text" placeholder="Filtrar ID..." value={filter.ID} onChange={e => setFilter({ ...filter, ID: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Proceso ID')} style={{ cursor: 'pointer' }}>
                  Lote <SortIcon columnKey="Proceso ID" />
                  <input type="text" placeholder="Filtrar Lote..." value={filter.ProcesoID} onChange={e => setFilter({ ...filter, ProcesoID: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Cliente CUIL')} style={{ cursor: 'pointer' }}>
                  CUIL <SortIcon columnKey="Cliente CUIL" />
                  <input type="text" placeholder="Buscar..." value={filter.CUIL} onChange={e => setFilter({ ...filter, CUIL: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Crédito ID')} style={{ cursor: 'pointer' }}>
                  Crédito <SortIcon columnKey="Crédito ID" />
                  <input type="text" placeholder="Filtrar Crédito..." value={filter.CreditoID} onChange={e => setFilter({ ...filter, CreditoID: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Cuota Nro')} style={{ cursor: 'pointer' }}>
                  Cuota <SortIcon columnKey="Cuota Nro" />
                  <input type="text" placeholder="Filtrar Cuota..." value={filter.CuotaNro} onChange={e => setFilter({ ...filter, CuotaNro: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Fecha Vencimiento')} style={{ cursor: 'pointer' }}>
                  Fecha Vto <SortIcon columnKey="Fecha Vencimiento" />
                </th>
                <th onClick={() => handleSort('Tipo')} style={{ cursor: 'pointer', position: 'relative' }}>
                  Tipo <SortIcon columnKey="Tipo" />
                  <div onClick={e => { e.stopPropagation(); setShowTipoFilter(!showTipoFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                    {filter.Tipo.length === 0 ? "Todos" : `${filter.Tipo.length} selec.`}
                  </div>
                  {showTipoFilter && (
                    <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, minWidth: 'max-content', zIndex: 100, background: 'var(--bg-base)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px', textAlign: 'left' }}>
                      {TIPOS_DISPONIBLES.map(est => (
                        <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                          <input type="checkbox" checked={filter.Tipo.includes(est)} onChange={() => handleTipoToggle(est)} />
                          {est}
                        </label>
                      ))}
                    </div>
                  )}
                </th>
                <th onClick={() => handleSort('Capital')} style={{ cursor: 'pointer' }}>
                  Capital <SortIcon columnKey="Capital" />
                </th>
                <th onClick={() => handleSort('Interés')} style={{ cursor: 'pointer' }}>
                  Interés <SortIcon columnKey="Interés" />
                </th>
                <th onClick={() => handleSort('IVA')} style={{ cursor: 'pointer' }}>
                  IVA <SortIcon columnKey="IVA" />
                </th>
                <th onClick={() => handleSort('Total')} style={{ cursor: 'pointer' }}>
                  Total Cobrado <SortIcon columnKey="Total" />
                  <input type="text" placeholder="Filtrar Total..." value={filter.Total} onChange={e => setFilter({ ...filter, Total: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Fecha Emisión')} style={{ cursor: 'pointer' }}>
                  Fecha Pago <SortIcon columnKey="Fecha Emisión" />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <input type="date" value={filter.Fecha.start} onChange={e => setFilter({ ...filter, Fecha: { ...filter.Fecha, start: e.target.value } })} style={{ width: '100%', padding: '4px', fontSize: '10px' }} title="Desde" />
                    <input type="date" value={filter.Fecha.end} onChange={e => setFilter({ ...filter, Fecha: { ...filter.Fecha, end: e.target.value } })} style={{ width: '100%', padding: '4px', fontSize: '10px' }} title="Hasta" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedCobranzas.length === 0 ? (
                <tr>
                  <td colSpan="12" className="text-center empty-state" style={{ padding: '40px' }}>
                    {loading ? "Cargando..." : "No hay cobranzas para mostrar con los filtros actuales."}
                  </td>
                </tr>
              ) : (
                filteredAndSortedCobranzas.map(c => (
                  <tr key={c.ID}>
                    <td>{c.ID}</td>
                    <td>{c["Proceso ID"]}</td>
                    <td>{c["Cliente CUIL"]}</td>
                    <td>{c["Crédito ID"]}</td>
                    <td>{c["Cuota Nro"]}</td>
                    <td>{c["Fecha Vencimiento"]}</td>
                    <td>
                       <span className={`status-badge status-${(c.Tipo || '').toLowerCase().replace(/ /g, '-')}`}>
                         {c.Tipo}
                       </span>
                    </td>
                    <td>{formatCurrency(c.Capital)}</td>
                    <td>{formatCurrency(c['Interés'])}</td>
                    <td>{formatCurrency(c.IVA)}</td>
                    <td style={{ fontWeight: 'bold' }}>{formatCurrency(c.Total)}</td>
                    <td>{c["Fecha Emisión"]}</td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot style={{ background: 'rgba(255, 255, 255, 0.05)', fontWeight: 'bold' }}>
              <tr>
                <td colSpan="7" style={{ textAlign: 'right' }}>TOTALES:</td>
                <td>{formatCurrency(totals.capital)}</td>
                <td>{formatCurrency(totals.interes)}</td>
                <td>{formatCurrency(totals.iva)}</td>
                <td style={{ color: 'var(--accent-secondary)' }}>{formatCurrency(totals.total)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </section>
  );
};

export default CollectionsListPage;
