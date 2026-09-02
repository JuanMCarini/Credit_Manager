import React, { useState, useEffect, useMemo, useRef, useTransition } from 'react';
import axiosClient from '../api/axiosClient';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area, LabelList, ComposedChart, Line} from 'recharts';
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { es } from 'date-fns/locale';
const formatCurrency = (value) => {
  if (value === null || value === undefined) return "$ 0";
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const CHART_COLORS = ['#6366f1', '#14b8a6', '#f59e0b', '#ec4899', '#8b5cf6', '#10b981', '#f43f5e', '#3b82f6'];

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

const renderCustomizedLabelMora = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index, payload }) => {
  const radius = outerRadius + 10;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  if (payload.isSmall && !payload.showSmallSum) return null;

  const displayPercent = payload.showSmallSum ? payload.smallSumPercent : percent;
  if (isNaN(displayPercent)) return null;
  const isRightSide = x > cx;

  if (payload.showSmallSum) {
    return (
      <g>
        <text
          x={x}
          y={y - 12}
          fill="var(--text-primary)"
          textAnchor={isRightSide ? 'start' : 'end'}
          dominantBaseline="central"
          fontSize={16}
          fontWeight="bold"
        >
          {`${(displayPercent * 100).toFixed(2)}%`}
        </text>
        <text
          x={x}
          y={y + 12}
          fill="var(--text-secondary)"
          textAnchor={isRightSide ? 'start' : 'end'}
          dominantBaseline="central"
          fontSize={10}
        >
          (MENORES A 5%)
        </text>
      </g>
    );
  }

  return (
    <text
      x={x}
      y={y}
      fill="var(--text-primary)"
      textAnchor={isRightSide ? 'start' : 'end'}
      dominantBaseline="central"
      fontSize={16}
      fontWeight="bold"
    >
      {`${(displayPercent * 100).toFixed(2)}%`}
    </text>
  );
};

