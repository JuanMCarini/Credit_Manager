import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const formatCurrency = (value) => {
  if (value === null || value === undefined) return "$ 0";
  return new Intl.NumberFormat('es-AR', { 
    style: 'currency', 
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const DashboardCarteraPage = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fechaCorte, setFechaCorte] = useState(new Date().toISOString().split('T')[0]);
  const [tasaDescuento, setTasaDescuento] = useState(0);
  const [tasaDescuentoStr, setTasaDescuentoStr] = useState("0 %");
  const [activeTab, setActiveTab] = useState('total'); // 'total' or 'periodo'

  const handleTasaChange = (e) => {
    const raw = e.target.value.replace(/[^0-9.,]/g, '').replace(',', '.');
    setTasaDescuentoStr(e.target.value); // Let user type freely
    setTasaDescuento(Number(raw) || 0);
  };

  const handleTasaBlur = () => {
    if (tasaDescuento !== null) {
      setTasaDescuentoStr(`${tasaDescuento} %`);
    }
  };

  const handleTasaFocus = () => {
    setTasaDescuentoStr(tasaDescuento === 0 ? '' : tasaDescuento.toString());
  };

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        // Obtener datos crudos para poder calcular el descuento exacto por vencimiento
        const response = await axiosClient.get('/api/v1/reports/balances', {
          params: {
            fecha: fechaCorte,
            con_saldo: true,
            agrupar: false
          }
        });
        setData(response.data);
      } catch (err) {
        console.error("Error cargando dashboard:", err);
        setError("Ocurrió un error al cargar la información del dashboard.");
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [fechaCorte]);

  // Calcular KPIs y agrupaciones
  let totalCapital = 0;
  let totalInteres = 0;
  let totalIva = 0;
  let totalGeneral = 0;
  let valorActual = 0;

  const grupos = {};
  const gruposPeriodo = {};
  const tna = tasaDescuento / 100;
  const fechaCorteDate = new Date(fechaCorte + 'T00:00:00'); // Force local midnight
  const corteYearMonth = fechaCorte.substring(0, 7);

  data.forEach(row => {
    const cap = row.Capital || 0;
    const int = row['Interés'] || 0;
    const iva = row.IVA || 0;
    const tot = row.Total || 0;

    totalCapital += cap;
    totalInteres += int;
    totalIva += iva;
    totalGeneral += tot;

    // Calcular Valor Actual
    const fVtoStr = row['Fecha Vencimiento'];
    const fVto = new Date(fVtoStr + 'T00:00:00');
    let diasVto = Math.floor((fVto - fechaCorteDate) / (1000 * 60 * 60 * 24));
    if (diasVto < 0) diasVto = 0;

    const flujoTotal = cap + int;
    const pv = flujoTotal / Math.pow(1 + (tna * 30 / 365), diasVto / 30);
    valorActual += pv;

    // Agrupar para la tabla
    const dueño = row.Dueño || 'Desconocido';
    const originador = row.Originador || 'N/A';
    const key = `${dueño}|${originador}`;

    if (!grupos[key]) {
      grupos[key] = { Dueño: dueño, Originador: originador, Capital: 0, 'Interés': 0, IVA: 0, Total: 0, ValorActual: 0 };
    }
    grupos[key].Capital += cap;
    grupos[key]['Interés'] += int;
    grupos[key].IVA += iva;
    grupos[key].Total += tot;
    grupos[key].ValorActual += pv;

    // Agrupar por periodo (vencimientos futuros y el actual)
    const vtoYearMonth = fVtoStr.substring(0, 7);
    if (vtoYearMonth >= corteYearMonth) {
      if (!gruposPeriodo[vtoYearMonth]) {
        gruposPeriodo[vtoYearMonth] = { Periodo: vtoYearMonth, Capital: 0, 'Interés': 0, IVA: 0, Total: 0 };
      }
      gruposPeriodo[vtoYearMonth].Capital += cap;
      gruposPeriodo[vtoYearMonth]['Interés'] += int;
      gruposPeriodo[vtoYearMonth].IVA += iva;
      gruposPeriodo[vtoYearMonth].Total += tot;
    }
  });

  const groupedData = Object.values(grupos);
  const periodData = Object.values(gruposPeriodo).sort((a, b) => a.Periodo.localeCompare(b.Periodo));

  if (loading) {
    return (
      <div className="page-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <div className="loading-spinner"></div>
        <span style={{ marginLeft: '10px' }}>Cargando información de la cartera...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="alert error">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="page-container" style={{ animation: 'fadeIn 0.5s ease' }}>
      <header className="page-header" style={{ marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '15px' }}>
        <div>
          <h1 className="page-title">Dashboard de Cartera</h1>
          <p className="page-subtitle">Información general y estado actual de los saldos activos</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label htmlFor="tasaDescuento" style={{ color: 'var(--text-secondary)', fontWeight: '500' }}>TNA Descuento:</label>
            <input 
              type="text" 
              id="tasaDescuento"
              value={tasaDescuentoStr}
              onChange={handleTasaChange}
              onBlur={handleTasaBlur}
              onFocus={handleTasaFocus}
              style={{ 
                padding: '8px 12px', 
                borderRadius: '8px', 
                border: '1px solid rgba(255,255,255,0.1)',
                background: 'rgba(0,0,0,0.2)',
                color: 'var(--text-primary)',
                width: '80px',
                textAlign: 'right'
              }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label htmlFor="fechaCorte" style={{ color: 'var(--text-secondary)', fontWeight: '500' }}>Fecha de Corte:</label>
            <input 
              type="date" 
              id="fechaCorte"
              value={fechaCorte}
              onChange={(e) => setFechaCorte(e.target.value)}
              style={{ 
                padding: '8px 12px', 
                borderRadius: '8px', 
                border: '1px solid rgba(255,255,255,0.1)',
                background: 'rgba(0,0,0,0.2)',
                color: 'var(--text-primary)',
                colorScheme: 'dark'
              }}
            />
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '20px' }}>
        <button 
          onClick={() => setActiveTab('total')}
          style={{ 
            padding: '10px 20px', 
            borderRadius: '8px', 
            border: 'none',
            background: activeTab === 'total' ? '#2196F3' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'total' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Cartera Total
        </button>
        <button 
          onClick={() => setActiveTab('periodo')}
          style={{ 
            padding: '10px 20px', 
            borderRadius: '8px', 
            border: 'none',
            background: activeTab === 'periodo' ? '#2196F3' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'periodo' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Detalle por Período
        </button>
      </div>

      {activeTab === 'total' ? (
        <>
          {/* KPI Cards */}
          <div style={{ 
            display: 'flex', 
            flexWrap: 'wrap',
            justifyContent: 'center', 
            gap: '20px', 
            marginBottom: '30px' 
          }}>
            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid #4CAF50', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Total Capital Activo</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalCapital)}</span>
            </div>
            
            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid #FF9800', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Total Interés</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalInteres)}</span>
            </div>

            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid #00BCD4', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Capital + Interés</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalCapital + totalInteres)}</span>
            </div>

            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid #9C27B0', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Total IVA</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalIva)}</span>
            </div>

            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid #2196F3', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Saldo Total a Favor</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalGeneral)}</span>
            </div>

            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid #E91E63', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default', background: 'linear-gradient(135deg, rgba(233, 30, 99, 0.1), rgba(0,0,0,0))' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Valor Actual ({tasaDescuento}%)</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(valorActual)}</span>
            </div>
          </div>

          {/* Breakdown Table */}
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Desglose por Dueño y Originador</h2>
            {groupedData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos disponibles en la cartera activa.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Dueño de Cartera</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Originador</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Capital</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Interés</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Cap + Int</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>IVA</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Total</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Valor Actual</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groupedData.map((row, idx) => (
                      <tr key={idx} style={{ 
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        transition: 'background-color 0.2s',
                      }} className="table-row-hover">
                        <td style={{ padding: '15px 10px', fontWeight: '500' }}>{row.Dueño}</td>
                        <td style={{ padding: '15px 10px', color: 'var(--text-secondary)' }}>{row.Originador}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.Capital)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row['Interés'])}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace', color: '#00BCD4' }}>{formatCurrency(row.Capital + row['Interés'])}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.IVA)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace' }}>{formatCurrency(row.Total)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: '#E91E63' }}>{formatCurrency(row.ValorActual)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : (
          <>
            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', marginBottom: '30px', height: '400px' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Proyección de Vencimientos</h2>
              {periodData.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay vencimientos futuros registrados.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={periodData}
                    margin={{ top: 10, right: 30, left: 20, bottom: 25 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis dataKey="Periodo" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} />
                    <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`} />
                    <Tooltip 
                      formatter={(value) => formatCurrency(value)}
                      contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'white' }}
                      itemStyle={{ color: 'white' }}
                    />
                    <Legend wrapperStyle={{ paddingTop: '20px' }} />
                    <Bar dataKey="Capital" stackId="a" fill="#4CAF50" name="Capital" />
                    <Bar dataKey="Interés" stackId="a" fill="#FF9800" name="Interés" />
                    <Bar dataKey="IVA" stackId="a" fill="#9C27B0" name="IVA" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Detalle por Período (Actual y Futuros)</h2>
              {periodData.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay vencimientos futuros registrados.</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Período</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Capital</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Interés</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Cap + Int</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>IVA</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {periodData.map((row, idx) => (
                      <tr key={idx} style={{ 
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        transition: 'background-color 0.2s',
                      }} className="table-row-hover">
                        <td style={{ padding: '15px 10px', fontWeight: '500' }}>{row.Periodo}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.Capital)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row['Interés'])}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace', color: '#00BCD4' }}>{formatCurrency(row.Capital + row['Interés'])}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.IVA)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: '#2196F3' }}>{formatCurrency(row.Total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
            </div>
          </>
        )}
      <style>{`
        .table-row-hover:hover {
          background-color: rgba(255,255,255,0.02);
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default DashboardCarteraPage;
