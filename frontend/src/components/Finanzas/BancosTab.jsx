import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { DollarSign, Plus, Edit2, Trash2, Calendar, Landmark, Settings, Upload } from 'lucide-react';
import axiosClient from '../../api/axiosClient';
import CuentaModal from './CuentaModal';
import MovimientoModal from './MovimientoModal';
import ExcelDateFilter from '../ExcelDateFilter';
import ExcelListFilter from '../ExcelListFilter';

const FilterInput = ({ col, columnFilters, setColumnFilters }) => (
  <div onClick={e => e.stopPropagation()}>
    <input 
      type="text" 
      placeholder="Filtrar..." 
      value={columnFilters[col] || ''} 
      onChange={(e) => setColumnFilters(prev => ({ ...prev, [col]: e.target.value }))}
      style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', boxSizing: 'border-box', fontWeight: 'normal' }}
    />
  </div>
);

const BancosTab = () => {
  const [cuentas, setCuentas] = useState([]);
  const [selectedCuentaId, setSelectedCuentaId] = useState('');
  const [kpis, setKpis] = useState({ saldo: 0, saldo_fci: 0, saldo_plazo_fijo: 0 });
  const [movimientos, setMovimientos] = useState([]);
  const [loading, setLoading] = useState(false);

  // Modals state
  const [isCuentaModalOpen, setIsCuentaModalOpen] = useState(false);
  const [editingCuenta, setEditingCuenta] = useState(null);

  const [isMovimientoModalOpen, setIsMovimientoModalOpen] = useState(false);
  const [editingMovimiento, setEditingMovimiento] = useState(null);

  // Filters for Movimientos
  const [filtroDesde, setFiltroDesde] = useState('');
  const [filtroHasta, setFiltroHasta] = useState('');
  const [columnFilters, setColumnFilters] = useState({});

  // Bulk Edit State
  const [selectedMovimientoIds, setSelectedMovimientoIds] = useState([]);
  const [conceptosOptions, setConceptosOptions] = useState([]);
  const [bulkConceptoId, setBulkConceptoId] = useState('');
  const [bulkUpdating, setBulkUpdating] = useState(false);

  const fetchCuentas = useCallback(async () => {
    try {
      const res = await axiosClient.get('/api/finanzas/cuentas');
      setCuentas(res.data);
      if (res.data.length > 0 && !selectedCuentaId) {
        setSelectedCuentaId(res.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  }, [selectedCuentaId]);

  const fetchDashboardData = useCallback(async () => {
    if (!selectedCuentaId) return;
    setLoading(true);
    try {
      const [kpiRes, movsRes] = await Promise.all([
        axiosClient.get(`/api/finanzas/cuentas/${selectedCuentaId}/kpis`, { params: { fecha_desde: filtroDesde || undefined, fecha_hasta: filtroHasta || undefined } }),
        axiosClient.get('/api/finanzas/movimientos', { 
          params: { 
            cuenta_id: selectedCuentaId,
            fecha_desde: filtroDesde || undefined,
            fecha_hasta: filtroHasta || undefined
          } 
        })
      ]);
      setKpis(kpiRes.data);
      setMovimientos(movsRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedCuentaId, filtroDesde, filtroHasta]);

  useEffect(() => {
    fetchCuentas();
  }, [fetchCuentas]);

  const fetchConceptos = useCallback(async () => {
    try {
      const res = await axiosClient.get('/api/finanzas/conceptos');
      setConceptosOptions(res.data);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchConceptos();
  }, [fetchConceptos]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleEditCuenta = () => {
    const cuenta = cuentas.find(c => c.id == selectedCuentaId);
    if (cuenta) {
      setEditingCuenta(cuenta);
      setIsCuentaModalOpen(true);
    }
  };

  const handleEditMovimiento = (mov) => {
    setEditingMovimiento(mov);
    setIsMovimientoModalOpen(true);
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedMovimientoIds(filteredMovimientos.map(m => m.id));
    } else {
      setSelectedMovimientoIds([]);
    }
  };

  const handleSelectMovimiento = (id) => {
    setSelectedMovimientoIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleBulkUpdate = async () => {
    if (!bulkConceptoId || selectedMovimientoIds.length === 0) return;
    setBulkUpdating(true);
    try {
      await axiosClient.put('/api/finanzas/movimientos/bulk-concepto', {
        movimiento_ids: selectedMovimientoIds,
        concepto_id: parseInt(bulkConceptoId)
      });
      setSelectedMovimientoIds([]);
      setBulkConceptoId('');
      fetchDashboardData();
    } catch (err) {
      console.error(err);
      alert('Error al actualizar los movimientos.');
    } finally {
      setBulkUpdating(false);
    }
  };

  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !selectedCuentaId) return;

    const formData = new FormData();
    formData.append('file', file);

    setIsUploading(true);
    try {
      const res = await axiosClient.post(`/api/finanzas/cuentas/${selectedCuentaId}/importar-extracto`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      alert(res.data.message + ". Filas procesadas: " + res.data.filas_procesadas);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
      alert('Error al subir el archivo: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsUploading(false);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteMovimiento = async (id) => {
    if (!window.confirm("¿Está seguro de que desea eliminar este movimiento?")) return;
    try {
      await axiosClient.delete(`/api/finanzas/movimientos/${id}`);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
      alert('Error al eliminar el movimiento');
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  const uniqueDates = useMemo(() => {
    return [...new Set(movimientos.map(m => m.fecha))].filter(Boolean).sort();
  }, [movimientos]);

  const uniqueConceptos = useMemo(() => {
    const list = movimientos.map(m => m.concepto?.name).filter(Boolean);
    return [...new Set(list)].sort();
  }, [movimientos]);

  const uniqueClasificaciones = useMemo(() => {
    const list = movimientos.map(m => m.concepto?.clasificacion?.name).filter(Boolean);
    return [...new Set(list)].sort();
  }, [movimientos]);

  const filteredMovimientos = useMemo(() => {
    return movimientos.filter(mov => {
      const cat = mov.concepto?.tipo_movimiento || '';
      const isIngreso = cat === 'Ingreso' || cat === 'Rescate FCI' || cat === 'Egresos de plazo fijo';
      let match = true;

      if (columnFilters['fecha']?.length > 0 && !columnFilters['fecha'].includes(mov.fecha)) return false;
      
      if (columnFilters.concepto && columnFilters.concepto.length > 0) {
        if (!columnFilters.concepto.includes(mov.concepto?.name)) {
          match = false;
        }
      }
      if (columnFilters.clasificacion && columnFilters.clasificacion.length > 0) {
        if (!columnFilters.clasificacion.includes(mov.concepto?.clasificacion?.name)) {
          match = false;
        }
      }
      
      if (columnFilters['nro_comprobante'] && !(mov.nro_comprobante || '-').toLowerCase().includes(columnFilters['nro_comprobante'].toLowerCase())) return false;
      
      if (columnFilters['descripcion'] && !(mov.descripcion || '-').toLowerCase().includes(columnFilters['descripcion'].toLowerCase())) return false;
      
      if (columnFilters['ingreso']) {
         if (!isIngreso) return false;
         if (!formatCurrency(mov.monto).toLowerCase().includes(columnFilters['ingreso'].toLowerCase())) return false;
      }
      
      if (columnFilters['egreso']) {
         if (isIngreso) return false;
         if (!formatCurrency(mov.monto).toLowerCase().includes(columnFilters['egreso'].toLowerCase())) return false;
      }
      
      return match;
    });
  }, [movimientos, columnFilters]);

  const subtotals = useMemo(() => {
    let ingresos = 0;
    let egresos = 0;
    filteredMovimientos.forEach(mov => {
      const cat = mov.concepto?.tipo_movimiento;
      const isIngreso = cat === 'Ingreso' || cat === 'Rescate FCI' || cat === 'Egresos de plazo fijo';
      if (isIngreso) {
        ingresos += Number(mov.monto) || 0;
      } else {
        egresos += Number(mov.monto) || 0;
      }
    });
    return { ingresos, egresos };
  }, [filteredMovimientos]);

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      
      {/* Controls Header */}
      <div className="card" style={{ marginBottom: '24px', display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div style={{ flex: '1', minWidth: '250px' }}>
          <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Landmark size={16} /> Cuenta Bancaria
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <select 
              className="form-control" 
              value={selectedCuentaId} 
              onChange={(e) => setSelectedCuentaId(e.target.value)}
              style={{ flex: 1 }}
            >
              <option value="">Seleccione una cuenta...</option>
              {cuentas.map(c => (
                <option key={c.id} value={c.id}>{c.banco?.nombre_banco} - {c.nombre} ({c.tipo_cuenta})</option>
              ))}
            </select>
            <button className="btn btn-outline" onClick={() => { setEditingCuenta(null); setIsCuentaModalOpen(true); }} title="Nueva Cuenta">
              <Plus size={18} />
            </button>
            <button className="btn btn-outline" onClick={handleEditCuenta} disabled={!selectedCuentaId} title="Editar Cuenta">
              <Settings size={18} />
            </button>
          </div>
        </div>

      </div>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px', marginBottom: '32px' }}>
        
        <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div className="stat-icon" style={{ background: 'rgba(var(--primary-rgb), 0.1)', color: 'var(--primary-color)', padding: '16px', borderRadius: '50%' }}>
            <DollarSign size={32} />
          </div>
          <div className="stat-content">
            <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Saldo Disponible (Cuenta)</p>
            <h3 className="stat-value" style={{ fontSize: '28px', fontWeight: 'bold', margin: 0, color: kpis.saldo < 0 ? 'var(--danger-color)' : 'inherit' }}>
              {formatCurrency(kpis.saldo)}
            </h3>
          </div>
        </div>

        <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div className="stat-icon" style={{ background: 'rgba(var(--secondary-rgb), 0.1)', color: 'var(--secondary-color)', padding: '16px', borderRadius: '50%' }}>
            <Landmark size={32} />
          </div>
          <div className="stat-content">
            <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Inversiones (FCI)</p>
            <h3 className="stat-value" style={{ fontSize: '28px', fontWeight: 'bold', margin: 0 }}>
              {formatCurrency(kpis.saldo_fci)}
            </h3>
          </div>
        </div>

        <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div className="stat-icon" style={{ background: 'rgba(var(--warning-rgb), 0.1)', color: '#d97706', padding: '16px', borderRadius: '50%' }}>
            <DollarSign size={32} />
          </div>
          <div className="stat-content">
            <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Inversiones (Plazo Fijo)</p>
            <h3 className="stat-value" style={{ fontSize: '28px', fontWeight: 'bold', margin: 0 }}>
              {formatCurrency(kpis.saldo_plazo_fijo)}
            </h3>
          </div>
        </div>

      </div>

      {/* Movements Table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '20px', fontWeight: 'bold' }}>Movimientos</h3>
          
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <input 
              type="date" 
              className="form-control" 
              placeholder="Desde" 
              value={filtroDesde} 
              onChange={(e) => setFiltroDesde(e.target.value)} 
            />
            <span>-</span>
            <input 
              type="date" 
              className="form-control" 
              placeholder="Hasta" 
              value={filtroHasta} 
              onChange={(e) => setFiltroHasta(e.target.value)} 
            />
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept=".xls,.xlsx" 
              onChange={handleFileUpload} 
            />
            <button 
              className="btn btn-secondary" 
              onClick={() => fileInputRef.current && fileInputRef.current.click()} 
              disabled={!selectedCuentaId || isUploading} 
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <Upload size={18} /> {isUploading ? 'Importando...' : 'Importar'}
            </button>
            <button className="btn btn-primary" onClick={() => { setEditingMovimiento(null); setIsMovimientoModalOpen(true); }} disabled={!selectedCuentaId} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={18} /> Nuevo Movimiento
            </button>
          </div>
        </div>

        {selectedMovimientoIds.length > 0 && (
          <div style={{ background: 'var(--surface-color)', border: '1px solid var(--border-color)', padding: '12px 16px', borderRadius: 'var(--radius)', display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', boxShadow: 'var(--shadow-sm)' }}>
            <span style={{ fontWeight: '500', color: 'var(--text-color)' }}>{selectedMovimientoIds.length} movimientos seleccionados</span>
            <select 
              className="form-control" 
              value={bulkConceptoId}
              onChange={e => setBulkConceptoId(e.target.value)}
              style={{ flex: 1, minWidth: '200px', maxWidth: '400px' }}
            >
              <option value="">Seleccione concepto a asignar...</option>
              {conceptosOptions.map(c => (
                <option key={c.id} value={c.id}>{c.name} ({c.tipo_movimiento})</option>
              ))}
            </select>
            <button 
              className="btn btn-primary" 
              style={{ padding: '6px 12px', fontSize: '13px', width: 'auto' }}
              onClick={handleBulkUpdate}
              disabled={!bulkConceptoId || bulkUpdating}
            >
              {bulkUpdating ? 'Actualizando...' : 'Aplicar Concepto'}
            </button>
            <button 
              className="btn btn-outline" 
              style={{ padding: '6px 12px', fontSize: '13px', width: 'auto' }}
              onClick={() => setSelectedMovimientoIds([])} 
            >
              Cancelar
            </button>
          </div>
        )}

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '40px', textAlign: 'center', verticalAlign: 'top' }}>
                  <div>
                    <input 
                      type="checkbox"
                      checked={filteredMovimientos.length > 0 && selectedMovimientoIds.length === filteredMovimientos.length}
                      onChange={handleSelectAll}
                    />
                  </div>
                </th>
                <th style={{ width: '120px', verticalAlign: 'top' }}>
                  <div>Fecha</div>
                  <ExcelDateFilter 
                    availableDates={uniqueDates}
                    selectedDates={columnFilters['fecha'] || []}
                    onChange={(opts) => setColumnFilters(prev => ({ ...prev, fecha: opts }))}
                  />
                </th>
                <th style={{ verticalAlign: 'top' }}>
                  <div>Concepto</div>
                  <ExcelListFilter 
                    availableOptions={uniqueConceptos}
                    selectedOptions={columnFilters['concepto'] || []}
                    onChange={(opts) => setColumnFilters(prev => ({ ...prev, concepto: opts }))}
                    title="Buscar Concepto..."
                  />
                </th>
                <th style={{ verticalAlign: 'top' }}>
                  <div>Clasificación</div>
                  <ExcelListFilter 
                    availableOptions={uniqueClasificaciones}
                    selectedOptions={columnFilters['clasificacion'] || []}
                    onChange={(opts) => setColumnFilters(prev => ({ ...prev, clasificacion: opts }))}
                    title="Buscar Clasificación..."
                  />
                </th>
                <th style={{ verticalAlign: 'top' }}>
                  <div>Nro. Comp</div>
                  <FilterInput col="nro_comprobante" columnFilters={columnFilters} setColumnFilters={setColumnFilters} />
                </th>
                <th style={{ verticalAlign: 'top' }}>
                  <div>Descripción</div>
                  <FilterInput col="descripcion" columnFilters={columnFilters} setColumnFilters={setColumnFilters} />
                </th>
                <th style={{ textAlign: 'right', verticalAlign: 'top' }}>
                  <div>Ingreso</div>
                  <FilterInput col="ingreso" columnFilters={columnFilters} setColumnFilters={setColumnFilters} />
                </th>
                <th style={{ textAlign: 'right', verticalAlign: 'top' }}>
                  <div>Egreso</div>
                  <FilterInput col="egreso" columnFilters={columnFilters} setColumnFilters={setColumnFilters} />
                </th>
                <th style={{ width: '100px', textAlign: 'center', verticalAlign: 'top' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '30px' }}><span className="spinner"></span></td>
                </tr>
              ) : filteredMovimientos.length === 0 ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>No hay movimientos en esta cuenta para los filtros seleccionados.</td>
                </tr>
              ) : (
                filteredMovimientos.map((mov) => {
                  const cat = mov.concepto?.tipo_movimiento;
                  const isIngreso = cat === 'Ingreso' || cat === 'Rescate FCI' || cat === 'Egresos de plazo fijo';
                  const isUnclassified = !mov.concepto || mov.concepto.name.includes('NO CLASIFICADO');
                  
                  let rowStyle = {};
                  if (selectedMovimientoIds.includes(mov.id)) {
                    rowStyle = { backgroundColor: 'rgba(var(--primary-rgb), 0.05)' };
                  } else if (isUnclassified) {
                    rowStyle = { backgroundColor: 'rgba(245, 158, 11, 0.05)' }; // Subtle warning background
                  }

                  return (
                    <tr key={mov.id} style={rowStyle}>
                      <td style={{ textAlign: 'center' }}>
                        <input 
                          type="checkbox"
                          checked={selectedMovimientoIds.includes(mov.id)}
                          onChange={() => handleSelectMovimiento(mov.id)}
                        />
                      </td>
                      <td>{mov.fecha}</td>
                      <td>
                        <div style={{ fontWeight: '500', color: isUnclassified ? 'var(--warning)' : 'inherit' }}>
                          {mov.concepto?.name || 'Sin Clasificar'}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{cat || '-'}</div>
                      </td>
                      <td>{mov.concepto?.clasificacion?.name || '-'}</td>
                      <td>{mov.nro_comprobante || '-'}</td>
                      <td>{mov.descripcion || '-'}</td>
                      <td style={{ textAlign: 'right', color: isIngreso ? 'var(--success-color)' : 'inherit', fontWeight: isIngreso ? 'bold' : 'normal' }}>
                        {isIngreso ? formatCurrency(mov.monto) : '-'}
                      </td>
                      <td style={{ textAlign: 'right', color: !isIngreso ? 'var(--danger-color)' : 'inherit', fontWeight: !isIngreso ? 'bold' : 'normal' }}>
                        {!isIngreso ? formatCurrency(mov.monto) : '-'}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                          <button className="btn-icon" onClick={() => handleEditMovimiento(mov)} title="Editar" style={{ color: 'var(--primary-color)', background: 'none', border: 'none', cursor: 'pointer' }}>
                            <Edit2 size={16} />
                          </button>
                          <button className="btn-icon" onClick={() => handleDeleteMovimiento(mov.id)} title="Eliminar" style={{ color: 'var(--danger-color)', background: 'none', border: 'none', cursor: 'pointer' }}>
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {filteredMovimientos.length > 0 && (
              <tfoot style={{ backgroundColor: 'var(--surface-color)', borderTop: '2px solid var(--border-color)' }}>
                <tr>
                  <td colSpan="6" style={{ textAlign: 'right', padding: '16px', fontWeight: 'bold' }}>Subtotales filtrados:</td>
                  <td style={{ textAlign: 'right', color: 'var(--success-color)', padding: '16px', fontWeight: 'bold' }}>
                    {formatCurrency(subtotals.ingresos)}
                  </td>
                  <td style={{ textAlign: 'right', color: 'var(--danger-color)', padding: '16px', fontWeight: 'bold' }}>
                    {formatCurrency(subtotals.egresos)}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      <CuentaModal 
        isOpen={isCuentaModalOpen} 
        onClose={() => setIsCuentaModalOpen(false)} 
        onSaved={fetchCuentas}
        cuenta={editingCuenta}
      />

      <MovimientoModal
        isOpen={isMovimientoModalOpen}
        onClose={() => setIsMovimientoModalOpen(false)}
        onSaved={fetchDashboardData}
        movimiento={editingMovimiento}
        cuentaIdDefault={selectedCuentaId}
      />

    </div>
  );
};

export default BancosTab;
