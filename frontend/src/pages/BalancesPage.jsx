import { useState } from 'react';
import axiosClient, { downloadFile } from '../api/axiosClient';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const BalancesPage = () => {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [activeGroups, setActiveGroups] = useState([]);
  const [reportDate, setReportDate] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);

  const [filters, setFilters] = useState({
    fecha: new Date().toISOString().split('T')[0],
    conSaldo: true,
    propias: ''
  });

  const [groupings, setGroupings] = useState({
    clientes: false,
    carteras: false,
    socios: false,
    originador: false,
    vencimientos: false,
    dueno: false,
    recurso: false,
    iva: false
  });

  const handleGroupChange = (key) => {
    setGroupings(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const buildParams = () => {
    const params = new URLSearchParams();
    if (filters.fecha) params.append('fecha', filters.fecha);
    if (!filters.conSaldo) params.append('con_saldo', 'false');
    if (filters.propias !== '') params.append('propias', filters.propias);

    const activeGrpKeys = Object.keys(groupings).filter(k => groupings[k]);
    if (activeGrpKeys.length > 0) {
      params.append('agrupar', 'true');
      activeGrpKeys.forEach(k => {
        if (k === 'dueno') params.append('dueño', 'true');
        else params.append(k, 'true');
      });
    }
    return params;
  };

  const handleConsultar = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const params = buildParams();
      const res = await axiosClient.get(`/api/v1/reports/balances?${params}`);
      
      const newActiveGroups = [];
      if (groupings.clientes) newActiveGroups.push({ id: 'CUIL Cliente', label: 'Cliente' });
      if (groupings.carteras) newActiveGroups.push({ id: 'ID Cartera', label: 'Cartera' });
      if (groupings.socios) newActiveGroups.push({ id: 'Proveedor', label: 'Proveedor/Socio' });
      if (groupings.originador) newActiveGroups.push({ id: 'Originador', label: 'Originador' });
      if (groupings.vencimientos) newActiveGroups.push({ id: 'Fecha Vencimiento', label: 'Vencimiento' });
      if (groupings.dueno) newActiveGroups.push({ id: 'Dueño', label: 'Dueño' });
      if (groupings.recurso) newActiveGroups.push({ id: 'recurso', label: 'Recurso' });
      if (groupings.iva) newActiveGroups.push({ id: 'iva_operado', label: 'Tasa IVA' });

      setActiveGroups(newActiveGroups);
      setResults(res.data);
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
  
  let headers = [];
  if (isGrouping) {
    headers = activeGroups.map(g => g.label).concat(["Capital", "Interés", "IVA", "Total Saldo"]);
  } else {
    headers = ["ID Crédito", "Proveedor", "Originador", "Cliente CUIL", "Cartera", "Nro. Cuota", "Fecha Vencimiento", "Capital", "Interés", "IVA", "Total Saldo"];
  }

  const totals = React.useMemo(() => {
    return results.reduce((acc, curr) => ({
      capital: acc.capital + (curr.Capital || 0),
      interes: acc.interes + (curr['Interés'] || 0),
      iva: acc.iva + (curr.IVA || 0),
      total: acc.total + (curr.Total || curr.total || 0)
    }), { capital: 0, interes: 0, iva: 0, total: 0 });
  }, [results]);

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
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Agrupar por:</label>
            <div className="grouping-options" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: 'var(--radius-sm)' }}>
              {Object.keys(groupings).map(key => (
                <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input type="checkbox" checked={groupings[key]} onChange={() => handleGroupChange(key)} /> 
                  {key.charAt(0).toUpperCase() + key.slice(1).replace('Dueno', 'Dueño')}
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
          </div>
          <div className="table-responsive" style={{ maxHeight: '500px', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  {headers.map((h, i) => <th key={i}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {results.length === 0 ? (
                  <tr>
                    <td colSpan={headers.length} className="text-center empty-state">No se encontraron saldos.</td>
                  </tr>
                ) : (
                  results.map((row, i) => {
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
              {results.length > 0 && (
                <tfoot style={{ background: 'rgba(255, 255, 255, 0.05)', fontWeight: 'bold' }}>
                  <tr>
                    <td colSpan={headers.length - 4} style={{ textAlign: 'right' }}>TOTALES:</td>
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
