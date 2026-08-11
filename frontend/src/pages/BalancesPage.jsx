import React, { useState, useMemo } from 'react';
import { FilterX } from 'lucide-react';
import axiosClient, { downloadFile } from '../api/axiosClient';
import ExportExcelButton from '../components/ExportExcelButton';
import ExcelDateFilter from '../components/ExcelDateFilter';
import ExcelNumberRangeFilter from '../components/ExcelNumberRangeFilter';
import ExcelListFilter from '../components/ExcelListFilter';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const BalancesPage = () => {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [activeGroups, setActiveGroups] = useState([]);
  const [reportDate, setReportDate] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const [tableFilters, setTableFilters] = useState({});
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  const [filters, setFilters] = useState({
    fecha: new Date().toISOString().split('T')[0],
    conSaldo: true,
    propias: ''
  });

  const availableGroups = {
    credito: 'ID Crédito',
    clientes: 'Cliente',
    carteras: 'Cartera',
    socios: 'Proveedor/Socio',
    originador: 'Originador',
    vencimientos: 'Vencimiento',
    dueno: 'Dueño',
    recurso: 'Recurso',
    iva: 'Tasa IVA'
  };

  const [selectedGroupings, setSelectedGroupings] = useState([]);

  const handleGroupChange = (key) => {
    setSelectedGroupings(prev => {
      if (prev.includes(key)) {
        return prev.filter(k => k !== key);
      } else {
        return [...prev, key];
      }
    });
  };

  const buildParams = () => {
    const params = new URLSearchParams();
    if (filters.fecha) params.append('fecha', filters.fecha);
    if (!filters.conSaldo) params.append('con_saldo', 'false');
    if (filters.propias !== '') params.append('propias', filters.propias);

    if (selectedGroupings.length > 0) {
      params.append('agrupar', 'true');
      params.append('agrupadores', selectedGroupings.join(','));
    }
    return params;
  };

  const handleConsultar = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const params = buildParams();
      const res = await axiosClient.get(`/api/v1/reports/balances?${params}`);
      
      const groupMapper = {
        credito: { id: 'ID Credito', label: 'ID Crédito' },
        clientes: { id: 'CUIL Cliente', label: 'Cliente' },
        carteras: { id: 'ID Cartera', label: 'Cartera' },
        socios: { id: 'Proveedor', label: 'Proveedor/Socio' },
        originador: { id: 'Originador', label: 'Originador' },
        vencimientos: { id: 'Fecha Vencimiento', label: 'Vencimiento' },
        dueno: { id: 'Dueño', label: 'Dueño' },
        recurso: { id: 'recurso', label: 'Recurso' },
        iva: { id: 'iva_operado', label: 'Tasa IVA' }
      };
      
      const newActiveGroups = selectedGroupings.map(k => groupMapper[k]);
      setActiveGroups(newActiveGroups);
      setResults(res.data);
      setTableFilters({});
      setSortConfig({ key: null, direction: 'asc' });
      setReportDate(filters.fecha ? new Date(filters.fecha + 'T00:00:00') : new Date());
      setHasSearched(true);
    } catch (error) {
      alert("Error: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExportarExcel = async () => {
    try {
      const params = buildParams();
      await downloadFile(`/api/v1/reports/balances/excel`, params, 'reporte_saldos.xlsx');
    } catch (error) {
      alert("Error descargando Excel: " + error.message);
    }
  };

  const isGrouping = activeGroups.length > 0;
  
  let columns = [];
  if (isGrouping) {
    columns = activeGroups.map(g => ({ label: g.label, key: g.id })).concat([
      { label: "Capital", key: "Capital" },
      { label: "Interés", key: "Interés" },
      { label: "IVA", key: "IVA" },
      { label: "Total Saldo", key: "Total" }
    ]);
  } else {
    columns = [
      { label: "ID Crédito", key: "ID Credito" },
      { label: "Proveedor", key: "Proveedor" },
      { label: "Originador", key: "Originador" },
      { label: "Cliente CUIL", key: "CUIL Cliente" },
      { label: "Cartera", key: "ID Cartera" },
      { label: "Nro. Cuota", key: "Nro. Cuota" },
      { label: "Fecha Vencimiento", key: "Fecha Vencimiento" },
      { label: "Capital", key: "Capital" },
      { label: "Interés", key: "Interés" },
      { label: "IVA", key: "IVA" },
      { label: "Total Saldo", key: "Total" }
    ];
  }

  const filteredAndSortedResults = useMemo(() => {
    let res = [...results];

    // Aplicar filtros
    Object.keys(tableFilters).forEach(key => {
      const filterVal = tableFilters[key];
      if (!filterVal || (Array.isArray(filterVal) && filterVal.length === 0)) return;
      if (typeof filterVal === 'object' && !Array.isArray(filterVal)) {
        if (filterVal.min === undefined && filterVal.max === undefined) return;
      }
      
      res = res.filter(row => {
        let rowVal = row[key];
        if (key === "Total") rowVal = row.Total || row.total; // Support fallback for Total
        
        if (Array.isArray(filterVal)) {
          return filterVal.includes(rowVal);
        } else if (typeof filterVal === 'object' && filterVal !== null) {
          // Es un rango numérico
          const numVal = Number(rowVal);
          if (isNaN(numVal)) return false;
          if (filterVal.min !== undefined && numVal < filterVal.min) return false;
          if (filterVal.max !== undefined && numVal > filterVal.max) return false;
          return true;
        } else {
          if (rowVal === null || rowVal === undefined) return false;
          return String(rowVal).toLowerCase().includes(String(filterVal).toLowerCase());
        }
      });
    });

    // Aplicar ordenamiento
    if (sortConfig.key) {
      res.sort((a, b) => {
        let valA = a[sortConfig.key];
        let valB = b[sortConfig.key];
        if (sortConfig.key === "Total") {
          valA = a.Total || a.total;
          valB = b.Total || b.total;
        }
        
        if (valA === null || valA === undefined) valA = '';
        if (valB === null || valB === undefined) valB = '';
        
        if (typeof valA === 'string' && typeof valB === 'string') {
          valA = valA.toLowerCase();
          valB = valB.toLowerCase();
        }
        
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return res;
  }, [results, tableFilters, sortConfig]);

  const totals = useMemo(() => {
    return filteredAndSortedResults.reduce((acc, curr) => ({
      capital: acc.capital + (curr.Capital || 0),
      interes: acc.interes + (curr['Interés'] || 0),
      iva: acc.iva + (curr.IVA || 0),
      total: acc.total + (curr.Total || curr.total || 0)
    }), { capital: 0, interes: 0, iva: 0, total: 0 });
  }, [filteredAndSortedResults]);

  const availableFechas = useMemo(() => {
    const dates = new Set();
    results.forEach(r => {
      if (r['Fecha Vencimiento']) dates.add(r['Fecha Vencimiento']);
    });
    return Array.from(dates).sort();
  }, [results]);

  const availableCreditIds = useMemo(() => {
    const ids = new Set();
    results.forEach(r => {
      if (r['ID Credito']) ids.add(String(r['ID Credito']));
    });
    return Array.from(ids).sort((a,b)=>Number(a)-Number(b));
  }, [results]);

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '5px' }}>↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Reporte de Saldos de Cartera</h2>
        <p>Métricas consolidadas directamente del Core Engine de base de datos.</p>
      </header>

      <div className="controls-panel glass-panel form-container" style={{ marginBottom: '32px' }}>
        <form onSubmit={handleConsultar} className="balances-controls" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', gap: '24px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="form-group inline" style={{ marginBottom: 0, flexDirection: 'row', alignItems: 'center' }}>
              <label style={{ marginRight: '8px' }}>Fecha de Corte:</label>
              <input type="date" value={filters.fecha} onChange={e => setFilters({...filters, fecha: e.target.value})} style={{ width: 'auto' }} />
            </div>

            <div className="filters-options" style={{ display: 'flex', gap: '16px', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                <input type="checkbox" checked={filters.conSaldo} onChange={e => setFilters({...filters, conSaldo: e.target.checked})} /> Con Saldo Deudor
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                Propiedad:
                <select value={filters.propias} onChange={e => setFilters({...filters, propias: e.target.value})} style={{ marginLeft: '8px', padding: '4px', width: 'auto' }}>
                  <option value="">Todas</option>
                  <option value="true">Propias</option>
                  <option value="false">Terceros</option>
                </select>
              </label>
            </div>
          </div>

          <div className="input-group">
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Agrupar por (el orden de selección define la jerarquía):</label>
            
            {selectedGroupings.length > 0 && (
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Orden:</span>
                {selectedGroupings.map((key, index) => (
                  <React.Fragment key={`pill-${key}`}>
                    <div style={{ 
                      background: 'var(--primary)', 
                      color: 'white', 
                      padding: '4px 12px', 
                      borderRadius: '16px',
                      fontSize: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}>
                      <span style={{ opacity: 0.7 }}>{index + 1}.</span> 
                      {availableGroups[key]}
                      <button type="button" onClick={() => handleGroupChange(key)} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', padding: '0 0 0 4px', fontSize: '1rem', lineHeight: 1 }}>&times;</button>
                    </div>
                    {index < selectedGroupings.length - 1 && <span style={{ color: 'var(--text-secondary)' }}>&gt;</span>}
                  </React.Fragment>
                ))}
              </div>
            )}

            <div className="grouping-options" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
              {Object.entries(availableGroups).map(([key, label]) => (
                <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input type="checkbox" checked={selectedGroupings.includes(key)} onChange={() => handleGroupChange(key)} /> 
                  {label}
                </label>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" className="btn-secondary" onClick={handleExportarExcel} style={{ minWidth: '150px' }}>
               Descargar Excel
            </button>
            <button type="submit" className="btn-primary" disabled={loading} style={{ minWidth: '200px' }}>
              {loading ? "Consultando..." : "Consultar Reporte"}
            </button>
          </div>
        </form>
      </div>

      {hasSearched && (
        <div className="table-container glass-panel fade-in" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, fontFamily: 'var(--font-heading)' }}>Resultados del Reporte</h3>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button 
                className="btn-secondary" 
                onClick={() => setTableFilters({})}
                title="Limpiar todos los filtros de la tabla"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', height: '100%', padding: '0 12px' }}
              >
                <FilterX size={16} /> Limpiar Filtros
              </button>
              <ExportExcelButton data={results} filteredData={filteredAndSortedResults} filename="balances_export" />
            </div>
          </div>
          <div className="table-responsive" style={{ maxHeight: '500px', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  {columns.map((col, i) => {
                    const isCurrency = ["Capital", "Interés", "IVA", "Total", "Total Saldo"].includes(col.label);
                    
                    return (
                      <th key={i} onClick={() => handleSort(col.key)} style={{ cursor: 'pointer' }}>
                        {col.label} <SortIcon columnKey={col.key} />
                        {col.key === 'Fecha Vencimiento' ? (
                          <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                            <ExcelDateFilter 
                              availableDates={availableFechas}
                              selectedDates={tableFilters[col.key] || []}
                              onChange={dates => setTableFilters({ ...tableFilters, [col.key]: dates })}
                            />
                          </div>
                        ) : col.key === 'ID Credito' ? (
                          <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                            <ExcelListFilter 
                              availableOptions={availableCreditIds}
                              selectedOptions={tableFilters[col.key] || []}
                              onChange={ids => setTableFilters({ ...tableFilters, [col.key]: ids })}
                              title="Filtrar IDs..."
                            />
                          </div>
                        ) : isCurrency ? (
                          <div onClick={e => e.stopPropagation()}>
                            <ExcelNumberRangeFilter
                              selectedRange={tableFilters[col.key] || {}}
                              onChange={range => setTableFilters({ ...tableFilters, [col.key]: range })}
                            />
                          </div>
                        ) : (
                          <input 
                            type="text" 
                            placeholder={`Filtrar...`} 
                            value={tableFilters[col.key] || ''} 
                            onChange={e => setTableFilters({ ...tableFilters, [col.key]: e.target.value })} 
                            onClick={e => e.stopPropagation()} 
                            style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} 
                          />
                        )}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedResults.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="text-center empty-state">No se encontraron saldos que coincidan con los filtros.</td>
                  </tr>
                ) : (
                  filteredAndSortedResults.map((row, i) => {
                    let colorTotal = "var(--accent-secondary)";
                    if (row['Fecha Vencimiento']) {
                      const vto = new Date(row['Fecha Vencimiento'] + 'T00:00:00');
                      const cutoff = new Date(reportDate);
                      cutoff.setHours(0, 0, 0, 0);
                      if (vto < cutoff) colorTotal = "var(--error)";
                    }

                    if (isGrouping) {
                      return (
                        <tr key={i}>
                          {activeGroups.map((g, gi) => (
                            <td key={gi}>{(row[g.id] !== undefined && row[g.id] !== null) ? row[g.id] : '-'}</td>
                          ))}
                          <td>{formatCurrency(row.Capital || 0)}</td>
                          <td>{formatCurrency(row['Interés'] || 0)}</td>
                          <td>{formatCurrency(row.IVA || 0)}</td>
                          <td style={{ fontWeight: 600, color: colorTotal }}>{formatCurrency(row.Total || 0)}</td>
                        </tr>
                      );
                    } else {
                      return (
                        <tr key={i}>
                          <td>{row['ID Credito'] || '-'}</td>
                          <td>{row.Proveedor || '-'}</td>
                          <td>{row.Originador || '-'}</td>
                          <td>{row['CUIL Cliente'] || '-'}</td>
                          <td>{row['ID Cartera'] || '-'}</td>
                          <td>{row['Nro. Cuota'] || '-'}</td>
                          <td>{row['Fecha Vencimiento'] || '-'}</td>
                          <td>{formatCurrency(row.Capital || 0)}</td>
                          <td>{formatCurrency(row['Interés'] || 0)}</td>
                          <td>{formatCurrency(row.IVA || 0)}</td>
                          <td style={{ fontWeight: 600, color: colorTotal }}>{formatCurrency(row.Total || row.total || 0)}</td>
                        </tr>
                      );
                    }
                  })
                )}
              </tbody>
              {filteredAndSortedResults.length > 0 && (
                <tfoot>
                  <tr>
                    <td colSpan={columns.length - 4} style={{ textAlign: 'right' }}>TOTALES VISIBLES:</td>
                    <td>{formatCurrency(totals.capital)}</td>
                    <td>{formatCurrency(totals.interes)}</td>
                    <td>{formatCurrency(totals.iva)}</td>
                    <td style={{ color: 'var(--accent-secondary)' }}>{formatCurrency(totals.total)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      )}
    </section>
  );
};

export default BalancesPage;