const DashboardCarteraPage = () => {
  const [data, setData] = useState([]);
  const [evolutionData, setEvolutionData] = useState([]);
  const [cobranzasEvolutionData, setCobranzasEvolutionData] = useState([]);
  const [espData, setEspData] = useState(null);
  const [nPeriodosEsp, setNPeriodosEsp] = useState(2);
  const [frecuenciaEsp, setFrecuenciaEsp] = useState(1);
  const [comparePeriodA, setComparePeriodA] = useState("");
  const [comparePeriodB, setComparePeriodB] = useState("");
  const [loading, setLoading] = useState(true);
  const [espLoading, setEspLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fechaCorteDate, setFechaCorteDate] = useState(() => {
    const today = new Date();
    return new Date(today.getFullYear(), today.getMonth(), 0);
  });
  const [fechaCorte, setFechaCorte] = useState(() => {
    const today = new Date();
    const lastDay = new Date(today.getFullYear(), today.getMonth(), 0);
    const yyyy = lastDay.getFullYear();
    const mm = String(lastDay.getMonth() + 1).padStart(2, '0');
    const dd = String(lastDay.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  });

  const handleDateChange = (date) => {
    setFechaCorteDate(date);
    if (date) {
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, '0');
      const dd = String(date.getDate()).padStart(2, '0');
      setFechaCorte(`${yyyy}-${mm}-${dd}`);
    }
  };

  const [tasaDescuento, setTasaDescuento] = useState(0);
  const [tasaDescuentoStr, setTasaDescuentoStr] = useState("0 %");
  const [appliedFilters, setAppliedFilters] = useState(() => {
    const today = new Date();
    const lastDay = new Date(today.getFullYear(), today.getMonth(), 0);
    const yyyy = lastDay.getFullYear();
    const mm = String(lastDay.getMonth() + 1).padStart(2, '0');
    const dd = String(lastDay.getDate()).padStart(2, '0');
    return {
      fechaCorte: `${yyyy}-${mm}-${dd}`,
      tasaDescuento: 0,
      nPeriodosEsp: 2,
      frecuenciaEsp: 1
    };
  });
  const [activeTab, setActiveTab] = useState('situacion_patrimonial'); // 'situacion_patrimonial', 'total', 'periodo', etc.
  const [filtroDueños, setFiltroDueños] = useState([]); // empty means 'Todos'
  const [filtroOriginadores, setFiltroOriginadores] = useState([]); // empty means 'Todos'
  const [openDueño, setOpenDueño] = useState(false);
  const [openOriginador, setOpenOriginador] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState(null);
  const [isPending, startTransition] = useTransition();

  const exportToPDF = async (orientation = 'p') => {
    setIsExporting(true);
    setExportFormat(orientation);

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
    root.style.setProperty('--color-total', '#2196F3');
    root.style.setProperty('--color-valoractual', '#E91E63');

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const mainContent = document.querySelector('.main-content');
    const originalMainOverflow = mainContent ? mainContent.style.overflow : '';
    if (mainContent) {
      mainContent.style.overflow = 'visible';
    }

    setTimeout(async () => {
      try {
        const pdf = new jsPDF(orientation, 'mm', 'a4');
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = pdf.internal.pageSize.getHeight();

        // --- PORTADA ---
        pdf.setFillColor(255, 255, 255);
        pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');

        try {
          const img = new Image();
          img.src = '/static/logo.png';
          await new Promise((resolve, reject) => {
            img.onload = () => resolve();
            img.onerror = () => reject(new Error('Image failed to load'));
          });

          const logoWidth = 80;
          const logoHeight = (img.height * logoWidth) / img.width;
          pdf.addImage(img, 'PNG', (pdfWidth - logoWidth) / 2, (pdfHeight / 2) - logoHeight - 20, logoWidth, logoHeight);
        } catch (err) {
          console.warn('Could not load logo for PDF cover', err);
          pdf.setFontSize(30);
          pdf.setTextColor(0, 0, 0);
          pdf.text('CreditManager', pdfWidth / 2, pdfHeight / 2 - 20, { align: 'center' });
        }

        pdf.setFontSize(24);
        pdf.setTextColor(0, 0, 0);
        pdf.text('Dashboard Financiero', pdfWidth / 2, pdfHeight / 2 + 10, { align: 'center' });

        pdf.setFontSize(12);
        pdf.setTextColor(100, 100, 100);
        const dueñosTextCover = filtroDueños.length > 0 ? filtroDueños.join(', ') : 'Todos';
        const origTextCover = filtroOriginadores.length > 0 ? filtroOriginadores.join(', ') : 'Todos';
        pdf.text(`Fecha de Corte: ${appliedFilters.fechaCorte.split('-').reverse().join('/')}`, pdfWidth / 2, pdfHeight / 2 + 25, { align: 'center' });
        pdf.text(`TNA: ${appliedFilters.tasaDescuento}%`, pdfWidth / 2, pdfHeight / 2 + 32, { align: 'center' });
        pdf.text(`Dueños: ${dueñosTextCover}`, pdfWidth / 2, pdfHeight / 2 + 39, { align: 'center' });
        pdf.text(`Originadores: ${origTextCover}`, pdfWidth / 2, pdfHeight / 2 + 46, { align: 'center' });

        pdf.setFontSize(10);
        pdf.text(`Generado el: ${new Date().toLocaleDateString('es-AR')} ${new Date().toLocaleTimeString('es-AR')}`, pdfWidth / 2, pdfHeight - 20, { align: 'center' });
        // --- FIN PORTADA ---

        const tabsToExport = [
          { id: 'export-tab-situacion', title: 'Estado de Situación Patrimonial' },
          { id: 'export-tab-total', title: 'Resumen Cartera' },
          { id: 'export-tab-evolucion', title: 'Evolución Cartera' },
          { id: 'export-tab-composicion', title: 'Composición Cartera' },
          { id: 'export-tab-periodo', title: 'Caída de Cuotas' },
          { id: 'export-tab-colocaciones', title: 'Colocaciones Cartera' },
          { id: 'export-tab-cobranzas', title: 'Cobranzas Cartera' },
          { id: 'export-tab-estados', title: 'Estados Cartera' },
          { id: 'export-tab-morosidad', title: 'Morosidad Cartera' }
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
            const availableWidth = pdfWidth - margin * 2;
            const maxImageHeight = pdfHeight - margin * 2 - 30; // 30 for titles and footer
            
            let width = availableWidth;
            let height = width / ratio;

            if (height > maxImageHeight) {
              height = maxImageHeight;
              width = height * ratio;
            }

            // Calcular posiciones para centrar vertical y horizontalmente
            const totalBlockHeight = 20 + height; // 20 es el espacio que ocupan los titulos
            const startY = Math.max(15, (pdfHeight - totalBlockHeight) / 2 + 5); 
            const offsetX = (availableWidth - width) / 2;

            pdf.addPage();

            pdf.setFillColor(255, 255, 255);
            pdf.rect(0, 0, pdfWidth, pdfHeight, 'F');

            pdf.setFontSize(16);
            pdf.setTextColor(0, 0, 0);
            pdf.text(`Dashboard - ${tabsToExport[i].title}`, margin, startY);

            pdf.setFontSize(9);
            pdf.setTextColor(100, 100, 100);
            const dueñosText = filtroDueños.length > 0 ? filtroDueños.join(', ') : 'Todos';
            const origText = filtroOriginadores.length > 0 ? filtroOriginadores.join(', ') : 'Todos';
            const filtrosStr = `Fecha de Corte: ${appliedFilters.fechaCorte.split('-').reverse().join('/')} | TNA: ${appliedFilters.tasaDescuento}% | Dueños: ${dueñosText} | Originadores: ${origText}`;
            pdf.text(filtrosStr, margin, startY + 7);

            pdf.addImage(imgData, 'PNG', margin + offsetX, startY + 13, width, height);

            if (orientation === 'p') {
              pdf.setFontSize(10);
              pdf.setTextColor(150, 150, 150);
              pdf.text(`Página ${pdf.internal.getNumberOfPages()}`, pdfWidth / 2, pdfHeight - 10, { align: 'center' });
            }

            pageCount++;
          }
        }

        const tipoReporte = orientation === 'p' ? 'Detallado' : 'Grafico';
        pdf.save(`Reporte Cartera - ${tipoReporte} - ${appliedFilters.fechaCorte}.pdf`);
      } catch (err) {
        console.error("Error exporting to PDF:", err);
      } finally {
        setIsExporting(false);
        setExportFormat(null);
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
    const fetchMainData = async () => {
      try {
        setLoading(true);
        const [response, evolutionResponse, tnaResponse, cobranzasEvoResponse] = await Promise.all([
          axiosClient.get('/api/v1/reports/balances', {
            params: {
              fecha: appliedFilters.fechaCorte,
              con_saldo: false,
              agrupar: false
            }
          }),
          axiosClient.get('/api/v1/reports/balances/evolution', {
            params: { meses: 12, fecha: appliedFilters.fechaCorte }
          }),
          axiosClient.get('/api/v1/carteras/venta/tna_reciente', {
            params: { fecha: appliedFilters.fechaCorte }
          }).catch(err => {
            console.error("Error fetching recent TNA:", err);
            return { data: { tna: 0 } };
          }),
          axiosClient.get('/api/v1/reports/cobranzas/evolution', {
            params: { meses: 12, fecha: appliedFilters.fechaCorte }
          })
        ]);
        
        setData(response.data);
        setEvolutionData(evolutionResponse.data);
        setCobranzasEvolutionData(cobranzasEvoResponse.data);

        if (tnaResponse && tnaResponse.data && tnaResponse.data.tna !== undefined) {
          const newTna = tnaResponse.data.tna;
          setTasaDescuento(newTna);
          setTasaDescuentoStr(`${newTna} %`);
          setAppliedFilters(prev => ({ ...prev, tasaDescuento: newTna }));
        }
      } catch (err) {
        console.error("Error cargando dashboard:", err);
        setError("Ocurrió un error al cargar la información del dashboard.");
      } finally {
        setLoading(false);
      }
    };

    fetchMainData();
  }, [appliedFilters.fechaCorte]);

  useEffect(() => {
    const fetchEspData = async () => {
      try {
        setEspLoading(true);
        const espResponse = await axiosClient.get('/api/v1/reports/esp', {
          params: { fecha: appliedFilters.fechaCorte, periodos: appliedFilters.nPeriodosEsp, salto: appliedFilters.frecuenciaEsp, tna_descuento: appliedFilters.tasaDescuento / 100 }
        });
        if (espResponse && espResponse.data) {
          setEspData(espResponse.data);
        }
      } catch (err) {
        console.error("Error fetching ESP data:", err);
        setEspData(null);
      } finally {
        setEspLoading(false);
      }
    };

    fetchEspData();
  }, [appliedFilters.fechaCorte, appliedFilters.nPeriodosEsp, appliedFilters.frecuenciaEsp, appliedFilters.tasaDescuento]);

  // Calcular KPIs y agrupaciones
  let totalCapital = 0;
  let totalInteres = 0;
  let totalIva = 0;
  let totalGeneral = 0;
  let valorActual = 0;

  const grupos = {};
  const gruposPeriodo = {};
  const tna = appliedFilters.tasaDescuento / 100;
  const parsedFechaCorteDate = new Date(appliedFilters.fechaCorte + 'T00:00:00'); // Force local midnight
  const corteYearMonth = appliedFilters.fechaCorte.substring(0, 7);

  const resumenEstados = {
    'APROBADO': { Estado: 'Aprobado', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-capital)' },
    'ACTIVO': { Estado: 'Activo', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-total)' },
    'MOROSO': { Estado: 'Moroso', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-interes)' },
    'INCOBRABLE': { Estado: 'Incobrable', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-valoractual)' },
    'JUDICIALIZADO': { Estado: 'Judicializado', Vencido: 0, AVencer: 0, Total: 0, fill: 'var(--color-iva)' },
    'CANCELADO': { Estado: 'Cancelado', Vencido: 0, AVencer: 0, Total: 0, fill: '#9E9E9E' },
    'OTRO': { Estado: 'Otro', Vencido: 0, AVencer: 0, Total: 0, fill: '#607D8B' }
  };

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
    let diasVto = Math.floor((fVto - parsedFechaCorteDate) / (1000 * 60 * 60 * 24));
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

    const rawEstado = (row['Estado Credito'] || row.Estado || '').toUpperCase();
    let normalizedEstado = 'OTRO';
    if (rawEstado.includes('APROBADO') || rawEstado.includes('FIRMADO')) normalizedEstado = 'APROBADO';
    else if (rawEstado.includes('ACTIVO') || rawEstado === 'PENDIENTE' || rawEstado === '') normalizedEstado = 'ACTIVO';
    else if (rawEstado.includes('MOROS')) normalizedEstado = 'MOROSO';
    else if (rawEstado.includes('INCOBRABLE')) normalizedEstado = 'INCOBRABLE';
    else if (rawEstado.includes('JUDICIAL')) normalizedEstado = 'JUDICIALIZADO';
    else if (rawEstado.includes('CANCELAD')) normalizedEstado = 'CANCELADO';

    let capInt = cap + int;
    if (normalizedEstado === 'CANCELADO') {
      capInt = cap + int + capCobrado + intCobrado;
    }
    
    const isVencido = fVto < parsedFechaCorteDate;

    if (isVencido) {
      resumenEstados[normalizedEstado].Vencido += capInt;
    } else {
      resumenEstados[normalizedEstado].AVencer += capInt;
    }
    resumenEstados[normalizedEstado].Total += capInt;

    // Agrupar por periodo (vencimientos futuros estrictamente posteriores a la fecha de corte)
    if (fVto > parsedFechaCorteDate) {
      const vtoYearMonth = fVtoStr.substring(0, 7);
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

  const groupedData = Object.values(grupos).filter(g => Math.abs(g.Total) > 0.01);
  const periodData = Object.values(gruposPeriodo).sort((a, b) => a.Periodo.localeCompare(b.Periodo));
  const estadosList = Object.values(resumenEstados).filter(e => e.Total > 0 || e.Estado !== 'Otro');

  const filteredEvolutionData = useMemo(() => {
    return evolutionData.map(month => {
      let capital = 0;
      let interes = 0;
      let iva = 0;
      let total = 0;

      const ownerCapital = {};
      let totalCapitalForDistribution = 0;

      if (month.detalles) {
        month.detalles.forEach(d => {
          const dueño = String(d.Dueño || 'Desconocido').trim().toUpperCase();
          const originador = String(d.Originador || 'N/A').trim().toUpperCase();

          const matchDueño = filtroDueños.length === 0 || filtroDueños.some(f => String(f).trim().toUpperCase() === dueño);
          const matchOriginador = filtroOriginadores.length === 0 || filtroOriginadores.some(f => String(f).trim().toUpperCase() === originador);

          if (matchDueño && matchOriginador) {
            capital += d.capital;
            interes += d.interes;
            iva += d.iva;
            total += d.total;
          }

          if (matchOriginador) {
            const dueñoRaw = String(d.Dueño || 'Desconocido').trim();
            if (!ownerCapital[dueñoRaw]) ownerCapital[dueñoRaw] = 0;
            ownerCapital[dueñoRaw] += d.total;
            totalCapitalForDistribution += d.total;
          }
        });
      }

      const monthData = {
        ...month,
        capital,
        interes,
        iva,
        total
      };

      Object.keys(ownerCapital).forEach(owner => {
        monthData[`owner_${owner}`] = totalCapitalForDistribution > 0 ? (ownerCapital[owner] / totalCapitalForDistribution) * 100 : 0;
        monthData[`ownerRaw_${owner}`] = ownerCapital[owner];
      });

      return monthData;
    });
  }, [evolutionData, filtroDueños, filtroOriginadores]);

  const evolutionUniqueDueños = useMemo(() => {
    const dueños = new Set();
    filteredEvolutionData.forEach(month => {
      Object.keys(month).forEach(key => {
        if (key.startsWith('owner_')) {
          dueños.add(key.replace('owner_', ''));
        }
      });
    });
    return Array.from(dueños).sort();
  }, [filteredEvolutionData]);

  const filteredCobranzasEvolutionData = useMemo(() => {
    if (!cobranzasEvolutionData) return [];
    return cobranzasEvolutionData.map(month => {
      let capital = 0;
      let interes = 0;
      let iva = 0;
      let total = 0;
      let recuperoMora = 0;
      const ownerRaw = {};
      const origRaw = {};
      const tipoRaw = {};
      
      let totalTeorico = 0;
      let totalMismoPeriodo = 0;

      if (month.detalles) {
        month.detalles.forEach(d => {
          const dueño = String(d.Dueño || 'Desconocido').trim().toUpperCase();
          const originador = String(d.Originador || 'N/A').trim().toUpperCase();

          const matchDueño = filtroDueños.length === 0 || filtroDueños.some(f => String(f).trim().toUpperCase() === dueño);
          const matchOriginador = filtroOriginadores.length === 0 || filtroOriginadores.some(f => String(f).trim().toUpperCase() === originador);

          if (matchDueño && matchOriginador) {
            capital += d.capital;
            interes += d.interes;
            iva += d.iva;
            total += d.total;
            recuperoMora += d.recupero_mora || 0;
            
            const dueñoRawStr = String(d.Dueño || 'Desconocido').trim();
            const origRawStr = String(d.Originador || 'N/A').trim();
            const tipoRawStr = String(d.tipo_cobranza || 'COMUN').trim();
            
            if (!ownerRaw[dueñoRawStr]) ownerRaw[dueñoRawStr] = 0;
            ownerRaw[dueñoRawStr] += d.total;
            
            if (!origRaw[origRawStr]) origRaw[origRawStr] = 0;
            origRaw[origRawStr] += d.total;
            
            if (!tipoRaw[tipoRawStr]) tipoRaw[tipoRawStr] = 0;
            tipoRaw[tipoRawStr] += d.total;
          }
        });
      }

      if (month.teoricos) {
        month.teoricos.forEach(t => {
          const dueño = String(t.Dueño || 'Desconocido').trim().toUpperCase();
          const originador = String(t.Originador || 'N/A').trim().toUpperCase();

          const matchDueño = filtroDueños.length === 0 || filtroDueños.some(f => String(f).trim().toUpperCase() === dueño);
          const matchOriginador = filtroOriginadores.length === 0 || filtroOriginadores.some(f => String(f).trim().toUpperCase() === originador);

          if (matchDueño && matchOriginador) {
            totalTeorico += t.total;
            totalMismoPeriodo += t.total_cobr || 0;
          }
        });
      }

      const monthData = {
        ...month,
        capital,
        interes,
        iva,
        total,
        totalTeorico,
        totalMismoPeriodo,
        recuperoMora
      };

      Object.keys(ownerRaw).forEach(owner => {
        monthData[`ownerRaw_${owner}`] = ownerRaw[owner];
      });
      Object.keys(origRaw).forEach(orig => {
        monthData[`origRaw_${orig}`] = origRaw[orig];
      });
      Object.keys(tipoRaw).forEach(tipo => {
        monthData[`tipoRaw_${tipo}`] = tipoRaw[tipo];
      });

      return monthData;
    });
  }, [cobranzasEvolutionData, filtroDueños, filtroOriginadores]);

  const cobranzasUniqueOriginadores = useMemo(() => {
    const origs = new Set();
    filteredCobranzasEvolutionData.forEach(month => {
      Object.keys(month).forEach(key => {
        if (key.startsWith('origRaw_')) origs.add(key.replace('origRaw_', ''));
      });
    });
    return Array.from(origs).sort();
  }, [filteredCobranzasEvolutionData]);

  const cobranzasUniqueTipos = useMemo(() => {
    const tipos = new Set();
    filteredCobranzasEvolutionData.forEach(month => {
      Object.keys(month).forEach(key => {
        if (key.startsWith('tipoRaw_')) tipos.add(key.replace('tipoRaw_', ''));
      });
    });
    return Array.from(tipos).sort();
  }, [filteredCobranzasEvolutionData]);

  const colocacionesData = useMemo(() => {
    const creditos = {};
    data.forEach(row => {
      const dueño = row.Dueño || 'Desconocido';
      const originador = row.Originador || 'N/A';

      const matchDueño = filtroDueños.length === 0 || filtroDueños.includes(dueño);
      const matchOriginador = filtroOriginadores.length === 0 || filtroOriginadores.includes(originador);

      if (!matchDueño || !matchOriginador) return;
      if (originador === 'PENALTY') return;

      const id = row['ID Credito'];
      if (!id) return;

      if (!creditos[id]) {
        creditos[id] = {
          fechaEmision: row['Fecha Emisión'],
          originador: originador,
          dueño: dueño,
          montoOriginal: 0,
          montoGenerado: 0,
        };
      }
      creditos[id].montoOriginal += (row.Capital || 0) + (row['Capital Cobrado'] || 0);
      creditos[id].montoGenerado += (row.Capital || 0) + (row['Capital Cobrado'] || 0)
        + (row['Interés'] || 0) + (row['Interés Cobrado'] || 0)
        + (row.IVA || 0) + (row['IVA Cobrado'] || 0);
    });

    const periodos = {};
    Object.values(creditos).forEach(c => {
      if (!c.fechaEmision) return;
      const d = new Date(c.fechaEmision);
      if (isNaN(d.getTime())) return;

      const periodo = c.fechaEmision.substring(0, 7); // 'YYYY-MM'
      if (!periodos[periodo]) {
        periodos[periodo] = { periodo, totalColocado: 0, totalGenerado: 0 };
      }

      periodos[periodo].totalColocado += c.montoOriginal;
      periodos[periodo].totalGenerado += c.montoGenerado;

      const origKey = `orig_${c.originador}`;
      const origGenKey = `origGen_${c.originador}`;
      if (!periodos[periodo][origKey]) periodos[periodo][origKey] = 0;
      if (!periodos[periodo][origGenKey]) periodos[periodo][origGenKey] = 0;
      periodos[periodo][origKey] += c.montoOriginal;
      periodos[periodo][origGenKey] += c.montoGenerado;
    });

    const allData = Object.values(periodos).sort((a, b) => a.periodo.localeCompare(b.periodo));

    allData.forEach(p => {
      Object.keys(p).forEach(k => {
        if (k.startsWith('orig_')) {
          const originador = k.replace('orig_', '');
          const val = p[k];
          p[`origPct_${originador}`] = p.totalColocado > 0 ? (val / p.totalColocado) * 100 : 0;
        }
      });
    });

    // Retornamos los últimos 12 periodos con actividad
    return allData.slice(-12);
  }, [data, filtroDueños, filtroOriginadores]);

  const moraBuckets = useMemo(() => {
    const buckets = [
      { label: 'Al día', min: 0, max: 0, Vencido: 0, AVencer: 0, Total: 0, fill: '#4CAF50' },
      { label: '1 - 30 días', min: 1, max: 30, Vencido: 0, AVencer: 0, Total: 0, fill: '#FFB74D' },
      { label: '31 - 60 días', min: 31, max: 60, Vencido: 0, AVencer: 0, Total: 0, fill: '#FF9800' },
      { label: '61 - 90 días', min: 61, max: 90, Vencido: 0, AVencer: 0, Total: 0, fill: '#F57C00' },
      { label: '91 - 180 días', min: 91, max: 180, Vencido: 0, AVencer: 0, Total: 0, fill: '#E65100' },
      { label: '181 - 365 días', min: 181, max: 365, Vencido: 0, AVencer: 0, Total: 0, fill: '#D32F2F' },
      { label: '> 365 días', min: 366, max: Infinity, Vencido: 0, AVencer: 0, Total: 0, fill: '#B71C1C' },
    ];

    const creditosMora = {};
    const parsedFechaCorteDate = new Date(appliedFilters.fechaCorte + 'T00:00:00');

    // Primer pasada: Calcular la mora (maxDiasMora) a nivel CRÉDITO, sin importar quién sea el dueño
    // de cada cuota. La mora es una propiedad del crédito.
    data.forEach(row => {
      const rawEstado = (row['Estado Credito'] || row.Estado || '').toUpperCase();
      let normalizedEstado = 'OTRO';
      if (rawEstado.includes('APROBADO') || rawEstado.includes('FIRMADO')) normalizedEstado = 'APROBADO';
      else if (rawEstado.includes('ACTIVO') || rawEstado === 'PENDIENTE' || rawEstado === '') normalizedEstado = 'ACTIVO';
      else if (rawEstado.includes('MOROS')) normalizedEstado = 'MOROSO';
      else if (rawEstado.includes('INCOBRABLE')) normalizedEstado = 'INCOBRABLE';
      else if (rawEstado.includes('JUDICIAL')) normalizedEstado = 'JUDICIALIZADO';
      else if (rawEstado.includes('CANCELAD')) normalizedEstado = 'CANCELADO';

      if (normalizedEstado === 'MOROSO' || normalizedEstado === 'ACTIVO' || normalizedEstado === 'APROBADO') {
        const id = row['ID Credito'];
        if (!id) return;

        if (!creditosMora[id]) {
          creditosMora[id] = { maxDiasMora: 0, totalVencido: 0, totalAVencer: 0, total: 0 };
        }

        const fVto = new Date(row['Fecha Vencimiento'] + 'T00:00:00');
        const isVencido = fVto < parsedFechaCorteDate;
        const balanceCuota = (row.Capital || 0) + (row['Interés'] || 0) + (row.IVA || 0);

        if (isVencido && balanceCuota > 0) {
          let diasMora = Math.floor((parsedFechaCorteDate - fVto) / (1000 * 60 * 60 * 24));
          if (diasMora < 1) diasMora = 1;

          if (diasMora > creditosMora[id].maxDiasMora) {
            creditosMora[id].maxDiasMora = diasMora;
          }
        }
      }
    });

    // Segunda pasada: Sumarizar los valores monetarios, pero SOLO de las cuotas que cumplen
    // los filtros seleccionados (Dueño, Originador).
    data.forEach(row => {
      const dueño = row.Dueño || 'Desconocido';
      const originador = row.Originador || 'N/A';

      const matchDueño = filtroDueños.length === 0 || filtroDueños.includes(dueño);
      const matchOriginador = filtroOriginadores.length === 0 || filtroOriginadores.includes(originador);

      if (!matchDueño || !matchOriginador) return;

      const rawEstado = (row['Estado Credito'] || row.Estado || '').toUpperCase();
      let normalizedEstado = 'OTRO';
      if (rawEstado.includes('APROBADO') || rawEstado.includes('FIRMADO')) normalizedEstado = 'APROBADO';
      else if (rawEstado.includes('ACTIVO') || rawEstado === 'PENDIENTE' || rawEstado === '') normalizedEstado = 'ACTIVO';
      else if (rawEstado.includes('MOROS')) normalizedEstado = 'MOROSO';
      else if (rawEstado.includes('INCOBRABLE')) normalizedEstado = 'INCOBRABLE';
      else if (rawEstado.includes('JUDICIAL')) normalizedEstado = 'JUDICIALIZADO';
      else if (rawEstado.includes('CANCELAD')) normalizedEstado = 'CANCELADO';

      if (normalizedEstado === 'MOROSO' || normalizedEstado === 'ACTIVO' || normalizedEstado === 'APROBADO') {
        const id = row['ID Credito'];
        if (!id || !creditosMora[id]) return;

        const fVto = new Date(row['Fecha Vencimiento'] + 'T00:00:00');
        const isVencido = fVto < parsedFechaCorteDate;
        const cuotaValue = (row.Capital || 0) + (row['Interés'] || 0) + (row.IVA || 0);

        if (isVencido) {
          creditosMora[id].totalVencido += cuotaValue;
        } else {
          creditosMora[id].totalAVencer += cuotaValue;
        }
        creditosMora[id].total += cuotaValue;
      }
    });

    Object.values(creditosMora).forEach(credito => {

      const bucket = buckets.find(b => credito.maxDiasMora >= b.min && credito.maxDiasMora <= b.max);
      if (bucket) {
        bucket.Vencido += credito.totalVencido;
        bucket.AVencer += credito.totalAVencer;
        bucket.Total += credito.total;
      }
    });

    return buckets;
  }, [data, appliedFilters.fechaCorte, filtroDueños, filtroOriginadores]);

  const colocacionesUniqueOriginadores = useMemo(() => {
    const originadores = new Set();
    colocacionesData.forEach(month => {
      Object.keys(month).forEach(key => {
        if (key.startsWith('orig_')) {
          originadores.add(key.replace('orig_', ''));
        }
      });
    });
    return Array.from(originadores).sort();
  }, [colocacionesData]);

  const composicionTableRows = useMemo(() => {
    const rows = [];
    evolutionData.forEach(month => {
      const aggByOwner = {};

      if (month.detalles) {
        month.detalles.forEach(d => {
          const originador = String(d.Originador || 'N/A').trim().toUpperCase();
          const matchOriginador = filtroOriginadores.length === 0 || filtroOriginadores.some(f => String(f).trim().toUpperCase() === originador);

          if (matchOriginador) {
            const dueño = String(d.Dueño || 'Desconocido').trim();
            if (!aggByOwner[dueño]) {
              aggByOwner[dueño] = { capital: 0, interes: 0, iva: 0, total: 0 };
            }
            aggByOwner[dueño].capital += d.capital;
            aggByOwner[dueño].interes += d.interes;
            aggByOwner[dueño].iva += d.iva;
            aggByOwner[dueño].total += d.total;
          }
        });
      }

      Object.keys(aggByOwner).sort().forEach(owner => {
        rows.push({
          periodo: month.periodo,
          dueño: owner,
          ...aggByOwner[owner]
        });
      });
    });

    return rows.reverse();
  }, [evolutionData, filtroOriginadores]);

  const moraBucketsPie = useMemo(() => {
    const totalMora = moraBuckets.reduce((acc, b) => acc + b.Total, 0);
    
    let smallSumTotal = 0;
    const smallBucketsIndices = [];
    
    moraBuckets.forEach((b, idx) => {
      if (b.Total > 0 && b.Total / totalMora < 0.05) {
        smallSumTotal += b.Total;
        smallBucketsIndices.push(idx);
      }
    });

    // We designate the LAST small bucket so all previous points are available in refs when it renders
    const designatedSmallBucketIndex = smallBucketsIndices.length > 0 ? smallBucketsIndices[smallBucketsIndices.length - 1] : -1;

    return moraBuckets.filter(b => b.Total > 0).map((b) => {
      const originalIdx = moraBuckets.indexOf(b);
      const isSmall = b.Total / totalMora < 0.05;
      const showSmallSum = originalIdx === designatedSmallBucketIndex;
      
      return {
        ...b,
        isSmall,
        showSmallSum,
        smallSumPercent: smallSumTotal / totalMora
      };
    });
  }, [moraBuckets]);

  const moraKPIs = useMemo(() => {
    let totalVencido = 0;
    let totalAVencer = 0;
    let moraTemprana = 0;
    let moraDura = 0;

    moraBuckets.forEach(b => {
      if (b.label !== 'Al día') {
        totalVencido += b.Vencido;
        totalAVencer += b.AVencer;
        if (b.max <= 90) {
          moraTemprana += b.Vencido;
        } else {
          moraDura += b.Vencido;
        }
      }
    });
    
    return {
      totalVencido,
      totalAVencer,
      moraTemprana,
      moraDura
    };
  }, [moraBuckets]);

  const smallBucketsFootnote = useMemo(() => {
    const totalMora = moraBuckets.reduce((acc, b) => acc + b.Total, 0);
    const smallBuckets = moraBuckets.filter(b => b.Total > 0 && b.Total / totalMora < 0.05);
    if (smallBuckets.length > 1) {
      const sum = smallBuckets.reduce((acc, b) => acc + b.Total, 0);
      return `El valor ${(sum / totalMora * 100).toFixed(2)}% agrupa las categorías: ${smallBuckets.map(b => b.label).join(', ')}.`;
    }
    return '';
  }, [moraBuckets]);

  const smallSlicesRef = useRef({});

  const tabKeys = [
    'situacion_patrimonial',
    'total',
    'evolucion',
    'composicion',
    'periodo',
    'colocaciones',
    'cobranzas',
    'estados',
    'morosidad'
  ];

  const handlePrevTab = () => {
    const currentIndex = tabKeys.indexOf(activeTab);
    if (currentIndex > 0) {
      setActiveTab(tabKeys[currentIndex - 1]);
    }
  };

  const handleNextTab = () => {
    const currentIndex = tabKeys.indexOf(activeTab);
    if (currentIndex < tabKeys.length - 1) {
      setActiveTab(tabKeys[currentIndex + 1]);
    }
  };

  const espPeriods = useMemo(() => {
    if (!espData || !espData.columns || !espData.data) return [];
    const allPeriods = espData.columns.filter(c => c !== "Categoria" && c !== "Detalle" && c !== "cat_order" && c !== "det_order");
    
    return allPeriods.filter(p => {
      return espData.data.some(row => Math.abs(row[p]) >= 0.01);
    });
  }, [espData]);

  const displayedEspPeriods = (isExporting && espPeriods.length > 6) ? espPeriods.slice(-6) : espPeriods;

  useEffect(() => {
    if (espPeriods.length >= 2) {
      setComparePeriodA(espPeriods[0]);
      setComparePeriodB(espPeriods[espPeriods.length - 1]);
    } else if (espPeriods.length === 1) {
      setComparePeriodA(espPeriods[0]);
      setComparePeriodB(espPeriods[0]);
    } else {
      setComparePeriodA("");
      setComparePeriodB("");
    }
  }, [espPeriods]);

  const espChartData = useMemo(() => {
    if (!espData || !espData.data) return [];
    return espPeriods.map(period => {
      let activo = 0;
      let pasivo = 0;
      let patrimonio = 0;
      espData.data.forEach(row => {
        if (row.Detalle === "Total") {
          if (row.Categoria === "") {
            patrimonio = row[period] || 0;
          }
          return; // Avoid double counting
        }
        if (row.Categoria === "Activos") activo += (row[period] || 0);
        if (row.Categoria === "Pasivos") pasivo += Math.abs(row[period] || 0); // Convert to positive for charting
      });
      return { period, Activo: activo, Pasivo: pasivo, Patrimonio: patrimonio };
    });
  }, [espData, espPeriods]);


  return (
    <div className="page-container" style={{ animation: 'fadeIn 0.5s ease' }}>
      <header className="page-header" style={{ marginBottom: '30px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Fila superior: Título y Botones de Exportación */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '15px' }}>
          <div>
            <h1 className="page-title" style={{ margin: 0 }}>Dashboard Financiero</h1>
            <p className="page-subtitle" style={{ margin: 0, marginTop: '5px' }}>Información general y estado actual de los saldos activos</p>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => exportToPDF('p')}
              disabled={exportFormat !== null}
              style={{
                padding: '10px 15px',
                borderRadius: '8px',
                border: 'none',
                background: 'var(--color-capital)',
                color: 'white',
                fontWeight: 'bold',
                cursor: exportFormat !== null ? 'not-allowed' : 'pointer',
                opacity: exportFormat !== null ? 0.7 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              📄 {exportFormat !== null ? 'Generando...' : 'Reporte Detallado'}
            </button>
            <button
              onClick={() => exportToPDF('l')}
              disabled={exportFormat !== null}
              style={{
                padding: '10px 15px',
                borderRadius: '8px',
                border: 'none',
                background: 'var(--color-total)',
                color: 'white',
                fontWeight: 'bold',
                cursor: exportFormat !== null ? 'not-allowed' : 'pointer',
                opacity: exportFormat !== null ? 0.7 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              📊 {exportFormat !== null ? 'Generando...' : 'Reporte Gráfico'}
            </button>
          </div>
        </div>

        {/* Fila inferior: Filtros y Botón de Aplicar */}
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
            <DatePicker
              id="fechaCorte"
              selected={fechaCorteDate}
              onChange={handleDateChange}
              dateFormat="dd/MM/yyyy"
              locale={es}
              customInput={
                <input
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: '1px solid rgba(255,255,255,0.1)',
                    background: 'rgba(0,0,0,0.2)',
                    color: 'var(--text-primary)',
                    colorScheme: 'dark',
                    width: '120px',
                    cursor: 'pointer'
                  }}
                />
              }
            />
          </div>
          <button
            onClick={() => {
              startTransition(() => {
                setAppliedFilters({
                  fechaCorte: fechaCorte,
                  nPeriodosEsp: nPeriodosEsp,
                  frecuenciaEsp: frecuenciaEsp,
                  tasaDescuento: tasaDescuento
                });
              });
            }}
            style={{
              padding: '10px 15px',
              borderRadius: '8px',
              border: '1px solid var(--color-total)',
              background: 'rgba(33, 150, 243, 0.1)',
              color: 'var(--color-total)',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-total)'; e.currentTarget.style.color = 'white'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(33, 150, 243, 0.1)'; e.currentTarget.style.color = 'var(--color-total)'; }}
          >
            Aplicar Filtros
          </button>
        </div>
      </header>

      {(loading || espLoading || isPending) ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '100px 0' }}>
          <div className="loading-spinner"></div>
          <span style={{ marginLeft: '10px' }}>Cargando información de la cartera...</span>
        </div>
      ) : error ? (
        <div className="alert error" style={{ marginTop: '20px' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          {error}
        </div>
      ) : (
        <>
          {/* Filtros y Navegación */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '20px' }}>
        
        {/* Filtros Izquierda */}
        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>

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
                    <input type="checkbox" checked={filtroDueños.length === 0} onChange={() => startTransition(() => setFiltroDueños([]))} />
                    <span style={{ opacity: filtroDueños.length === 0 ? 1 : 0.6 }}>Todos</span>
                  </label>
                  {uniqueDueños.filter(d => d !== 'Todos').map(d => (
                    <label key={d} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', cursor: 'pointer', fontSize: '0.9rem' }}>
                      <input
                        type="checkbox"
                        checked={filtroDueños.includes(d)}
                        onChange={(e) => {
                          startTransition(() => {
                            if (e.target.checked) setFiltroDueños([...filtroDueños, d]);
                            else setFiltroDueños(filtroDueños.filter(item => item !== d));
                          });
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
                    <input type="checkbox" checked={filtroOriginadores.length === 0} onChange={() => startTransition(() => setFiltroOriginadores([]))} />
                    <span style={{ opacity: filtroOriginadores.length === 0 ? 1 : 0.6 }}>Todos</span>
                  </label>
                  {uniqueOriginadores.filter(o => o !== 'Todos').map(o => (
                    <label key={o} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', cursor: 'pointer', fontSize: '0.9rem' }}>
                      <input
                        type="checkbox"
                        checked={filtroOriginadores.includes(o)}
                        onChange={(e) => {
                          startTransition(() => {
                            if (e.target.checked) setFiltroOriginadores([...filtroOriginadores, o]);
                            else setFiltroOriginadores(filtroOriginadores.filter(item => item !== o));
                          });
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

        {/* Navegación Derecha */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handlePrevTab}
            disabled={tabKeys.indexOf(activeTab) === 0}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(0,0,0,0.2)',
              color: tabKeys.indexOf(activeTab) === 0 ? 'rgba(255,255,255,0.3)' : 'white',
              cursor: tabKeys.indexOf(activeTab) === 0 ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
              transition: 'background 0.2s, color 0.2s'
            }}
            title="Hoja Anterior"
          >
            ←
          </button>
          <button
            onClick={handleNextTab}
            disabled={tabKeys.indexOf(activeTab) === tabKeys.length - 1}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(0,0,0,0.2)',
              color: tabKeys.indexOf(activeTab) === tabKeys.length - 1 ? 'rgba(255,255,255,0.3)' : 'white',
              cursor: tabKeys.indexOf(activeTab) === tabKeys.length - 1 ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
              transition: 'background 0.2s, color 0.2s'
            }}
            title="Siguiente Hoja"
          >
            →
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '15px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <button
          onClick={() => setActiveTab('situacion_patrimonial')}
          style={{
            padding: '10px 20px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'situacion_patrimonial' ? 'var(--color-total)' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'situacion_patrimonial' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Estado de Situación Patrimonial
        </button>
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
          Resumen Cartera
        </button>
        <button
          onClick={() => setActiveTab('evolucion')}
          style={{
            padding: '10px 20px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'evolucion' ? 'var(--color-total)' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'evolucion' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Evolución Cartera
        </button>
        <button
          onClick={() => setActiveTab('composicion')}
          style={{
            padding: '10px 20px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'composicion' ? 'var(--color-total)' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'composicion' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Composición Cartera
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
          Caída de Cuotas
        </button>
        <button
          onClick={() => setActiveTab('colocaciones')}
          style={{
            padding: '10px 20px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'colocaciones' ? 'var(--color-total)' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'colocaciones' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Colocaciones Cartera
        </button>
        <button
          onClick={() => setActiveTab('cobranzas')}
          style={{
            padding: '10px 20px',
            borderRadius: '8px',
            border: 'none',
            background: activeTab === 'cobranzas' ? 'var(--color-total)' : 'rgba(255,255,255,0.05)',
            color: activeTab === 'cobranzas' ? 'white' : 'var(--text-secondary)',
            cursor: 'pointer',
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          Cobranzas Cartera
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
          Estados Cartera
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
          Morosidad Cartera
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

      {(activeTab === 'situacion_patrimonial' || isExporting) && (
        <div id="export-tab-situacion">
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', marginBottom: '30px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: '600', margin: 0 }}>Estado de Situación Patrimonial</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <label style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Frecuencia:</label>
                  <select
                    value={frecuenciaEsp}
                    onChange={(e) => setFrecuenciaEsp(Number(e.target.value))}
                    style={{
                      padding: '6px 10px',
                      borderRadius: '6px',
                      border: '1px solid rgba(255,255,255,0.1)',
                      background: 'rgba(0,0,0,0.2)',
                      color: 'var(--text-primary)',
                      cursor: 'pointer'
                    }}
                  >
                    <option value={1}>Mensual (1m)</option>
                    <option value={2}>Bimestral (2m)</option>
                    <option value={3}>Trimestral (3m)</option>
                    <option value={6}>Semestral (6m)</option>
                    <option value={12}>Anual (12m)</option>
                  </select>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <label style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Periodos:</label>
                  <select
                    value={nPeriodosEsp}
                    onChange={(e) => setNPeriodosEsp(Number(e.target.value))}
                    style={{
                      padding: '6px 10px',
                      borderRadius: '6px',
                      border: '1px solid rgba(255,255,255,0.1)',
                      background: 'rgba(0,0,0,0.2)',
                      color: 'var(--text-primary)',
                      cursor: 'pointer'
                    }}
                  >
                    <option value={2}>2</option>
                    <option value={3}>3</option>
                    <option value={4}>4</option>
                    <option value={5}>5</option>
                    <option value={6}>6</option>
                    <option value={12}>12</option>
                    <option value={24}>24</option>
                  </select>
                </div>
              </div>
            </div>
            
            {!espData || !espData.data ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
                <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
                  No hay datos disponibles para el Estado de Situación Patrimonial.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
                {/* Gráfico Comparativo Activo vs Pasivo */}
                <div>
                  <h3 style={{ fontSize: '1rem', marginBottom: '15px', color: 'var(--text-secondary)' }}>Evolución Activo vs Pasivo</h3>
                  <div style={{ height: 300, width: '100%' }}>
                    <ResponsiveContainer>
                      <ComposedChart data={espChartData} margin={{ top: 20, right: 30, left: 40, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis dataKey="period" stroke="var(--text-secondary)" tickFormatter={(val) => val.split(' - ')[0]} />
                        <YAxis width={80} stroke="var(--text-secondary)" tickFormatter={(value) => `$ ${new Intl.NumberFormat('es-AR', { notation: 'compact', compactDisplay: 'short' }).format(value)}`} />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'white' }}
                          formatter={(value) => formatCurrency(value)}
                        />
                        <Legend wrapperStyle={{ paddingTop: '10px' }} />
                        <Bar isAnimationActive={!isExporting} dataKey="Activo" fill="var(--color-capital)" radius={[4, 4, 0, 0]} />
                        <Bar isAnimationActive={!isExporting} dataKey="Pasivo" fill="var(--color-valoractual)" radius={[4, 4, 0, 0]} />
                        <Line isAnimationActive={!isExporting} type="monotone" dataKey="Patrimonio" stroke={isExporting ? "#ca8a04" : "#facc15"} strokeWidth={3} dot={{ r: 4, strokeWidth: 2, fill: 'var(--bg-card)' }} activeDot={{ r: 6 }} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Tabla Detallada */}
                <div style={{ overflowX: 'auto' }}>
                  <h3 style={{ fontSize: '1rem', marginBottom: '15px', color: isExporting ? '#000000' : 'var(--text-secondary)' }}>Detalle Patrimonial</h3>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid rgba(255,255,255,0.1)' }}>
                        <th style={{ padding: '8px 12px', color: isExporting ? '#000000' : 'var(--text-secondary)', fontWeight: '600', fontSize: '0.85rem', minWidth: '180px' }}>Detalle</th>
                        {displayedEspPeriods.map(p => {
                          const parts = p.split(' - ');
                          const datePart = parts[0];
                          const tnaPart = parts[1] || '';
                          
                          return (
                            <th key={p} style={{ padding: '8px 4px', color: isExporting ? '#000000' : 'var(--text-secondary)', fontWeight: '600', textAlign: 'center', verticalAlign: 'bottom', fontSize: '0.85rem' }}>
                              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', lineHeight: '1.2' }}>
                                <span>{datePart}</span>
                                {tnaPart && <span style={{ fontSize: '0.8em', opacity: 0.7, fontWeight: 'normal' }}>{tnaPart}</span>}
                              </div>
                            </th>
                          );
                        })}
                        {espPeriods.length >= 2 && (
                          <th style={{ padding: '8px 4px', textAlign: 'center', minWidth: '130px' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px' }}>
                              <span style={{ color: 'var(--color-capital)', fontWeight: 'bold' }}>Variación</span>
                              <div style={{ display: 'flex', gap: '5px', alignItems: 'center', justifyContent: 'center' }}>
                                <select 
                                  value={comparePeriodA} 
                                  onChange={(e) => setComparePeriodA(e.target.value)}
                                  style={{ padding: '2px 4px', fontSize: '0.8rem', background: 'rgba(0,0,0,0.3)', color: 'var(--text-secondary)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '4px' }}
                                >
                                  {espPeriods.map(p => <option key={p} value={p}>{p.split(' ')[0]}</option>)}
                                </select>
                                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>vs</span>
                                <select 
                                  value={comparePeriodB} 
                                  onChange={(e) => setComparePeriodB(e.target.value)}
                                  style={{ padding: '2px 4px', fontSize: '0.8rem', background: 'rgba(0,0,0,0.3)', color: 'var(--text-primary)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '4px' }}
                                >
                                  {espPeriods.map(p => <option key={p} value={p}>{p.split(' ')[0]}</option>)}
                                </select>
                              </div>
                            </div>
                          </th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {(() => {
                        const filteredData = espData.data.filter(row => {
                          if (isExporting && exportFormat === 'l' && row.Detalle !== "Total") return false;
                          if (row.Categoria === "" && row.Detalle === "Total") return true;
                          return espPeriods.some(p => Math.abs(row[p]) >= 0.01);
                        });

                        return filteredData.map((row, idx) => {
                          const isTotalGeneral = row.Categoria === "" && row.Detalle === "Total";
                          const isSubTotal = row.Detalle === "Total" && !isTotalGeneral;
                          const isFirstOfCategory = (isExporting && exportFormat === 'l') ? false : (idx === 0 || filteredData[idx - 1].Categoria !== row.Categoria);
                          
                          return (
                            <React.Fragment key={idx}>
                            {isFirstOfCategory && row.Categoria !== "" && (
                              <tr style={{ background: isExporting ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.08)' }}>
                                <td colSpan={displayedEspPeriods.length >= 2 ? displayedEspPeriods.length + 2 : displayedEspPeriods.length + 1} style={{ padding: '10px 12px', color: isExporting ? '#000000' : 'var(--text-primary)', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px', fontSize: '0.85rem' }}>
                                  {row.Categoria}
                                </td>
                              </tr>
                            )}
                            <tr style={{ 
                              borderBottom: isTotalGeneral ? '2px solid rgba(250, 204, 21, 0.5)' : (isSubTotal ? '2px solid rgba(255,255,255,0.1)' : '1px solid rgba(255,255,255,0.03)'),
                              background: isTotalGeneral ? (isExporting ? '#fef08a' : 'rgba(250, 204, 21, 0.15)') : (isSubTotal ? 'rgba(255,255,255,0.02)' : 'transparent'),
                              fontWeight: isSubTotal || isTotalGeneral ? 'bold' : 'normal',
                              color: isTotalGeneral ? (isExporting ? '#000000' : '#facc15') : 'inherit'
                            }} className={isTotalGeneral ? "" : "table-row-hover"}>
                              <td style={{ padding: '8px 12px 8px 30px', color: isTotalGeneral ? (isExporting ? '#000000' : '#facc15') : (isExporting ? '#000000' : 'var(--text-primary)'), fontSize: '0.85rem' }}>
                                {isTotalGeneral ? 'PATRIMONIO NETO' : (isExporting && exportFormat === 'l' && isSubTotal ? `TOTAL ${row.Categoria.toUpperCase()}` : row.Detalle)}
                              </td>
                              {displayedEspPeriods.map(p => (
                                <td key={p} style={{ padding: '6px 4px', textAlign: 'right', color: isTotalGeneral ? (isExporting ? '#000000' : '#facc15') : (isExporting ? '#000000' : (row[p] < 0 ? 'var(--color-valoractual)' : 'var(--text-primary)')), fontSize: '0.8rem' }}>
                                  {formatCurrency(row[p])}
                                </td>
                              ))}
                              {espPeriods.length >= 2 && (
                                <td style={{ padding: '6px 4px', textAlign: 'right', fontWeight: 'bold', background: 'rgba(255,255,255,0.02)', fontSize: '0.8rem' }}>
                                  {(() => {
                                    const valA = row[comparePeriodA] || 0;
                                    const valB = row[comparePeriodB] || 0;
                                    const diff = valB - valA;
                                    
                                    if (diff === 0) return <span style={{ color: isTotalGeneral ? (isExporting ? '#000000' : '#facc15') : 'var(--text-secondary)' }}>-</span>;
                                    
                                    const diffColor = diff > 0 ? '#10b981' : '#ef4444';
                                    const pct = valA !== 0 ? ((diff / Math.abs(valA)) * 100).toFixed(1) : null;
                                    
                                    return (
                                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', lineHeight: '1.2' }}>
                                        <span style={{ color: diffColor }}>{diff > 0 ? '+' : ''}{formatCurrency(diff)}</span>
                                        {pct && (
                                          <span style={{ fontSize: '0.75rem', color: diffColor, opacity: 0.8 }}>
                                            {diff > 0 ? '+' : ''}{pct}%
                                          </span>
                                        )}
                                      </div>
                                    );
                                  })()}
                                </td>
                              )}
                            </tr>
                          </React.Fragment>
                        );
                      });
                      })()}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
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
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '1px' }}>Valor Actual ({appliedFilters.tasaDescuento}%)</span>
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

      {(activeTab === 'evolucion' || isExporting) && (
        <div id="export-tab-evolucion">
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '20px' }}>
            {(() => {
              const len = filteredEvolutionData.length;
              const lastEvol = len > 0 ? filteredEvolutionData[len - 1] : { capital: 0, interes: 0, iva: 0, total: 0 };
              const prevEvol = len > 1 ? filteredEvolutionData[len - 2] : { capital: 0, interes: 0, iva: 0, total: 0 };
              
              const calcGrowth = (curr, prev) => {
                const diff = curr - prev;
                if (diff === 0 || prev === 0) return { diff: 0, pct: 0, color: 'var(--text-secondary)', sign: '' };
                const pct = (diff / Math.abs(prev)) * 100;
                return {
                  diff,
                  pct,
                  color: diff > 0 ? '#10b981' : '#ef4444',
                  sign: diff > 0 ? '+' : ''
                };
              };

              const growths = {
                total: calcGrowth(lastEvol.total, prevEvol.total),
                capital: calcGrowth(lastEvol.capital, prevEvol.capital),
                interes: calcGrowth(lastEvol.interes, prevEvol.interes),
                iva: calcGrowth(lastEvol.iva, prevEvol.iva)
              };

              const renderKPI = (title, growth, borderColor) => (
                <div className="glass-panel" style={{ flex: 1, minWidth: '200px', padding: '20px', borderRadius: '12px', borderTop: `4px solid ${borderColor}`, textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px' }}>CRECIMIENTO {title}</div>
                  <div style={{ color: growth.color, fontSize: '1.8rem', fontWeight: 'bold' }}>
                    {growth.diff === 0 ? '-' : `${growth.sign}${formatCurrency(growth.diff)}`}
                  </div>
                  {len > 1 && growth.diff !== 0 && (
                    <div style={{ color: growth.color, fontSize: '0.85rem', marginTop: '8px', fontWeight: '500' }}>
                      {growth.sign}{growth.pct.toFixed(1)}% vs mes anterior
                    </div>
                  )}
                  {len <= 1 && (
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '8px' }}>
                      Sin datos previos
                    </div>
                  )}
                </div>
              );

              return (
                <>
                  {renderKPI('TOTAL', growths.total, 'var(--color-total)')}
                  {renderKPI('CAPITAL', growths.capital, 'var(--color-capital)')}
                  {renderKPI('INTERÉS', growths.interes, 'var(--color-interes)')}
                  {renderKPI('IVA', growths.iva, 'var(--color-iva)')}
                </>
              );
            })()}
          </div>
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', marginBottom: '30px', height: '400px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Evolución de Cartera (12 Meses)</h2>
            {filteredEvolutionData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>Cargando evolución histórica...</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={filteredEvolutionData}
                  margin={{ top: 10, right: 30, left: 20, bottom: 25 }}
                >
                  <defs>
                    <linearGradient id="colorCapital" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-capital)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="var(--color-capital)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorInteres" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-interes)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="var(--color-interes)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorIva" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-iva)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="var(--color-iva)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="periodo" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} />
                  <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`} />
                  <Tooltip
                    formatter={(value) => formatCurrency(value)}
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'white' }}
                    itemStyle={{ color: 'white' }}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  <Area isAnimationActive={!isExporting} type="monotone" dataKey="capital" stackId="1" stroke="var(--color-capital)" fillOpacity={1} fill="url(#colorCapital)" name="Capital" />
                  <Area isAnimationActive={!isExporting} type="monotone" dataKey="interes" stackId="1" stroke="var(--color-interes)" fillOpacity={1} fill="url(#colorInteres)" name="Interés" />
                  <Area isAnimationActive={!isExporting} type="monotone" dataKey="iva" stackId="1" stroke="var(--color-iva)" fillOpacity={1} fill="url(#colorIva)" name="IVA" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="glass-panel" style={{ display: exportFormat === 'l' ? 'none' : 'block', padding: '25px', borderRadius: '12px', marginTop: '20px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Detalle Histórico (12 Meses)</h2>
            {filteredEvolutionData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos históricos disponibles.</p>
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
                    {[...filteredEvolutionData].reverse().map((row, idx) => (
                      <tr key={idx} style={{
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        transition: 'background-color 0.2s',
                      }} className="table-row-hover">
                        <td style={{ padding: '15px 10px', fontWeight: '500' }}>{row.periodo}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.capital)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.interes)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-capint)' }}>{formatCurrency(row.capital + row.interes)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.iva)}</td>
                        <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-total)' }}>{formatCurrency(row.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {(activeTab === 'composicion' || isExporting) && (
        <div id="export-tab-composicion">
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '20px' }}>
            {(() => {
              const lastPeriod = filteredEvolutionData.length > 0 ? filteredEvolutionData[filteredEvolutionData.length - 1].periodo : null;
              const currentOwnersRows = composicionTableRows.filter(r => r.periodo === lastPeriod && r.dueño !== 'Total');
              return currentOwnersRows.map(row => (
                <div key={row.dueño} className="glass-panel" style={{ flex: 1, minWidth: '200px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-capital)', textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px', textTransform: 'uppercase' }}>{row.dueño}</div>
                  <div style={{ color: 'var(--text-primary)', fontSize: '1.5rem', fontWeight: 'bold' }}>{formatCurrency(row.total)}</div>
                </div>
              ));
            })()}
          </div>
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', marginBottom: '30px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Cartera por Dueño (Capital y %)</h2>
            {filteredEvolutionData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos disponibles.</p>
            ) : (
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={filteredEvolutionData} margin={{ top: 10, right: 30, left: 20, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="periodo" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickMargin={10} />
                  <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickFormatter={(val) => `$${(val / 1000000).toFixed(1)}M`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                    formatter={(value, name, props) => {
                      const pct = props.payload[`owner_${name}`];
                      const pctStr = pct ? pct.toFixed(1) : '0.0';
                      const valStr = (value / 1000000).toFixed(1);
                      return [`${pctStr}% - $${valStr}M`, name];
                    }}
                    labelFormatter={(label) => `Período: ${label}`}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  {evolutionUniqueDueños.map((dueño, index) => (
                    <Bar
                      isAnimationActive={!isExporting}
                      key={dueño}
                      dataKey={`ownerRaw_${dueño}`}
                      name={dueño}
                      stackId="a"
                      fill={CHART_COLORS[index % CHART_COLORS.length]}
                    >
                      <LabelList
                        dataKey={`owner_${dueño}`}
                        position="inside"
                        fill="#fff"
                        formatter={(val) => val > 5 ? `${val.toFixed(1)}%` : ''}
                        style={{ fontSize: 12, fontWeight: 'bold' }}
                      />
                    </Bar>
                  ))}
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="glass-panel" style={{ display: exportFormat === 'l' ? 'none' : 'block', padding: '25px', borderRadius: '12px', marginTop: '20px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Detalle por Período y Dueño</h2>
            {composicionTableRows.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos disponibles.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                      <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>Período</th>
                      <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>Dueño</th>
                      <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>Capital</th>
                      <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>Interés</th>
                      <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>IVA</th>
                      <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {composicionTableRows.map((row, idx) => (
                      <tr key={`${row.periodo}-${row.dueño}-${idx}`} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                        <td style={{ padding: '12px', color: 'var(--text-primary)' }}>{row.periodo}</td>
                        <td style={{ padding: '12px', color: 'var(--text-primary)' }}>{row.dueño}</td>
                        <td style={{ padding: '12px', textAlign: 'right', color: 'var(--color-capital)', fontFamily: 'monospace' }}>{formatCurrency(row.capital)}</td>
                        <td style={{ padding: '12px', textAlign: 'right', color: 'var(--color-interes)', fontFamily: 'monospace' }}>{formatCurrency(row.interes)}</td>
                        <td style={{ padding: '12px', textAlign: 'right', color: 'var(--color-iva)', fontFamily: 'monospace' }}>{formatCurrency(row.iva)}</td>
                        <td style={{ padding: '12px', textAlign: 'right', color: 'var(--color-total)', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatCurrency(row.total)}</td>
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
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '20px' }}>
            {(() => {
              const proxVenc = periodData.length > 0 ? periodData[0] : { Capital: 0, Interés: 0, IVA: 0, Total: 0 };
              return (
                <>
                  <div className="glass-panel" style={{ flex: 1, minWidth: '200px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-total)', textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px' }}>TOTAL PRÓXIMO VENCIMIENTO</div>
                    <div style={{ color: 'var(--text-primary)', fontSize: '1.8rem', fontWeight: 'bold' }}>{formatCurrency(proxVenc.Total)}</div>
                  </div>
                  <div className="glass-panel" style={{ flex: 1, minWidth: '200px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-capital)', textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px' }}>CAPITAL PRÓXIMO VENCIMIENTO</div>
                    <div style={{ color: 'var(--text-primary)', fontSize: '1.8rem', fontWeight: 'bold' }}>{formatCurrency(proxVenc.Capital)}</div>
                  </div>
                  <div className="glass-panel" style={{ flex: 1, minWidth: '200px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-interes)', textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px' }}>INTERÉS PRÓXIMO VENCIMIENTO</div>
                    <div style={{ color: 'var(--text-primary)', fontSize: '1.8rem', fontWeight: 'bold' }}>{formatCurrency(proxVenc['Interés'] || proxVenc.Interes || 0)}</div>
                  </div>
                  <div className="glass-panel" style={{ flex: 1, minWidth: '200px', padding: '20px', borderRadius: '12px', borderTop: '4px solid var(--color-iva)', textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px' }}>IVA PRÓXIMO VENCIMIENTO</div>
                    <div style={{ color: 'var(--text-primary)', fontSize: '1.8rem', fontWeight: 'bold' }}>{formatCurrency(proxVenc.IVA)}</div>
                  </div>
                </>
              );
            })()}
          </div>
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', marginBottom: '30px', height: '400px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Proyección de Vencimientos</h2>
            {periodData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay vencimientos futuros registrados.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={periodData}
                  margin={{ top: 10, right: 30, left: 20, bottom: isExporting ? 45 : 25 }}
                  barCategoryGap="20%"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis 
                    dataKey="Periodo" 
                    stroke="var(--text-secondary)" 
                    tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} 
                    interval={isExporting ? 0 : 'preserveEnd'} 
                    angle={isExporting ? -45 : 0} 
                    textAnchor={isExporting ? 'end' : 'middle'} 
                    height={isExporting ? 60 : 30}
                  />
                  <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`} />
                  <Tooltip
                    formatter={(value) => formatCurrency(value)}
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'white' }}
                    itemStyle={{ color: 'white' }}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  <Bar isAnimationActive={!isExporting} dataKey="Capital" stackId="a" fill="var(--color-capital)" name="Capital" />
                  <Bar isAnimationActive={!isExporting} dataKey="Interés" stackId="a" fill="var(--color-interes)" name="Interés" />
                  <Bar isAnimationActive={!isExporting} dataKey="IVA" stackId="a" fill="var(--color-iva)" name="IVA" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="glass-panel" style={{ display: exportFormat === 'l' ? 'none' : 'block', padding: '25px', borderRadius: '12px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Detalle por Período (Actual y Futuros)</h2>
            {periodData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay vencimientos futuros registrados.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                      <th style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontWeight: '500', fontSize: '0.95rem' }}>Período</th>
                      <th style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right', fontSize: '0.95rem' }}>Capital</th>
                      <th style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right', fontSize: '0.95rem' }}>Interés</th>
                      <th style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right', fontSize: '0.95rem' }}>Cap + Int</th>
                      <th style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right', fontSize: '0.95rem' }}>IVA</th>
                      <th style={{ padding: '8px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right', fontSize: '0.95rem' }}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {periodData.map((row, idx) => (
                      <tr key={idx} style={{
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        transition: 'background-color 0.2s',
                        fontSize: '0.9rem'
                      }} className="table-row-hover">
                        <td style={{ padding: '6px 10px', fontWeight: '500' }}>{row.Periodo}</td>
                        <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.Capital)}</td>
                        <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row['Interés'])}</td>
                        <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-capint)' }}>{formatCurrency(row.Capital + row['Interés'])}</td>
                        <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(row.IVA)}</td>
                        <td style={{ padding: '6px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-total)' }}>{formatCurrency(row.Total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {(activeTab === 'colocaciones' || isExporting) && (
        <div id="export-tab-colocaciones">
          <div style={{ display: 'flex', gap: '20px', flexWrap: 'nowrap', marginBottom: '30px' }}>
            <div className="glass-panel" style={{ flex: 3, minWidth: '0', padding: '25px', borderRadius: '12px' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Volumen de Colocaciones (Capital Vendido por Período)</h2>
              {colocacionesData.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos de originación en este rango.</p>
              ) : (
                <ResponsiveContainer width="100%" height={400}>
                  <ComposedChart data={colocacionesData} margin={{ top: 10, right: 30, left: 20, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="periodo" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickMargin={10} />
                  <YAxis yAxisId="left" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickFormatter={(val) => `$${(val / 1000000).toFixed(1)}M`} />
                  <YAxis yAxisId="right" orientation="right" stroke="var(--color-total)" tick={{ fill: 'var(--color-total)', fontSize: 12 }} tickFormatter={(val) => `$${(val / 1000000).toFixed(1)}M`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                    formatter={(value, name, props) => {
                      if (name === 'Monto Generado') {
                        return [`$${(value / 1000000).toFixed(2)}M`, name];
                      }
                      const pct = props.payload[`origPct_${name}`];
                      const pctStr = pct ? pct.toFixed(1) : '0.0';
                      const valStr = (value / 1000000).toFixed(1);
                      return [`${pctStr}% - $${valStr}M`, name];
                    }}
                    labelFormatter={(label) => `Período de Emisión: ${label}`}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  {colocacionesUniqueOriginadores.map((originador, index) => (
                    <Bar
                      yAxisId="left"
                      isAnimationActive={!isExporting}
                      key={originador}
                      dataKey={`orig_${originador}`}
                      name={originador}
                      stackId="a"
                      fill={CHART_COLORS[(index + 2) % CHART_COLORS.length]}
                    >
                      <LabelList
                        dataKey={`origPct_${originador}`}
                        position="inside"
                        fill="#fff"
                        formatter={(val) => val > 5 ? `${val.toFixed(1)}%` : ''}
                        style={{ fontSize: 12, fontWeight: 'bold' }}
                      />
                    </Bar>
                  ))}
                  <Line isAnimationActive={!isExporting} yAxisId="right" type="monotone" dataKey="totalGenerado" stroke="var(--color-total)" strokeWidth={3} name="Monto Generado" dot={{ r: 4 }} activeDot={{ r: 6 }} />
                </ComposedChart>
              </ResponsiveContainer>
              )}
            </div>
            
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '15px', minWidth: '250px', justifyContent: 'center' }}>
              <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '5px' }}>
                Último período {colocacionesData.length > 0 ? `(${colocacionesData[colocacionesData.length - 1].periodo})` : ''}
              </div>
              
              {(() => {
                const ultimoPeriodo = colocacionesData.length > 0 ? colocacionesData[colocacionesData.length - 1] : {};
                const totalCapital = ultimoPeriodo.totalColocado || 0;
                const totalMonto = ultimoPeriodo.totalGenerado || 0;
                if (colocacionesData.length === 0) return null;
                return (
                  <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px', borderLeft: `4px solid var(--color-total)`, background: 'linear-gradient(135deg, rgba(33, 150, 243, 0.1), rgba(0,0,0,0))' }}>
                    <div style={{ color: 'var(--text-primary)', fontSize: '1rem', marginBottom: '8px', fontWeight: 'bold', textTransform: 'uppercase' }}>TOTAL DEL MES</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                      <div>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Capital Total: </span>
                        <span style={{ color: 'var(--color-capital)', fontSize: '1.2rem', fontWeight: 'bold' }}>{formatCurrency(totalCapital)}</span>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Monto Total: </span>
                        <span style={{ color: 'var(--color-total)', fontSize: '1.2rem', fontWeight: 'bold' }}>{formatCurrency(totalMonto)}</span>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {colocacionesUniqueOriginadores.map((originador, index) => {
                const ultimoPeriodo = colocacionesData.length > 0 ? colocacionesData[colocacionesData.length - 1] : {};
                const totalColocado = ultimoPeriodo[`orig_${originador}`] || 0;
                const totalGenerado = ultimoPeriodo[`origGen_${originador}`] || 0;
                return (
                  <div key={originador} className="glass-panel" style={{ padding: '20px', borderRadius: '12px', borderLeft: `4px solid ${CHART_COLORS[(index + 2) % CHART_COLORS.length]}` }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '8px', textTransform: 'uppercase' }}>{originador}</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                      <div>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Capital: </span>
                        <span style={{ color: 'var(--color-capital)', fontSize: '1.1rem', fontWeight: 'bold' }}>{formatCurrency(totalColocado)}</span>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Monto Total: </span>
                        <span style={{ color: 'var(--color-total)', fontSize: '1.1rem', fontWeight: 'bold' }}>{formatCurrency(totalGenerado)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="glass-panel" style={{ display: exportFormat === 'l' ? 'none' : 'block', padding: '25px', borderRadius: '12px', marginTop: '20px', marginBottom: '30px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Detalle de Originaciones por Período</h2>
            {colocacionesData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos disponibles.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                      <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>Período</th>
                      <th style={{ textAlign: 'left', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>Socio Originador</th>
                      <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>Volumen de Colocación</th>
                      <th style={{ textAlign: 'right', padding: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>% del Período</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...colocacionesData].reverse().map((row, idx) => (
                      <React.Fragment key={idx}>
                        {colocacionesUniqueOriginadores.map(originador => {
                          const val = row[`orig_${originador}`];
                          if (!val) return null;
                          const pct = row[`origPct_${originador}`];
                          return (
                            <tr key={`${row.periodo}-${originador}`} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }} className="table-row-hover">
                              <td style={{ padding: '12px' }}>{row.periodo}</td>
                              <td style={{ padding: '12px', fontWeight: '500', color: 'var(--text-primary)' }}>{originador}</td>
                              <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace' }}>{formatCurrency(val)}</td>
                              <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{pct.toFixed(2)}%</td>
                            </tr>
                          );
                        })}
                        <tr style={{ borderBottom: '2px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.02)' }}>
                          <td colSpan={2} style={{ padding: '8px 12px', fontWeight: '600', color: 'var(--text-secondary)' }}>TOTAL {row.periodo}</td>
                          <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace' }}>{formatCurrency(row.totalColocado)}</td>
                          <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>100%</td>
                        </tr>
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {(activeTab === 'cobranzas' || isExporting) && (
        <div id="export-tab-cobranzas" style={{ display: 'grid', gridTemplateColumns: isExporting ? 'repeat(auto-fit, minmax(450px, 1fr))' : '1fr', gap: '25px', marginBottom: '30px' }}>
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', height: '400px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Evolución de Cobranzas (Últimos 12 Meses)</h2>
            {filteredCobranzasEvolutionData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>Cargando evolución de cobranzas...</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={filteredCobranzasEvolutionData}
                  margin={{ top: 10, right: 30, left: 20, bottom: 25 }}
                >
                  <defs>
                    <linearGradient id="colorCobrCapital" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-capital)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="var(--color-capital)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorCobrInteres" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-interes)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="var(--color-interes)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorCobrIva" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-iva)" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="var(--color-iva)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="periodo" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} />
                  <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)' }} tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`} />
                  <Tooltip
                    formatter={(value) => formatCurrency(value)}
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'white' }}
                    itemStyle={{ color: 'white' }}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  <Area isAnimationActive={!isExporting} type="monotone" dataKey="capital" stackId="1" stroke="var(--color-capital)" fillOpacity={1} fill="url(#colorCobrCapital)" name="Capital Cobrado" />
                  <Area isAnimationActive={!isExporting} type="monotone" dataKey="interes" stackId="1" stroke="var(--color-interes)" fillOpacity={1} fill="url(#colorCobrInteres)" name="Interés Cobrado" />
                  <Area isAnimationActive={!isExporting} type="monotone" dataKey="iva" stackId="1" stroke="var(--color-iva)" fillOpacity={1} fill="url(#colorCobrIva)" name="IVA Cobrado" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', height: '400px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Cobranzas por Tipo</h2>
            {filteredCobranzasEvolutionData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos de cobranzas disponibles.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={filteredCobranzasEvolutionData} margin={{ top: 10, right: 30, left: 20, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="periodo" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickMargin={10} />
                  <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickFormatter={(val) => `$${(val / 1000000).toFixed(1)}M`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                    formatter={(value, name) => {
                      const valStr = (value / 1000000).toFixed(1);
                      return [`$${valStr}M`, name];
                    }}
                    labelFormatter={(label) => `Período: ${label}`}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  {cobranzasUniqueTipos.map((tipo, index) => (
                    <Bar
                      isAnimationActive={!isExporting}
                      key={tipo}
                      dataKey={`tipoRaw_${tipo}`}
                      name={tipo}
                      stackId="a"
                      fill={CHART_COLORS[index % CHART_COLORS.length]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          
          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', height: '400px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Real Cobrado vs Caída Teórica</h2>
            {filteredCobranzasEvolutionData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos disponibles.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={filteredCobranzasEvolutionData} margin={{ top: 10, right: 30, left: 20, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="periodo" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickMargin={10} xAxisId={0} />
                  <XAxis dataKey="periodo" xAxisId={1} hide />
                  <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickFormatter={(val) => `$${(val / 1000000).toFixed(1)}M`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                    formatter={(value, name) => {
                      const valStr = (value / 1000000).toFixed(1);
                      return [`$${valStr}M`, name];
                    }}
                    labelFormatter={(label) => `Período: ${label}`}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  <Bar
                    isAnimationActive={!isExporting}
                    dataKey="totalTeorico"
                    name="Caída Teórica"
                    fill="#ef4444"
                    xAxisId={0}
                  />
                  <Bar
                    isAnimationActive={!isExporting}
                    dataKey="totalMismoPeriodo"
                    name="Total Cobrado"
                    fill="var(--color-capital)"
                    xAxisId={1}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', height: '400px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Recupero de Mora</h2>
            {filteredCobranzasEvolutionData.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No hay datos disponibles.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={filteredCobranzasEvolutionData} margin={{ top: 10, right: 30, left: 20, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                  <XAxis dataKey="periodo" stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickMargin={10} />
                  <YAxis stroke="var(--text-secondary)" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} tickFormatter={(val) => `$${(val / 1000000).toFixed(1)}M`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                    itemStyle={{ color: '#fff' }}
                    formatter={(value, name) => {
                      const valStr = (value / 1000000).toFixed(1);
                      return [`$${valStr}M`, name];
                    }}
                    labelFormatter={(label) => `Período: ${label}`}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  <Bar
                    isAnimationActive={!isExporting}
                    dataKey="recuperoMora"
                    name="Recupero de Mora"
                    fill="#f97316"
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      )}

      {(activeTab === 'estados' || isExporting) && (
        <div id="export-tab-estados">
          <div style={{ display: 'grid', gridTemplateColumns: isExporting ? 'repeat(auto-fit, minmax(450px, 1fr))' : '1fr', gap: '25px', marginBottom: '30px' }}>
            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', display: 'flex', flexDirection: 'column' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600', textAlign: 'center' }}>Distribución por Estado</h2>
              <div style={{ flex: 1, minHeight: '250px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      isAnimationActive={!isExporting}
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

            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Saldos por Estado (Cap+Int)</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '15px' }}>
                <div style={{
                  background: 'rgba(0,0,0,0.2)',
                  border: `1px solid var(--text-primary)40`,
                  borderLeft: `4px solid var(--text-primary)`,
                  borderRadius: '8px',
                  padding: '15px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '5px',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                }}>
                  <span style={{ color: 'var(--text-primary)', fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>Total General</span>
                  <span style={{ fontSize: '1.3rem', fontWeight: 'bold', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{formatCurrency(estadosList.reduce((acc, curr) => acc + curr.Total, 0))}</span>
                </div>
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
                    <span style={{ color: d.fill, fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{d.Estado}</span>
                    <span style={{ fontSize: '1.3rem', fontWeight: 'bold', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{formatCurrency(d.Total)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="glass-panel" style={{ display: exportFormat === 'l' ? 'none' : 'block', padding: '25px', borderRadius: '12px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Saldos Vencidos vs A Vencer (Cap+Int)</h2>
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
                  <tfoot>
                    <tr style={{ background: 'rgba(255,255,255,0.05)', borderTop: '2px solid rgba(255,255,255,0.2)' }}>
                      <td style={{ padding: '15px 10px', fontWeight: 'bold', color: 'var(--text-primary)' }}>TOTALES</td>
                      <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-interes)' }}>{formatCurrency(estadosList.reduce((acc, curr) => acc + curr.Vencido, 0))}</td>
                      <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-total)' }}>{formatCurrency(estadosList.reduce((acc, curr) => acc + curr.AVencer, 0))}</td>
                      <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--text-primary)' }}>{formatCurrency(estadosList.reduce((acc, curr) => acc + curr.Total, 0))}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {(activeTab === 'morosidad' || isExporting) && (
        <div id="export-tab-morosidad">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginBottom: '30px' }}>
            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '10px' }}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Total Vencido (Mora)</span>
              <span style={{ fontSize: '1.8rem', fontWeight: 'bold', color: 'var(--color-interes)' }}>{formatCurrency(moraKPIs.totalVencido)}</span>
            </div>
            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '10px' }}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px' }}>A Vencer (Cartera Morosa)</span>
              <span style={{ fontSize: '1.8rem', fontWeight: 'bold', color: 'var(--color-total)' }}>{formatCurrency(moraKPIs.totalAVencer)}</span>
            </div>
            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '10px' }}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Mora Temprana (1-90 días)</span>
              <span style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#f59e0b' }}>{formatCurrency(moraKPIs.moraTemprana)}</span>
            </div>
            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '10px' }}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: '500', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Mora Dura (&gt;90 días)</span>
              <span style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#ef4444' }}>{formatCurrency(moraKPIs.moraDura)}</span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isExporting ? 'repeat(auto-fit, minmax(450px, 1fr))' : '1fr', gap: '25px', marginBottom: '30px' }}>
            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', minHeight: '400px' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Distribución de Mora (Cap+Int+IVA)</h2>
              <ResponsiveContainer width="100%" height={320}>
                <PieChart margin={{ top: 10, right: 60, bottom: 10, left: 60 }}>
                  <Pie 
                    isAnimationActive={!isExporting}
                    data={moraBucketsPie} 
                    dataKey="Total" 
                    nameKey="label" 
                    cx="50%" 
                    cy="50%" 
                    innerRadius={45} 
                    outerRadius={70} 
                    label={renderCustomizedLabelMora} 
                    labelLine={(props) => {
                      const { points, payload, index } = props;
                      if (!points) return null;
                      
                      if (payload.isSmall) {
                        smallSlicesRef.current[index] = points[0];
                      }

                      if (payload.isSmall && !payload.showSmallSum) return <g></g>;
                      
                      if (payload.showSmallSum) {
                        const elbow = points[1] || points[0];
                        if (!elbow) return null;
                        const smallIndices = moraBucketsPie.map((b, i) => b.isSmall ? i : -1).filter(i => i !== -1);
                        
                        return (
                          <g>
                            <polyline points={points.map(p => `${p.x},${p.y}`).join(' ')} fill="none" stroke="var(--text-secondary)" />
                            {smallIndices.map(si => {
                              if (si === index) return null;
                              const p0 = smallSlicesRef.current[si];
                              if (!p0) return null;
                              return (
                                <line key={`conn-${si}`} x1={p0.x} y1={p0.y} x2={elbow.x} y2={elbow.y} stroke="var(--text-secondary)" strokeDasharray="3 3" />
                              );
                            })}
                          </g>
                        );
                      }
                      
                      return <polyline points={points.map(p => `${p.x},${p.y}`).join(' ')} fill="none" stroke="var(--text-secondary)" />;
                    }}
                  >
                    {moraBucketsPie.map((entry, index) => <Cell key={index} fill={entry.fill} />)}
                  </Pie>
                  <Tooltip
                    formatter={(value) => formatCurrency(value)}
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'white' }}
                    itemStyle={{ color: 'white' }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
              {smallBucketsFootnote && (
                <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '10px' }}>
                  {smallBucketsFootnote}
                </div>
              )}
            </div>
            
            <div className="glass-panel" style={{ padding: '25px', borderRadius: '12px', minHeight: '400px' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Saldos Vencidos (Cap+Int+IVA)</h2>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart
                  data={moraBuckets.filter(b => b.label !== 'Al día')}
                  margin={{ top: 35, right: 30, left: 20, bottom: 25 }}
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
                <Bar isAnimationActive={!isExporting} dataKey="Vencido" fill="var(--color-interes)" name="Valor Vencido" radius={[4, 4, 0, 0]}>
                  <LabelList
                    dataKey="Vencido"
                    position="top"
                    fill="var(--color-interes)"
                    formatter={(val) => val > 0 ? `$${(val / 1000000).toFixed(1)}M` : ''}
                    style={{ fontSize: 11, fontWeight: 'bold' }}
                  />
                </Bar>
                <Bar isAnimationActive={!isExporting} dataKey="AVencer" fill="var(--color-total)" name="Valor A Vencer" radius={[4, 4, 0, 0]}>
                  <LabelList
                    dataKey="AVencer"
                    position="top"
                    fill="var(--color-total)"
                    formatter={(val) => val > 0 ? `$${(val / 1000000).toFixed(1)}M` : ''}
                    style={{ fontSize: 11, fontWeight: 'bold' }}
                  />
                </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-panel" style={{ display: exportFormat === 'l' ? 'none' : 'block', padding: '25px', borderRadius: '12px', marginBottom: '30px' }}>
            <h2 style={{ fontSize: '1.2rem', marginBottom: '20px', fontWeight: '600' }}>Detalle de Cuotas Vencidas (Clasificadas por Días de Mora)</h2>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                    <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500' }}>Días de Morosidad</th>
                    <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Valor Vencido</th>
                    <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Valor A Vencer</th>
                    <th style={{ padding: '15px 10px', color: 'var(--text-secondary)', fontWeight: '500', textAlign: 'right' }}>Deuda Total Crédito</th>
                  </tr>
                </thead>
                <tbody>
                  {moraBuckets.filter(b => b.label !== 'Al día').map((row, idx) => (
                    <tr key={idx} style={{
                      borderBottom: '1px solid rgba(255,255,255,0.05)',
                      transition: 'background-color 0.2s',
                    }} className="table-row-hover">
                      <td style={{ padding: '15px 10px', fontWeight: '500' }}>{row.label}</td>
                      <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-interes)' }}>{formatCurrency(row.Vencido)}</td>
                      <td style={{ padding: '15px 10px', textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-total)' }}>{formatCurrency(row.AVencer)}</td>
                      <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--text-primary)' }}>{formatCurrency(row.Total)}</td>
                    </tr>
                  ))}
                  <tr style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}>
                    <td style={{ padding: '15px 10px', fontWeight: 'bold' }}>TOTAL MOROSIDAD</td>
                    <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-interes)' }}>{formatCurrency(moraBuckets.filter(b => b.label !== 'Al día').reduce((acc, b) => acc + b.Vencido, 0))}</td>
                    <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--color-total)' }}>{formatCurrency(moraBuckets.filter(b => b.label !== 'Al día').reduce((acc, b) => acc + b.AVencer, 0))}</td>
                    <td style={{ padding: '15px 10px', textAlign: 'right', fontWeight: 'bold', fontFamily: 'monospace', color: 'var(--text-primary)' }}>{formatCurrency(moraBuckets.filter(b => b.label !== 'Al día').reduce((acc, b) => acc + b.Total, 0))}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
        </>
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
