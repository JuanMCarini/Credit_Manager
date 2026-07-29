import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
const formatCurrency = (value) => {
  if (value === null || value === undefined) return "$ 0";
  return new Intl.NumberFormat('es-AR', { 
    style: 'currency', 
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const RADIAN = Math.PI / 180;
const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }) => {
  const radius = outerRadius + 20;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  if (percent < 0.0001) return null; // Ocultar si el porcentaje es 0% para que no se superpongan todas las etiquetas nulas

  return (
    <text 
      x={x} 
      y={y} 
      fill="var(--text-primary)" 
      textAnchor={x > cx ? 'start' : 'end'} 
      dominantBaseline="central" 
      fontSize={16} 
      fontWeight="bold"
    >
      {`${(percent * 100).toFixed(2)}%`}
    </text>
  );
};

const DashboardCarteraPage = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fechaCorte, setFechaCorte] = useState(new Date().toISOString().split('T')[0]);
  const [tasaDescuento, setTasaDescuento] = useState(0);
  const [tasaDescuentoStr, setTasaDescuentoStr] = useState("0 %");
  const [activeTab, setActiveTab] = useState('total'); // 'total' or 'periodo'
  const [filtroDueños, setFiltroDueños] = useState([]); // empty means 'Todos'
  const [filtroOriginadores, setFiltroOriginadores] = useState([]); // empty means 'Todos'
  const [openDueño, setOpenDueño] = useState(false);
  const [openOriginador, setOpenOriginador] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const exportToPDF = async () => {
    setIsExporting(true);
    
    const root = document.documentElement;
    root.style.setProperty('--bg-base', '#ffffff');
    root.style.setProperty('--bg-panel', '#ffffff');
    root.style.setProperty('--text-primary', '#000000');
    root.style.setProperty('--text-secondary', '#333333');
    root.style.setProperty('--border-color', '#dddddd');
    
    root.style.setProperty('--color-capital', '#2E7D32');
    root.style.setProperty('--color-interes', '#F57C00');
    root.style.setProperty('--color-capint', '#0097A7');
    root.style.setProperty('--color-iva', '#7B1FA2');
    root.style.setProperty('--color-total', '#1976D2');
    root.style.setProperty('--color-valoractual', '#C2185B');
    
    setTimeout(async () => {
      try {
        const pdf = new jsPDF('p', 'mm', 'a4');
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = pdf.internal.pageSize.getHeight();
        
        const tabsToExport = [
          { id: 'export-tab-total', title: 'Cartera Total' },
          { id: 'export-tab-periodo', title: 'Detalle por Período' },
          { id: 'export-tab-estados', title: 'Detalle de Estados' },
          { id: 'export-tab-morosidad', title: 'Análisis de Morosidad' }
        ];

        let pageCount = 0;
        for (let i = 0; i < tabsToExport.length; i++) {
          const el = document.getElementById(tabsToExport[i].id);
          if (el) {
            const originalWidth = el.style.width;
            el.style.width = '1100px';
            el.style.maxWidth = '1100px';
            
            await new Promise(resolve => setTimeout(resolve, 150)); // let recharts adjust

            const canvas = await html2canvas(el, { 
              scale: 2, 
              backgroundColor: '#ffffff',
              windowWidth: 1150
            });
            
            el.style.width = originalWidth;
            el.style.maxWidth = '';

            const imgData = canvas.toDataURL('image/png');
            
            const imgProps = pdf.getImageProperties(imgData);
            const ratio = imgProps.width / imgProps.height;
            const margin = 10;
            let width = pdfWidth - margin * 2;
            let height = width / ratio;
            
            const maxPageHeight = pdfHeight - margin * 2 - 20;
            if (height > maxPageHeight) {
              height = maxPageHeight;
              width = height * ratio;
            }
            
            if (pageCount > 0) {
              pdf.addPage();
            }
            
            pdf.setFillColor(255, 255, 255);
            pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');
            
            pdf.setFontSize(16);
            pdf.setTextColor(0, 0, 0);
            pdf.text(`Dashboard - ${tabsToExport[i].title}`, margin, 15);
            
            pdf.setFontSize(9);
            pdf.setTextColor(100, 100, 100);
            const dueñosText = filtroDueños.length > 0 ? filtroDueños.join(', ') : 'Todos';
            const origText = filtroOriginadores.length > 0 ? filtroOriginadores.join(', ') : 'Todos';
            const filtrosStr = `Fecha de Corte: ${fechaCorte.split('-').reverse().join('/')} | TNA: ${tasaDescuento}% | Dueños: ${dueñosText} | Originadores: ${origText}`;
            pdf.text(filtrosStr, margin, 22);
            
            pdf.addImage(imgData, 'PNG', margin, 28, width, height);
            pageCount++;
          }
        }
        
        pdf.save('Dashboard_Cartera.pdf');
      } catch (err) {
        console.error("Error exporting to PDF:", err);
      } finally {
        setIsExporting(false);
        root.style.removeProperty('--bg-base');
        root.style.removeProperty('--bg-panel');
        root.style.removeProperty('--text-primary');
        root.style.removeProperty('--text-secondary');
        root.style.removeProperty('--border-color');
        root.style.removeProperty('--color-capital');
        root.style.removeProperty('--color-interes');
        root.style.removeProperty('--color-capint');
        root.style.removeProperty('--color-iva');
        root.style.removeProperty('--color-total');
        root.style.removeProperty('--color-valoractual');
      }
    }, 1500);
  };

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
            con_saldo: false,
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

  const resumenEstados = {
    'APROBADO': { Estado: 'Aprobado', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-capital)' },
    'ACTIVO': { Estado: 'Activo', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-total)' },
    'MOROSO': { Estado: 'Moroso', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-interes)' },
    'INCOBRABLE': { Estado: 'Incobrable', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-valoractual)' },
    'JUDICIALIZADO': { Estado: 'Judicializado', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-iva)' },
    'OTRO': { Estado: 'Otro', Vencido: 0, AVencer: 0, Total: 0, fill: '#607D8B' }
  };

  const moraBuckets = [
    { label: '1 - 30 días', min: 1, max: 30, Capital: 0, Interés: 0, IVA: 0, Total: 0 },
    { label: '31 - 60 días', min: 31, max: 60, Capital: 0, Interés: 0, IVA: 0, Total: 0 },
    { label: '61 - 90 días', min: 61, max: 90, Capital: 0, Interés: 0, IVA: 0, Total: 0 },
    { label: '91 - 180 días', min: 91, max: 180, Capital: 0, Interés: 0, IVA: 0, Total: 0 },
    { label: '181 - 365 días', min: 181, max: 365, Capital: 0, Interés: 0, IVA: 0, Total: 0 },
    { label: '> 365 días', min: 366, max: Infinity, Capital: 0, Interés: 0, IVA: 0, Total: 0 },
  ];

  data.forEach(row => {
    const dueño = row.Dueño || 'Desconocido';
    const originador = row.Originador || 'N/A';
    
    const matchDueño = filtroDueños.length === 0 || filtroDueños.includes(dueño);
    const matchOriginador = filtroOriginadores.length === 0 || filtroOriginadores.includes(originador);
    
    if (!matchDueño || !matchOriginador) return;

    const cap = row.Capital || 0;
    const int = row['Interés'] || 0;
    const iva = row.IVA || 0;
    const tot = row.Total || 0;
    
    const capCobrado = row['Capital Cobrado'] || 0;
    const intCobrado = row['Interés Cobrado'] || 0;
    const ivaCobrado = row['IVA Cobrado'] || 0;
    const totCobrado = capCobrado + intCobrado + ivaCobrado;
    const estado = row.Estado || 'PENDIENTE';

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
    const key = `${dueño}|${originador}`;

    if (!grupos[key]) {
      grupos[key] = { Dueño: dueño, Originador: originador, Capital: 0, 'Interés': 0, IVA: 0, Total: 0, ValorActual: 0, Cobrado: 0 };
    }
    grupos[key].Capital += cap;
    grupos[key]['Interés'] += int;
    grupos[key].IVA += iva;
    grupos[key].Total += tot;
    grupos[key].ValorActual += pv;
    grupos[key].Cobrado += totCobrado;

    const rawEstado = (row.Estado || '').toUpperCase();
    let normalizedEstado = 'OTRO';
    if (rawEstado.includes('APROBADO')) normalizedEstado = 'APROBADO';
    else if (rawEstado.includes('ACTIVO') || rawEstado === 'PENDIENTE' || rawEstado === '') normalizedEstado = 'ACTIVO';
    else if (rawEstado.includes('MOROS')) normalizedEstado = 'MOROSO';
    else if (rawEstado.includes('INCOBRABLE')) normalizedEstado = 'INCOBRABLE';
    else if (rawEstado.includes('JUDICIALIZADO')) normalizedEstado = 'JUDICIALIZADO';

    const capInt = cap + int;
    const isVencido = fVto < fechaCorteDate;
    
    if (isVencido) {
      resumenEstados[normalizedEstado].Vencido += capInt;
    } else {
      resumenEstados[normalizedEstado].AVencer += capInt;
    }
    resumenEstados[normalizedEstado].Total += capInt;

    // Calcular días de mora si es MOROSO
    if (normalizedEstado === 'MOROSO') {
      let diasMora = Math.floor((fechaCorteDate - fVto) / (1000 * 60 * 60 * 24));
      if (diasMora < 1) diasMora = 1; // Si está moroso, asumimos al menos 1 día para que agrupe en "1 - 30 días"
      
      const bucket = moraBuckets.find(b => diasMora >= b.min && diasMora <= b.max);
      if (bucket) {
        bucket.Capital += cap;
        bucket.Interés += int;
        bucket.IVA += iva;
        bucket.Total += tot;
      }
    }

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

  const uniqueDueños = ['Todos', ...new Set(data.map(d => d.Dueño || 'Desconocido'))].sort();
  const uniqueOriginadores = ['Todos', ...new Set(data.map(d => d.Originador || 'N/A'))].sort();

  const groupedData = Object.values(grupos);
  const periodData = Object.values(gruposPeriodo).sort((a, b) => a.Periodo.localeCompare(b.Periodo));
  const estadosList = Object.values(resumenEstados).filter(e => e.Total > 0 || e.Estado !== 'Otro');

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
          <button 
            onClick={exportToPDF}
            disabled={isExporting}
            style={{ 
              padding: '8px 16px', 
              borderRadius: '8px', 
              border: 'none',
              background: 'var(--color-capital)',
              color: 'white',
              fontWeight: 'bold',
              cursor: isExporting ? 'not-allowed' : 'pointer',
              opacity: isExporting ? 0.7 : 1,
              marginLeft: '10px'
            }}
          >
            {isExporting ? 'Generando PDF...' : 'Exportar a PDF'}
          </button>
        </div>
      </header>

      {/* Filtros */}
      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px', flexWrap: 'wrap' }}>
        
        {/* Filtro Dueños Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', position: 'relative' }}>
          <label style={{ color: 'var(--text-secondary)', fontWeight: '500' }}>Dueño:</label>
          <div style={{ position: 'relative' }}>
            <button 
              onClick={() => setOpenDueño(!openDueño)}
              style={{ padding: '8px 12px', borderRadius: '8px', background: 'rgba(0,0,0,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer', minWidth: '150px', textAlign: 'left', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
              <span>{filtroDueños.length === 0 ? 'Todos' : `${filtroDueños.length} seleccionados`}</span>
              <span style={{ fontSize: '0.8rem', marginLeft: '10px' }}>▼</span>
            </button>
            
            {openDueño && (
              <div className="custom-scrollbar" style={{ position: 'absolute', top: '100%', left: 0, marginTop: '5px', padding: '8px', borderRadius: '8px', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.2)', maxHeight: '200px', overflowY: 'auto', minWidth: '220px', zIndex: 10, boxShadow: '0 4px 15px rgba(0,0,0,0.5)' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', cursor: 'pointer', fontSize: '0.9rem' }}>
                  <input type="checkbox" checked={filtroDueños.length === 0} onChange={() => setFiltroDueños([])} />
                  <span style={{ opacity: filtroDueños.length === 0 ? 1 : 0.6 }}>Todos</span>
                </label>
                {uniqueDueños.filter(d => d !== 'Todos').map(d => (
                  <label key={d} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', cursor: 'pointer', fontSize: '0.9rem' }}>
                    <input 
                      type="checkbox" 
                      checked={filtroDueños.includes(d)} 
                      onChange={(e) => {
                        if (e.target.checked) setFiltroDueños([...filtroDueños, d]);
                        else setFiltroDueños(filtroDueños.filter(item => item !== d));
                      }} 
                    />
                    <span style={{ opacity: filtroDueños.includes(d) ? 1 : 0.6 }}>{d}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Filtro Originadores Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', position: 'relative' }}>
          <label style={{ color: 'var(--text-secondary)', fontWeight: '500' }}>Originador:</label>
          <div style={{ position: 'relative' }}>
            <button 
              onClick={() => setOpenOriginador(!openOriginador)}
              style={{ padding: '8px 12px', borderRadius: '8px', background: 'rgba(0,0,0,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer', minWidth: '150px', textAlign: 'left', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
              <span>{filtroOriginadores.length === 0 ? 'Todos' : `${filtroOriginadores.length} seleccionados`}</span>
              <span style={{ fontSize: '0.8rem', marginLeft: '10px' }}>▼</span>
            </button>
            
            {openOriginador && (
              <div className="custom-scrollbar" style={{ position: 'absolute', top: '100%', left: 0, marginTop: '5px', padding: '8px', borderRadius: '8px', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.2)', maxHeight: '200px', overflowY: 'auto', minWidth: '220px', zIndex: 10, boxShadow: '0 4px 15px rgba(0,0,0,0.5)' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', cursor: 'pointer', fontSize: '0.9rem' }}>
                  <input type="checkbox" checked={filtroOriginadores.length === 0} onChange={() => setFiltroOriginadores([])} />
                  <span style={{ opacity: filtroOriginadores.length === 0 ? 1 : 0.6 }}>Todos</span>
                </label>
                {uniqueOriginadores.filter(o => o !== 'Todos').map(o => (
                  <label key={o} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', cursor: 'pointer', fontSize: '0.9rem' }}>
                    <input 
                      type="checkbox" 
                      checked={filtroOriginadores.includes(o)} 
                      onChange={(e) => {
                        if (e.target.checked) setFiltroOriginadores([...filtroOriginadores, o]);
                        else setFiltroOriginadores(filtroOriginadores.filter(item => item !== o));
                      }} 
                    />
                    <span style={{ opacity: filtroOriginadores.includes(o) ? 1 : 0.6 }}>{o}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '20px' }}>
        <button 
          onClick={() => setActiveTab('total')}
          style={{ 
            padding: '10px 20px', 
            borderRadius: '8px', 
            border: 'none',
            background: activeTab === 'total' ? 'var(--color-total)' : 'rgba(255,255,255,0.05)',
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
            background: activeTab === 'periodo' ? 'var(--color-total)' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'periodo' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Detalle por Período
        </button>
        <button 
          onClick={() => setActiveTab('estados')}
          style={{ 
            padding: '10px 20px', 
            borderRadius: '8px', 
            border: 'none',
            background: activeTab === 'estados' ? 'var(--color-total)' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'estados' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Detalle de Estados
        </button>
        <button 
          onClick={() => setActiveTab('morosidad')}
          style={{ 
            padding: '10px 20px', 
            borderRadius: '8px', 
            border: 'none',
            background: activeTab === 'morosidad' ? 'var(--color-total)' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'morosidad' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Análisis de Morosidad
        </button>
      </div>

      {isExporting && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(15, 23, 42, 0.9)',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: '1.5rem',
          fontWeight: 'bold'
        }}>
          <div>Generando PDF...</div>
          <div style={{ fontSize: '1rem', marginTop: '10px', color: 'var(--text-secondary)' }}>Por favor espere mientras se capturan los gráficos.</div>
        </div>
      )}

      {(activeTab === 'total' || isExporting) && (
        <div id="export-tab-total">
          {/* KPI Cards */}
          <div style={{ 
            display: 'flex', 
            flexWrap: 'wrap',
            justifyContent: 'center', 
            gap: '20px', 
            marginBottom: '30px' 
          }}>
            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-capital)', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Total Capital Activo</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalCapital)}</span>
            </div>
            
            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-interes)', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Total Interés</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalInteres)}</span>
            </div>

            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-capint)', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Capital + Interés</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalCapital + totalInteres)}</span>
            </div>

            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-iva)', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Total IVA</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalIva)}</span>
            </div>

            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-total)', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Saldo Total a Favor</span>
              <span style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{formatCurrency(totalGeneral)}</span>
            </div>

            <div className="glass-panel" style={{ width: '100%', minWidth: '260px', maxWidth: '300px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-valoractual)', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '10px', transition: 'transform 0.2s', cursor: 'default', background: 'linear-gradient(135deg, rgba(233, 30, 99, 0.1), rgba(0,0,0,0))' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-5px)'} onMouseOut={e => e.currentTarget.style.transform = 'translateY(0)'}>
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
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-capint)' }}>{formatCurrency(row.Capital + row['Interés'])}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.IVA)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace' }}>{formatCurrency(row.Total)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-valoractual)' }}>{formatCurrency(row.ValorActual)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {(activeTab === 'periodo' || isExporting) && (
          <div id="export-tab-periodo">
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
                    <Bar dataKey="Capital" stackId="a" fill="var(--color-capital)" name="Capital" />
                    <Bar dataKey="Interés" stackId="a" fill="var(--color-interes)" name="Interés" />
                    <Bar dataKey="IVA" stackId="a" fill="var(--color-iva)" name="IVA" />
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
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-capint)' }}>{formatCurrency(row.Capital + row['Interés'])}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.IVA)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-total)' }}>{formatCurrency(row.Total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
            </div>
          </div>
      )}

      {(activeTab === 'estados' || isExporting) && (
        <div id="export-tab-estados">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', marginBottom: '30px' }}>
            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', flex: '1 1 300px', display: 'flex', flexDirection: 'column' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600', textAlign: 'center' }}>Porcentaje por Estado</h2>
              <div style={{ flex: 1, minHeight: '250px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={estadosList.filter(e => e.Total > 0)}
                      cx="50%"
                      cy="50%"
                      labelLine={true}
                      label={renderCustomizedLabel}
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="Total"
                      nameKey="Estado"
                    >
                      {estadosList.filter(e => e.Total > 0).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value) => formatCurrency(value)}
                      contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'white' }}
                      itemStyle={{ color: 'white' }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', flex: '2 1 500px' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Distribución de Estados (Capital + Interés)</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '15px' }}>
                {estadosList.map((d, idx) => (
                  <div key={idx} style={{ 
                    background: 'rgba(0,0,0,0.2)', 
                    border: `1px solid ${d.fill}40`, 
                    borderLeft: `4px solid ${d.fill}`, 
                    borderRadius: '8px', 
                    padding: '15px 20px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '5px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}>
                    <span style={{ color: d.fill, fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{d.Estado}</span>
                    <span style={{ fontSize: '1.3rem', fontWeight: 'bold', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{formatCurrency(d.Total)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Detalle de Montos por Estado (Capital + Interés)</h2>
            {estadosList.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos disponibles en la cartera activa.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Estado</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Vencido</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>A Vencer</th>
                      <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {estadosList.map((row, idx) => (
                      <tr key={idx} style={{ 
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        transition: 'background-color 0.2s',
                      }} className="table-row-hover">
                        <td style={{ padding: '15px 10px', fontWeight: '500', color: row.fill }}>{row.Estado.toUpperCase()}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-interes)' }}>{formatCurrency(row.Vencido)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-total)' }}>{formatCurrency(row.AVencer)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace' }}>{formatCurrency(row.Total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {(activeTab === 'morosidad' || isExporting) && (
        <div id="export-tab-morosidad">
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', marginBottom: '30px', height: '400px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Composición de la Morosidad</h2>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={moraBuckets}
                margin={{ top: 10, right: 30, left: 20, bottom: 25 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis dataKey="label" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} />
                <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`} />
                <Tooltip 
                  formatter={(value) => formatCurrency(value)}
                  contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'white' }}
                  itemStyle={{ color: 'white' }}
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Bar dataKey="Capital" stackId="a" fill="var(--color-capital)" name="Capital" />
                <Bar dataKey="Interés" stackId="a" fill="var(--color-interes)" name="Interés" />
                <Bar dataKey="IVA" stackId="a" fill="var(--color-iva)" name="IVA" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', marginBottom: '30px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Detalle de Créditos Morosos</h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                  <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Días de Morosidad</th>
                  <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Capital</th>
                  <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Interés</th>
                  <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>IVA</th>
                  <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Total</th>
                </tr>
              </thead>
              <tbody>
                {moraBuckets.map((row, idx) => (
                  <tr key={idx} style={{ 
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    transition: 'background-color 0.2s',
                  }} className="table-row-hover">
                    <td style={{ padding: '15px 10px', fontWeight: '500' }}>{row.label}</td>
                    <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.Capital)}</td>
                    <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.Interés)}</td>
                    <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.IVA)}</td>
                    <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-valoractual)' }}>{formatCurrency(row.Total)}</td>
                  </tr>
                ))}
                <tr style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}>
                  <td style={{ padding: '15px 10px', fontWeight: 'bold' }}>TOTAL MOROSIDAD</td>
                  <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace' }}>{formatCurrency(moraBuckets.reduce((acc, b) => acc + b.Capital, 0))}</td>
                  <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace' }}>{formatCurrency(moraBuckets.reduce((acc, b) => acc + b.Interés, 0))}</td>
                  <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace' }}>{formatCurrency(moraBuckets.reduce((acc, b) => acc + b.IVA, 0))}</td>
                  <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-valoractual)' }}>{formatCurrency(moraBuckets.reduce((acc, b) => acc + b.Total, 0))}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        </div>
      )}

      <style>{`
        .table-row-hover:hover {
          background-color: rgba(255,255,255,0.02);
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(0,0,0,0.1);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.2);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.3);
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
