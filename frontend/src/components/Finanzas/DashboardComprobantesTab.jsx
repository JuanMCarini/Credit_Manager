import { useState, useMemo } from 'react';
import { FileText, AlertCircle, CheckCircle, TrendingUp, Calendar } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#64748b'];

const DashboardComprobantesTab = ({ comprobantes }) => {
  const getToday = () => new Date().toISOString().split('T')[0];
  const getFirstDayOfMonth = () => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().split('T')[0];
  };

  const [fechaDesde, setFechaDesde] = useState(getFirstDayOfMonth());
  const [fechaHasta, setFechaHasta] = useState(getToday());

  // Filtrar comprobantes por fecha de emisión
  const filteredComprobantes = useMemo(() => {
    return comprobantes.filter(c => {
      if (!c.fecha_emision) return true;
      const f = c.fecha_emision;
      if (fechaDesde && f < fechaDesde) return false;
      if (fechaHasta && f > fechaHasta) return false;
      return true;
    });
  }, [comprobantes, fechaDesde, fechaHasta]);

  // Calcular KPIs
  const { totalAdeudado, deudaVencida, totalPagado, nuevasObligaciones } = useMemo(() => {
    let adeudado = 0;
    let vencido = 0;
    let pagado = 0;
    let nuevas = 0;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    filteredComprobantes.forEach(c => {
      const impTotal = parseFloat(c.importe_total || 0);
      const impCancelado = parseFloat(c.importe_cancelado || 0);
      const saldo = Math.max(0, impTotal - impCancelado);
      
      nuevas += impTotal;
      pagado += impCancelado;

      if (c.estado !== 'pagado') {
        adeudado += saldo;
        
        if (c.fecha_vencimiento) {
          const venc = new Date(c.fecha_vencimiento + 'T00:00:00');
          if (venc < today) {
            vencido += saldo;
          }
        }
      }
    });

    return { totalAdeudado: adeudado, deudaVencida: vencido, totalPagado: pagado, nuevasObligaciones: nuevas };
  }, [filteredComprobantes]);

  // Gráfico: Deuda por Proveedor (Top 5 + Otros)
  const deudaPorProveedor = useMemo(() => {
    const map = {};
    filteredComprobantes.forEach(c => {
      if (c.estado !== 'pagado') {
        const saldo = Math.max(0, parseFloat(c.importe_total || 0) - parseFloat(c.importe_cancelado || 0));
        if (saldo > 0) {
          const provName = c.proveedor?.razon_social || 'Desconocido';
          map[provName] = (map[provName] || 0) + saldo;
        }
      }
    });

    const sorted = Object.entries(map).sort((a, b) => b[1] - a[1]);
    const top5 = sorted.slice(0, 5).map(item => ({ name: item[0], value: item[1] }));
    const otros = sorted.slice(5).reduce((acc, curr) => acc + curr[1], 0);
    
    if (otros > 0) {
      top5.push({ name: 'Otros', value: otros });
    }
    
    return top5;
  }, [filteredComprobantes]);

  // Gráfico: Gastos por Concepto
  const gastosPorConcepto = useMemo(() => {
    const map = {};
    filteredComprobantes.forEach(c => {
      const impTotal = parseFloat(c.importe_total || 0);
      if (impTotal > 0) {
        const concepto = c.concepto?.name || 'Sin Clasificar';
        map[concepto] = (map[concepto] || 0) + impTotal;
      }
    });

    const sorted = Object.entries(map)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);

    return sorted.slice(0, 7); // Top 7 conceptos
  }, [filteredComprobantes]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ backgroundColor: 'var(--surface-color)', padding: '10px', border: '1px solid var(--border-color)', borderRadius: '8px', boxShadow: 'var(--shadow-md)' }}>
          <p style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>{payload[0].name}</p>
          <p style={{ margin: 0, color: payload[0].color || 'var(--primary-color)' }}>
            {formatCurrency(payload[0].value)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Filtros */}
      <div className="card" style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div>
          <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Calendar size={16} /> Fecha Desde (Emisión)
          </label>
          <input 
            type="date" 
            className="form-control" 
            value={fechaDesde} 
            onChange={e => setFechaDesde(e.target.value)} 
          />
        </div>
        <div>
          <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Calendar size={16} /> Fecha Hasta (Emisión)
          </label>
          <input 
            type="date" 
            className="form-control" 
            value={fechaHasta} 
            onChange={e => setFechaHasta(e.target.value)} 
          />
        </div>
        <div style={{ flex: 1 }} />
      </div>

      {/* KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', marginBottom: '32px' }}>
        <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div className="stat-icon" style={{ background: 'rgba(14, 165, 233, 0.1)', color: 'var(--primary-color)', padding: '16px', borderRadius: '50%' }}>
            <FileText size={32} />
          </div>
          <div className="stat-content">
            <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Nuevas Obligaciones</p>
            <h3 className="stat-value" style={{ fontSize: '24px', fontWeight: 'bold', margin: 0, color: 'var(--primary-color)' }}>
              {formatCurrency(nuevasObligaciones)}
            </h3>
          </div>
        </div>

        <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div className="stat-icon" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger-color)', padding: '16px', borderRadius: '50%' }}>
            <AlertCircle size={32} />
          </div>
          <div className="stat-content">
            <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Total Adeudado</p>
            <h3 className="stat-value" style={{ fontSize: '24px', fontWeight: 'bold', margin: 0, color: 'var(--danger-color)' }}>
              {formatCurrency(totalAdeudado)}
            </h3>
            {deudaVencida > 0 && (
              <p style={{ fontSize: '12px', color: 'var(--danger-color)', margin: '4px 0 0 0', fontWeight: '500' }}>
                Incluye {formatCurrency(deudaVencida)} vencidos
              </p>
            )}
          </div>
        </div>

        <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px' }}>
          <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success-color)', padding: '16px', borderRadius: '50%' }}>
            <CheckCircle size={32} />
          </div>
          <div className="stat-content">
            <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Total Pagado</p>
            <h3 className="stat-value" style={{ fontSize: '24px', fontWeight: 'bold', margin: 0, color: 'var(--success-color)' }}>
              {formatCurrency(totalPagado)}
            </h3>
          </div>
        </div>
      </div>

      {/* Gráficos */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '24px' }}>
        
        {/* Gráfico 1: Deuda por Proveedor */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            Deuda Pendiente por Proveedor
          </h3>
          <div style={{ height: '300px', width: '100%' }}>
            {deudaPorProveedor.length > 0 ? (
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={deudaPorProveedor}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {deudaPorProveedor.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                No hay deuda pendiente en este periodo
              </div>
            )}
          </div>
        </div>

        {/* Gráfico 2: Gastos por Concepto */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            Nuevas Obligaciones por Concepto
          </h3>
          <div style={{ height: '300px', width: '100%' }}>
            {gastosPorConcepto.length > 0 ? (
              <ResponsiveContainer>
                <BarChart data={gastosPorConcepto} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="var(--border-color)" />
                  <XAxis type="number" tickFormatter={(val) => `$${(val/1000000).toLocaleString('es-AR', { maximumFractionDigits: 1 })}M`} style={{ fontSize: '12px', fill: 'var(--text-muted)' }} />
                  <YAxis dataKey="name" type="category" width={150} style={{ fontSize: '12px', fill: 'var(--text-muted)' }} />
                  <Tooltip content={<CustomTooltip />} cursor={{fill: 'rgba(255,255,255,0.05)'}} />
                  <Bar dataKey="value" fill="var(--primary-color)" radius={[0, 4, 4, 0]}>
                    {gastosPorConcepto.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                No hay comprobantes en este periodo
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default DashboardComprobantesTab;
