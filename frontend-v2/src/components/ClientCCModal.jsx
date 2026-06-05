import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const ClientCCModal = ({ cuil, clientName, onClose, initialFilterCredito = '' }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [filter, setFilter] = useState({ Credito: String(initialFilterCredito), Cuota: '', Vto: { start: '', end: '' }, Estado: [] });
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [showEstadoFilter, setShowEstadoFilter] = useState(false);

  const ESTADOS_DISPONIBLES = ['PENDIENTE', 'CANCELADA', 'MOROSA'];

  useEffect(() => {
    const fetchCC = async () => {
      try {
        const res = await axiosClient.get(`/api/v1/clientes/${cuil}/cuenta_corriente`);
        setData(res.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchCC();
  }, [cuil]);

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

  const filteredAndSortedData = React.useMemo(() => {
    let result = [...data];

    if (filter.Credito) result = result.filter(c => c.credito_id === parseInt(filter.Credito, 10));
    if (filter.Cuota) result = result.filter(c => c.nro_cuota === parseInt(filter.Cuota, 10));
    if (filter.Vto.start || filter.Vto.end) {
      result = result.filter(c => {
        if (!c.vencimiento) return false;
        const parts = c.vencimiento.split('/');
        if (parts.length !== 3) return false;
        const rowDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
        
        if (filter.Vto.start && rowDate < filter.Vto.start) return false;
        if (filter.Vto.end && rowDate > filter.Vto.end) return false;
        return true;
      });
    }
    if (filter.Estado.length > 0) result = result.filter(c => filter.Estado.includes(c.estado));

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
  }, [data, filter, sortConfig]);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '5px' }}>↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
      backdropFilter: 'blur(5px)'
    }}>
      <div className="glass-panel" style={{
        width: '100%', maxWidth: '1200px', maxHeight: '90vh', overflowY: 'auto',
        position: 'relative', padding: '24px'
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none',
          color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px'
        }}>✕</button>
        
        <h2 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)' }}>
          Cuenta Corriente Unificada: {clientName ? `${clientName} (CUIL: ${cuil})` : cuil}
        </h2>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>Cargando cuenta corriente...</div>
        ) : error ? (
          <div style={{ color: 'var(--error)', textAlign: 'center', padding: '40px' }}>{error}</div>
        ) : (
          <div className="table-responsive">
            <table className="data-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th onClick={() => handleSort('credito_id')} style={{ cursor: 'pointer' }}>
                    Crédito <SortIcon columnKey="credito_id" />
                    <input type="number" placeholder="Filtrar..." value={filter.Credito} onChange={e => setFilter({ ...filter, Credito: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                  </th>
                  <th onClick={() => handleSort('nro_cuota')} style={{ cursor: 'pointer' }}>
                    Cuota <SortIcon columnKey="nro_cuota" />
                    <input type="number" placeholder="Filtrar..." value={filter.Cuota} onChange={e => setFilter({ ...filter, Cuota: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                  </th>
                  <th onClick={() => handleSort('vencimiento')} style={{ cursor: 'pointer' }}>
                    Vto <SortIcon columnKey="vencimiento" />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                      <input type="date" value={filter.Vto.start} onChange={e => setFilter({ ...filter, Vto: { ...filter.Vto, start: e.target.value } })} style={{ width: '100%', padding: '4px', fontSize: '10px' }} title="Desde" />
                      <input type="date" value={filter.Vto.end} onChange={e => setFilter({ ...filter, Vto: { ...filter.Vto, end: e.target.value } })} style={{ width: '100%', padding: '4px', fontSize: '10px' }} title="Hasta" />
                    </div>
                  </th>
                  <th onClick={() => handleSort('capital')} style={{ cursor: 'pointer' }}>Capital <SortIcon columnKey="capital" /></th>
                  <th onClick={() => handleSort('interes')} style={{ cursor: 'pointer' }}>Interés <SortIcon columnKey="interes" /></th>
                  <th onClick={() => handleSort('iva')} style={{ cursor: 'pointer' }}>IVA <SortIcon columnKey="iva" /></th>
                  <th onClick={() => handleSort('total_esperado')} style={{ cursor: 'pointer' }}>Total Esp. <SortIcon columnKey="total_esperado" /></th>
                  <th onClick={() => handleSort('total_cobrado')} style={{ cursor: 'pointer' }}>Total Cob. <SortIcon columnKey="total_cobrado" /></th>
                  <th onClick={() => handleSort('saldo_pendiente')} style={{ cursor: 'pointer' }}>Saldo Pend. <SortIcon columnKey="saldo_pendiente" /></th>
                  <th onClick={() => handleSort('estado')} style={{ cursor: 'pointer', position: 'relative' }}>
                    Estado <SortIcon columnKey="estado" />
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
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedData.length === 0 ? (
                  <tr>
                    <td colSpan="10" style={{ textAlign: 'center', padding: '40px' }}>
                      No hay cuotas registradas para este cliente con los filtros actuales.
                    </td>
                  </tr>
                ) : (
                  filteredAndSortedData.map((c, i) => {
                    const extStr = c.id_externo && c.id_externo !== '-' ? ` (${c.id_externo})` : '';
                    const creditoLabel = `#${c.credito_id}${extStr}`;
                    
                    return (
                      <React.Fragment key={`${c.credito_id}-${c.nro_cuota}-${i}`}>
                        <tr>
                          <td>{creditoLabel}</td>
                          <td>{c.nro_cuota}</td>
                          <td>{c.vencimiento}</td>
                          <td>{formatCurrency(c.capital)}</td>
                          <td>{formatCurrency(c.interes)}</td>
                          <td>{formatCurrency(c.iva)}</td>
                          <td style={{ fontWeight: 600 }}>{formatCurrency(c.total_esperado)}</td>
                          <td style={{ color: 'var(--accent-secondary)', fontWeight: 600 }}>{formatCurrency(c.total_cobrado)}</td>
                          <td style={{
                            color: c.estado === 'MOROSA' ? 'var(--error)' : c.estado === 'PENDIENTE' ? 'var(--accent-secondary)' : 'inherit',
                            fontWeight: 500
                          }}>
                            {c.estado === 'CANCELADA' ? '-' : formatCurrency(c.saldo_pendiente)}
                          </td>
                          <td>
                            <span style={{
                              padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                              background: c.estado === 'CANCELADA' ? 'var(--accent-secondary)' : c.estado === 'MOROSA' ? 'var(--error)' : 'rgba(255,255,255,0.1)',
                              color: '#fff'
                            }}>
                              {c.estado}
                            </span>
                          </td>
                        </tr>
                        {c.detalle_cobranzas && c.detalle_cobranzas.map((cob, j) => (
                          <tr key={`cob-${j}`} style={{ background: 'rgba(255, 255, 255, 0.02)', fontSize: '12px', color: 'var(--text-secondary)' }}>
                            <td colSpan="3" style={{ textAlign: 'right', borderLeft: '2px solid var(--accent-secondary)' }}>
                              ↳ Cobranza ({cob.tipo}) el {cob.fecha}
                            </td>
                            <td>{formatCurrency(cob.capital)}</td>
                            <td>{formatCurrency(cob.interes)}</td>
                            <td>{formatCurrency(cob.iva)}</td>
                            <td>-</td>
                            <td style={{ color: 'var(--accent-secondary)' }}>{formatCurrency(cob.total)}</td>
                            <td colSpan="2"></td>
                          </tr>
                        ))}
                      </React.Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ClientCCModal;
