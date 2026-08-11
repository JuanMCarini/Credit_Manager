import { useState, useEffect, useCallback, useMemo } from 'react';
import { DollarSign, Landmark, ArrowUpRight, ArrowDownRight, Calendar } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import axiosClient from '../../api/axiosClient';

const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#64748b'];

const DashboardBancosTab = () => {
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  
  const [kpis, setKpis] = useState({
    saldo: 0,
    saldo_fci: 0,
    saldo_plazo_fijo: 0,
    ingresos_periodo: 0,
    egresos_periodo: 0,
    flujo_neto: 0
  });
  
  const [movimientos, setMovimientos] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      const [kpisRes, movsRes] = await Promise.all([
        axiosClient.get('/api/finanzas/kpis-globales', {
          params: {
            fecha_desde: fechaDesde || undefined,
            fecha_hasta: fechaHasta || undefined
          }
        }),
        axiosClient.get('/api/finanzas/movimientos', {
          params: {
            fecha_desde: fechaDesde || undefined,
            fecha_hasta: fechaHasta || undefined
          }
        })
      ]);
      
      setKpis(kpisRes.data);
      setMovimientos(movsRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [fechaDesde, fechaHasta]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  // Agrupar movimientos por clasificación
  const { ingresosData, egresosData } = useMemo(() => {
    const ingresosMap = {};
    const egresosMap = {};

    movimientos.forEach(mov => {
      const cat = mov.concepto?.tipo_movimiento;
      const isIngreso = cat === 'Ingreso' || cat === 'Rescate FCI' || cat === 'Egresos de plazo fijo';
      
      const clasificacion = mov.concepto?.clasificacion?.name || 'Sin Clasificar';
      
      if (isIngreso) {
        ingresosMap[clasificacion] = (ingresosMap[clasificacion] || 0) + Number(mov.monto);
      } else {
        egresosMap[clasificacion] = (egresosMap[clasificacion] || 0) + Number(mov.monto);
      }
    });

    const formatData = (map) => Object.keys(map).map(name => ({
      name,
      value: map[name]
    })).sort((a, b) => b.value - a.value);

    return {
      ingresosData: formatData(ingresosMap),
      egresosData: formatData(egresosMap)
    };
  }, [movimientos]);

  const renderCustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ backgroundColor: 'var(--surface-color, #1e1e1e)', border: '1px solid var(--border-color, #333)', padding: '10px', borderRadius: '4px', color: 'var(--text-color, #fff)' }}>
          <p style={{ margin: 0, fontWeight: 'bold' }}>{payload[0].payload.name}</p>
          <p style={{ margin: 0, color: payload[0].payload.fill }}>{formatCurrency(payload[0].value)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ animation: 'fadeIn 0.3s ease-in-out' }}>
      
      {/* Filtros */}
      <div className="card" style={{ marginBottom: '24px', display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div style={{ minWidth: '200px' }}>
          <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Calendar size={16} /> Fecha Desde
          </label>
          <input 
            type="date" 
            className="form-control" 
            value={fechaDesde} 
            onChange={(e) => setFechaDesde(e.target.value)} 
          />
        </div>
        <div style={{ minWidth: '200px' }}>
          <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Calendar size={16} /> Fecha Hasta
          </label>
          <input 
            type="date" 
            className="form-control" 
            value={fechaHasta} 
            onChange={(e) => setFechaHasta(e.target.value)} 
          />
        </div>
        <div>
          <button className="btn btn-outline" onClick={() => { setFechaDesde(''); setFechaHasta(''); }}>
            Limpiar Filtros
          </button>
        </div>
      </div>

      {loading && <div style={{ textAlign: 'center', padding: '20px' }}><span className="spinner"></span> Cargando...</div>}

      {!loading && (
        <>
          {/* KPIs Principales (Saldos Históricos / Acumulados a la fecha de corte) */}
          <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: 'bold' }}>Estado de Cuentas (Acumulado)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', marginBottom: '32px' }}>
            <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div className="stat-icon" style={{ background: 'rgba(var(--primary-rgb), 0.1)', color: 'var(--primary-color)', padding: '16px', borderRadius: '50%' }}>
                <Landmark size={32} />
              </div>
              <div className="stat-content">
                <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Saldo Total en Bancos</p>
                <h3 className="stat-value" style={{ fontSize: '28px', fontWeight: 'bold', margin: 0, color: kpis.saldo < 0 ? 'var(--danger-color)' : 'inherit' }}>
                  {formatCurrency(kpis.saldo)}
                </h3>
              </div>
            </div>

            <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div className="stat-icon" style={{ background: 'rgba(var(--secondary-rgb), 0.1)', color: 'var(--secondary-color)', padding: '16px', borderRadius: '50%' }}>
                <DollarSign size={32} />
              </div>
              <div className="stat-content">
                <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Inversiones FCI</p>
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
                <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Inversiones Plazo Fijo</p>
                <h3 className="stat-value" style={{ fontSize: '28px', fontWeight: 'bold', margin: 0 }}>
                  {formatCurrency(kpis.saldo_plazo_fijo)}
                </h3>
              </div>
            </div>
          </div>

          {/* KPIs del Período */}
          <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: 'bold' }}>Flujo de Caja (Período Seleccionado)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', marginBottom: '32px' }}>
            <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success-color)', padding: '16px', borderRadius: '50%' }}>
                <ArrowUpRight size={32} />
              </div>
              <div className="stat-content">
                <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Total Ingresos</p>
                <h3 className="stat-value" style={{ fontSize: '24px', fontWeight: 'bold', margin: 0, color: 'var(--success-color)' }}>
                  {formatCurrency(kpis.ingresos_periodo)}
                </h3>
              </div>
            </div>

            <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div className="stat-icon" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger-color)', padding: '16px', borderRadius: '50%' }}>
                <ArrowDownRight size={32} />
              </div>
              <div className="stat-content">
                <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Total Egresos</p>
                <h3 className="stat-value" style={{ fontSize: '24px', fontWeight: 'bold', margin: 0, color: 'var(--danger-color)' }}>
                  {formatCurrency(kpis.egresos_periodo)}
                </h3>
              </div>
            </div>

            <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div className="stat-icon" style={{ background: 'rgba(14, 165, 233, 0.1)', color: '#0ea5e9', padding: '16px', borderRadius: '50%' }}>
                <DollarSign size={32} />
              </div>
              <div className="stat-content">
                <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Flujo Neto</p>
                <h3 className="stat-value" style={{ fontSize: '24px', fontWeight: 'bold', margin: 0, color: kpis.flujo_neto >= 0 ? 'var(--success-color)' : 'var(--danger-color)' }}>
                  {formatCurrency(kpis.flujo_neto)}
                </h3>
              </div>
            </div>
          </div>

          {/* Gráficos */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '24px', marginBottom: '32px' }}>
            <div className="card">
              <h4 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: 'bold', textAlign: 'center' }}>Distribución de Ingresos</h4>
              {ingresosData.length > 0 ? (
                <div style={{ height: '300px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={ingresosData} layout="vertical" margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="var(--border-color)" />
                      <XAxis type="number" tickFormatter={(val) => `$${(val/1000).toFixed(0)}k`} style={{ fontSize: '12px' }} />
                      <YAxis type="category" dataKey="name" width={140} style={{ fontSize: '12px' }} />
                      <Tooltip content={renderCustomTooltip} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {ingresosData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                  No hay ingresos en el período seleccionado.
                </div>
              )}
            </div>

            <div className="card">
              <h4 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: 'bold', textAlign: 'center' }}>Distribución de Egresos</h4>
              {egresosData.length > 0 ? (
                <div style={{ height: '300px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={egresosData} layout="vertical" margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="var(--border-color)" />
                      <XAxis type="number" tickFormatter={(val) => `$${(val/1000).toFixed(0)}k`} style={{ fontSize: '12px' }} />
                      <YAxis type="category" dataKey="name" width={140} style={{ fontSize: '12px' }} />
                      <Tooltip content={renderCustomTooltip} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {egresosData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[(index + 3) % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                  No hay egresos en el período seleccionado.
                </div>
              )}
            </div>
          </div>
          
        </>
      )}
    </div>
  );
};

export default DashboardBancosTab;
