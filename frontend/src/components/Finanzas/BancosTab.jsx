import { useState, useEffect, useCallback, useMemo } from 'react';
import { DollarSign, Plus, Edit2, Trash2, Calendar, Landmark, Settings } from 'lucide-react';
import axiosClient from '../../api/axiosClient';
import CuentaModal from './CuentaModal';
import MovimientoModal from './MovimientoModal';

const BancosTab = () => {
  const [cuentas, setCuentas] = useState([]);
  const [selectedCuentaId, setSelectedCuentaId] = useState('');
  const [fechaCorte, setFechaCorte] = useState(new Date().toISOString().substring(0, 10));
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
        axiosClient.get(`/api/finanzas/cuentas/${selectedCuentaId}/kpis`, { params: { fecha_corte: fechaCorte } }),
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
  }, [selectedCuentaId, fechaCorte, filtroDesde, filtroHasta]);

  useEffect(() => {
    fetchCuentas();
  }, [fetchCuentas]);

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

        <div style={{ minWidth: '200px' }}>
          <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Calendar size={16} /> Fecha de Corte (KPIs)
          </label>
          <input 
            type="date" 
            className="form-control" 
            value={fechaCorte} 
            onChange={(e) => setFechaCorte(e.target.value)} 
          />
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
            <button className="btn btn-primary" onClick={() => { setEditingMovimiento(null); setIsMovimientoModalOpen(true); }} disabled={!selectedCuentaId} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={18} /> Nuevo Movimiento
            </button>
          </div>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '120px' }}>Fecha</th>
                <th>Concepto</th>
                <th>Descripción</th>
                <th style={{ textAlign: 'right' }}>Ingreso</th>
                <th style={{ textAlign: 'right' }}>Egreso</th>
                <th style={{ width: '100px', textAlign: 'center' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '30px' }}><span className="spinner"></span></td>
                </tr>
              ) : movimientos.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>No hay movimientos en esta cuenta para los filtros seleccionados.</td>
                </tr>
              ) : (
                movimientos.map((mov) => {
                  const cat = mov.concepto?.tipo_movimiento;
                  const isIngreso = cat === 'Ingresos' || cat === 'Rescate FCI' || cat === 'Plazo Fijo - Egresos';
                  return (
                    <tr key={mov.id}>
                      <td>{mov.fecha}</td>
                      <td>
                        <div style={{ fontWeight: '500' }}>{mov.concepto?.name}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{cat}</div>
                      </td>
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
