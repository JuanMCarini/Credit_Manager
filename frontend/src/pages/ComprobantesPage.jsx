import React, { useState, useCallback, useEffect, useMemo, Fragment } from 'react';
import axiosClient from '../api/axiosClient';
import { FileText, Users, Plus, Download, Edit, Trash2, CreditCard, PieChart } from 'lucide-react';
import ComprobanteModal from '../components/Finanzas/ComprobanteModal';
import ProveedorModal from '../components/Finanzas/ProveedorModal';
import CancelacionModal from '../components/Finanzas/CancelacionModal';
import DashboardComprobantesTab from '../components/Finanzas/DashboardComprobantesTab';
import PlanPagoForm from '../components/Finanzas/PlanPagoForm';
import CancelacionesListModal from '../components/Finanzas/CancelacionesListModal';

const MultiSelectDropdown = ({ options, selectedValues, onChange, placeholder }) => {
  const [isOpen, setIsOpen] = useState(false);

  // Cierra al hacer click afuera (opcional, pero por simplicidad usamos onMouseLeave o un overlay)
  
  const handleToggle = (val, e) => {
    e.stopPropagation();
    if (selectedValues.includes(val)) {
      onChange(selectedValues.filter(v => v !== val));
    } else {
      onChange([...selectedValues, val]);
    }
  };

  return (
    <div style={{ position: 'relative', width: '100%', marginTop: '5px' }} onMouseLeave={() => setIsOpen(false)}>
      <div 
        onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen); }}
        style={{ 
          padding: '4px', border: '1px solid var(--border-color)', borderRadius: '4px', 
          cursor: 'pointer', fontSize: '12px', minHeight: '24px', 
          backgroundColor: 'var(--surface-color)', textAlign: 'left',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
        }}
      >
        {selectedValues.length === 0 ? placeholder : `${selectedValues.length} seleccionados`}
      </div>
      {isOpen && (
        <div style={{ 
          position: 'absolute', top: '100%', left: 0, width: 'max-content', minWidth: '100%', 
          maxHeight: '150px', overflowY: 'auto', backgroundColor: 'var(--surface-color)', 
          border: '1px solid var(--border-color)', borderRadius: '4px', zIndex: 10, 
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)' 
        }}>
          {options.map(opt => (
            <div 
              key={opt} 
              onClick={(e) => handleToggle(opt, e)} 
              style={{ 
                padding: '6px', fontSize: '12px', display: 'flex', alignItems: 'center', 
                gap: '6px', cursor: 'pointer', borderBottom: '1px solid var(--background-color)',
                fontWeight: 'normal', color: 'var(--text-color)', textAlign: 'left'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--background-color)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              <input type="checkbox" checked={selectedValues.includes(opt)} readOnly style={{ margin: 0 }} />
              {String(opt).toUpperCase()}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const ComprobantesPage = () => {
  const [activeTab, setActiveTab] = useState('resumen');

  const [comprobantes, setComprobantes] = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [conceptos, setConceptos] = useState([]);
  const [planes, setPlanes] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  
  // Modals state
  const [isComprobanteModalOpen, setIsComprobanteModalOpen] = useState(false);
  const [isProveedorModalOpen, setIsProveedorModalOpen] = useState(false);
  const [isCancelacionModalOpen, setIsCancelacionModalOpen] = useState(false);
  const [isCancelacionesListModalOpen, setIsCancelacionesListModalOpen] = useState(false);
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [selectedComprobante, setSelectedComprobante] = useState(null);
  const [selectedProveedor, setSelectedProveedor] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState(null);

  const [comprobanteFilter, setComprobanteFilter] = useState({ proveedor: [], numero: '', concepto: [], estado: [] });
  const [comprobanteSort, setComprobanteSort] = useState({ key: 'fecha_emision', direction: 'desc' });
  const [planFilter, setPlanFilter] = useState({ id_origen: '', proveedor: '' });
  const [planSort, setPlanSort] = useState({ key: 'fecha', direction: 'desc' });
  const [expandedPlanes, setExpandedPlanes] = useState({});

  const togglePlanExpand = (planId) => {
    setExpandedPlanes(prev => ({ ...prev, [planId]: !prev[planId] }));
  };
  
  const handleSortComprobante = (key) => {
    let direction = 'asc';
    if (comprobanteSort.key === key && comprobanteSort.direction === 'asc') direction = 'desc';
    setComprobanteSort({ key, direction });
  };
  
  const handleSortPlan = (key) => {
    let direction = 'asc';
    if (planSort.key === key && planSort.direction === 'asc') direction = 'desc';
    setPlanSort({ key, direction });
  };

  const filteredAndSortedComprobantes = useMemo(() => {
    let result = [...comprobantes];
    if (comprobanteFilter.proveedor && comprobanteFilter.proveedor.length > 0) {
      result = result.filter(c => comprobanteFilter.proveedor.includes(c.proveedor?.razon_social));
    }
    if (comprobanteFilter.numero) {
      result = result.filter(c => {
         const numStr = `${c.tipo_comprobante} ${String(c.punto_venta).padStart(4, '0')}-${String(c.numero_comprobante).padStart(8, '0')}`;
         return numStr.toLowerCase().includes(comprobanteFilter.numero.toLowerCase());
      });
    }
    if (comprobanteFilter.concepto && comprobanteFilter.concepto.length > 0) {
      result = result.filter(c => comprobanteFilter.concepto.includes(c.concepto?.name));
    }
    if (comprobanteFilter.estado && comprobanteFilter.estado.length > 0) {
      result = result.filter(c => {
        let st = c.estado;
        if (c.estado !== 'pagado' && c.fecha_vencimiento) {
          const today = new Date();
          const venc = new Date(c.fecha_vencimiento + 'T00:00:00');
          today.setHours(0, 0, 0, 0);
          if (venc < today) st = 'vencido';
        }
        return comprobanteFilter.estado.includes(st.toLowerCase());
      });
    }
    if (comprobanteSort.key) {
      result.sort((a, b) => {
        let valA = a[comprobanteSort.key] || '';
        let valB = b[comprobanteSort.key] || '';
        
        if (comprobanteSort.key === 'proveedor') {
            valA = a.proveedor?.razon_social || '';
            valB = b.proveedor?.razon_social || '';
        } else if (comprobanteSort.key === 'concepto') {
            valA = a.concepto?.name || '';
            valB = b.concepto?.name || '';
        } else if (comprobanteSort.key === 'numero') {
            valA = `${a.tipo_comprobante} ${String(a.punto_venta).padStart(4, '0')}-${String(a.numero_comprobante).padStart(8, '0')}`;
            valB = `${b.tipo_comprobante} ${String(b.punto_venta).padStart(4, '0')}-${String(b.numero_comprobante).padStart(8, '0')}`;
        } else if (comprobanteSort.key === 'estado_calc') {
            const getEst = (c) => {
                let st = c.estado;
                if (c.estado !== 'pagado' && c.fecha_vencimiento) {
                  const today = new Date();
                  const venc = new Date(c.fecha_vencimiento + 'T00:00:00');
                  today.setHours(0, 0, 0, 0);
                  if (venc < today) st = 'vencido';
                }
                return st;
            };
            valA = getEst(a);
            valB = getEst(b);
        } else if (comprobanteSort.key === 'saldo') {
            valA = Math.max(0, parseFloat(a.importe_total) - parseFloat(a.importe_cancelado || 0));
            valB = Math.max(0, parseFloat(b.importe_total) - parseFloat(b.importe_cancelado || 0));
        }

        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        
        if (valA < valB) return comprobanteSort.direction === 'asc' ? -1 : 1;
        if (valA > valB) return comprobanteSort.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [comprobantes, comprobanteFilter, comprobanteSort]);

  const filteredAndSortedPlanes = useMemo(() => {
    let result = [...planes];
    if (planFilter.id_origen) {
      result = result.filter(p => (p.id_origen || '').toLowerCase().includes(planFilter.id_origen.toLowerCase()));
    }
    if (planFilter.proveedor) {
      result = result.filter(p => (p.proveedor?.razon_social || p.proveedor_id || '').toLowerCase().includes(planFilter.proveedor.toLowerCase()));
    }
    if (planSort.key) {
      result.sort((a, b) => {
        let valA = a[planSort.key] || '';
        let valB = b[planSort.key] || '';
        
        if (planSort.key === 'proveedor') {
            valA = a.proveedor?.razon_social || a.proveedor_id || '';
            valB = b.proveedor?.razon_social || b.proveedor_id || '';
        }

        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        
        if (valA < valB) return planSort.direction === 'asc' ? -1 : 1;
        if (valA > valB) return planSort.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [planes, planFilter, planSort]);


  const SortIcon = ({ sortConfig, columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '5px' }}>↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  const uniqueProveedores = useMemo(() => {
    let result = [...comprobantes];
    if (comprobanteFilter.numero) {
      result = result.filter(c => `${c.tipo_comprobante} ${String(c.punto_venta).padStart(4, '0')}-${String(c.numero_comprobante).padStart(8, '0')}`.toLowerCase().includes(comprobanteFilter.numero.toLowerCase()));
    }
    if (comprobanteFilter.concepto && comprobanteFilter.concepto.length > 0) {
      result = result.filter(c => comprobanteFilter.concepto.includes(c.concepto?.name));
    }
    if (comprobanteFilter.estado && comprobanteFilter.estado.length > 0) {
      result = result.filter(c => {
        let st = c.estado;
        if (c.estado !== 'pagado' && c.fecha_vencimiento) {
          const today = new Date();
          const venc = new Date(c.fecha_vencimiento + 'T00:00:00');
          today.setHours(0, 0, 0, 0);
          if (venc < today) st = 'vencido';
        }
        return comprobanteFilter.estado.includes(st.toLowerCase());
      });
    }
    return [...new Set(result.map(c => c.proveedor?.razon_social).filter(Boolean))].sort();
  }, [comprobantes, comprobanteFilter.numero, comprobanteFilter.concepto, comprobanteFilter.estado]);

  const uniqueConceptos = useMemo(() => {
    let result = [...comprobantes];
    if (comprobanteFilter.proveedor && comprobanteFilter.proveedor.length > 0) {
      result = result.filter(c => comprobanteFilter.proveedor.includes(c.proveedor?.razon_social));
    }
    if (comprobanteFilter.numero) {
      result = result.filter(c => `${c.tipo_comprobante} ${String(c.punto_venta).padStart(4, '0')}-${String(c.numero_comprobante).padStart(8, '0')}`.toLowerCase().includes(comprobanteFilter.numero.toLowerCase()));
    }
    if (comprobanteFilter.estado && comprobanteFilter.estado.length > 0) {
      result = result.filter(c => {
        let st = c.estado;
        if (c.estado !== 'pagado' && c.fecha_vencimiento) {
          const today = new Date();
          const venc = new Date(c.fecha_vencimiento + 'T00:00:00');
          today.setHours(0, 0, 0, 0);
          if (venc < today) st = 'vencido';
        }
        return comprobanteFilter.estado.includes(st.toLowerCase());
      });
    }
    return [...new Set(result.map(c => c.concepto?.name).filter(Boolean))].sort();
  }, [comprobantes, comprobanteFilter.proveedor, comprobanteFilter.numero, comprobanteFilter.estado]);
  
  const uniqueEstados = useMemo(() => {
    let result = [...comprobantes];
    if (comprobanteFilter.proveedor && comprobanteFilter.proveedor.length > 0) {
      result = result.filter(c => comprobanteFilter.proveedor.includes(c.proveedor?.razon_social));
    }
    if (comprobanteFilter.numero) {
      result = result.filter(c => `${c.tipo_comprobante} ${String(c.punto_venta).padStart(4, '0')}-${String(c.numero_comprobante).padStart(8, '0')}`.toLowerCase().includes(comprobanteFilter.numero.toLowerCase()));
    }
    if (comprobanteFilter.concepto && comprobanteFilter.concepto.length > 0) {
      result = result.filter(c => comprobanteFilter.concepto.includes(c.concepto?.name));
    }
    return [...new Set(result.map(c => {
        let st = c.estado;
        if (c.estado !== 'pagado' && c.fecha_vencimiento) {
          const today = new Date();
          const venc = new Date(c.fecha_vencimiento + 'T00:00:00');
          today.setHours(0, 0, 0, 0);
          if (venc < today) st = 'vencido';
        }
        return st;
    }))].sort();
  }, [comprobantes, comprobanteFilter.proveedor, comprobanteFilter.numero, comprobanteFilter.concepto]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [resComp, resProv, resConceptos, resPlanes] = await Promise.all([
        axiosClient.get('/api/finanzas/comprobantes'),
        axiosClient.get('/api/finanzas/proveedores'),
        axiosClient.get('/api/finanzas/conceptos'),
        axiosClient.get('/api/finanzas/planes')
      ]);
      setComprobantes(resComp.data);
      setProveedores(resProv.data);
      setConceptos(resConceptos.data);
      setPlanes(resPlanes.data);
    } catch (err) {
      console.error(err);
      setError('Error al cargar los datos.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  const handleOpenComprobanteModal = (comp = null) => {
    setSelectedComprobante(comp);
    setIsComprobanteModalOpen(true);
  };

  const handleOpenProveedorModal = (prov = null) => {
    setSelectedProveedor(prov);
    setIsProveedorModalOpen(true);
  };

  const handleOpenPlanModal = (plan = null) => {
    setSelectedPlan(plan);
    setIsPlanModalOpen(true);
  };

  const handleOpenCancelacionModal = (comp) => {
    setSelectedComprobante(comp);
    setIsCancelacionModalOpen(true);
  };

  const handleOpenCancelacionesListModal = (comp) => {
    setSelectedComprobante(comp);
    setIsCancelacionesListModalOpen(true);
  };

  const handleDeleteComprobante = async (id) => {
    if (!window.confirm("¿Está seguro de eliminar este comprobante?")) return;
    try {
      await axiosClient.delete(`/api/finanzas/comprobantes/${id}`);
      fetchData();
    } catch (err) {
      alert("Error al eliminar el comprobante.");
    }
  };

  const handleDeleteProveedor = async (id) => {
    if (!window.confirm("¿Está seguro de eliminar este proveedor?")) return;
    try {
      await axiosClient.delete(`/api/finanzas/proveedores/${id}`);
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || "Error al eliminar el proveedor.");
    }
  };

  const handleDeletePlan = async (id) => {
    if (!window.confirm("¿Está seguro de eliminar este plan de pago? Se eliminarán todas las cuotas asociadas.")) return;
    try {
      await axiosClient.delete(`/api/finanzas/planes/${id}`);
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || "Error al eliminar el plan.");
    }
  };

  const handleDownloadPdf = (filepath) => {
    // Assuming filepath is served via static route. 
    // Usually, in a real app, it would be a proper URL or an API endpoint that returns the file.
    // Given the previous setup, uploads are in data/uploads and served at /static.
    if (!filepath) return;
    // Extract filename from path (e.g. data/uploads/comprobantes/file.pdf -> comprobantes/file.pdf)
    // Actually, filepath might be absolute or relative. Let's just create a link to /static/...
    const url = `/static/${filepath.split('uploads/')[1] || filepath.split('uploads\\')[1]}`;
    window.open(url, '_blank');
  };

  return (
    <div className="page-container" style={{ padding: '24px', margin: '0 auto' }}>
      <header className="page-header" style={{ marginBottom: '32px' }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '28px', fontWeight: 'bold' }}>
          <FileText size={32} color="var(--primary-color)" />
          Gestión de Comprobantes
        </h1>
        <p className="page-description" style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px' }}>
          Administre las facturas y comprobantes recibidos, así como el listado de proveedores.
        </p>
      </header>

      <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--border-color)', marginBottom: '24px' }}>
        <button
          onClick={() => setActiveTab('resumen')}
          style={{
            padding: '12px 24px',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'resumen' ? '3px solid var(--primary-color)' : '3px solid transparent',
            color: activeTab === 'resumen' ? 'var(--primary-color)' : 'var(--text-muted)',
            fontWeight: activeTab === 'resumen' ? '600' : '400',
            cursor: 'pointer',
            fontSize: '16px',
            transition: 'all 0.2s',
            display: 'flex', alignItems: 'center', gap: '8px'
          }}
        >
          <PieChart size={18} />
          Resumen
        </button>
        <button
          onClick={() => setActiveTab('comprobantes')}
          style={{
            padding: '12px 24px',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'comprobantes' ? '3px solid var(--primary-color)' : '3px solid transparent',
            color: activeTab === 'comprobantes' ? 'var(--primary-color)' : 'var(--text-muted)',
            fontWeight: activeTab === 'comprobantes' ? '600' : '400',
            cursor: 'pointer',
            fontSize: '16px',
            transition: 'all 0.2s',
            display: 'flex', alignItems: 'center', gap: '8px'
          }}
        >
          <FileText size={18} />
          Comprobantes
        </button>
        <button
          onClick={() => setActiveTab('proveedores')}
          style={{
            padding: '12px 24px',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'proveedores' ? '3px solid var(--primary-color)' : '3px solid transparent',
            color: activeTab === 'proveedores' ? 'var(--primary-color)' : 'var(--text-muted)',
            fontWeight: activeTab === 'proveedores' ? '600' : '400',
            cursor: 'pointer',
            fontSize: '16px',
            transition: 'all 0.2s',
            display: 'flex', alignItems: 'center', gap: '8px'
          }}
        >
          <Users size={18} />
          Proveedores
        </button>
        <button
          onClick={() => setActiveTab('planes')}
          style={{
            padding: '12px 24px',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'planes' ? '3px solid var(--primary-color)' : '3px solid transparent',
            color: activeTab === 'planes' ? 'var(--primary-color)' : 'var(--text-muted)',
            fontWeight: activeTab === 'planes' ? '600' : '400',
            cursor: 'pointer',
            fontSize: '16px',
            transition: 'all 0.2s',
            display: 'flex', alignItems: 'center', gap: '8px'
          }}
        >
          <CreditCard size={18} />
          Planes de Pago
        </button>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>{error}</div>}

      {activeTab === 'resumen' && (
        <DashboardComprobantesTab comprobantes={comprobantes} />
      )}

      {activeTab === 'comprobantes' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>Listado de Comprobantes</h3>
            <button className="btn btn-primary" onClick={() => handleOpenComprobanteModal()} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={18} /> Nuevo Comprobante
            </button>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              
              <thead>
                <tr>
                  <th onClick={() => handleSortComprobante('fecha_emision')} style={{ textAlign: 'center', cursor: 'pointer' }}>Fecha Emisión <SortIcon sortConfig={comprobanteSort} columnKey="fecha_emision" /></th>
                  <th onClick={() => handleSortComprobante('fecha_vencimiento')} style={{ textAlign: 'center', cursor: 'pointer' }}>Vencimiento <SortIcon sortConfig={comprobanteSort} columnKey="fecha_vencimiento" /></th>
                  <th onClick={() => handleSortComprobante('proveedor')} style={{ textAlign: 'center', cursor: 'pointer' }}>
                    Proveedor <SortIcon sortConfig={comprobanteSort} columnKey="proveedor" />
                    <MultiSelectDropdown 
                      options={uniqueProveedores} 
                      selectedValues={comprobanteFilter.proveedor} 
                      onChange={val => setComprobanteFilter({ ...comprobanteFilter, proveedor: val })} 
                      placeholder="Todos" 
                    />
                  </th>
                  <th onClick={() => handleSortComprobante('numero')} style={{ textAlign: 'center', cursor: 'pointer' }}>
                    Comprobante <SortIcon sortConfig={comprobanteSort} columnKey="numero" />
                    <input type="text" placeholder="Filtrar..." value={comprobanteFilter.numero} onChange={e => setComprobanteFilter({ ...comprobanteFilter, numero: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                  </th>
                  <th onClick={() => handleSortComprobante('concepto')} style={{ textAlign: 'center', cursor: 'pointer' }}>
                    Concepto <SortIcon sortConfig={comprobanteSort} columnKey="concepto" />
                    <MultiSelectDropdown 
                      options={uniqueConceptos} 
                      selectedValues={comprobanteFilter.concepto} 
                      onChange={val => setComprobanteFilter({ ...comprobanteFilter, concepto: val })} 
                      placeholder="Todos" 
                    />
                  </th>
                  <th onClick={() => handleSortComprobante('importe_total')} style={{ textAlign: 'center', cursor: 'pointer' }}>Total <SortIcon sortConfig={comprobanteSort} columnKey="importe_total" /></th>
                  <th onClick={() => handleSortComprobante('saldo')} style={{ textAlign: 'center', cursor: 'pointer' }}>Saldo <SortIcon sortConfig={comprobanteSort} columnKey="saldo" /></th>
                  <th onClick={() => handleSortComprobante('estado_calc')} style={{ textAlign: 'center', cursor: 'pointer' }}>
                    Estado <SortIcon sortConfig={comprobanteSort} columnKey="estado_calc" />
                    <MultiSelectDropdown 
                      options={uniqueEstados} 
                      selectedValues={comprobanteFilter.estado} 
                      onChange={val => setComprobanteFilter({ ...comprobanteFilter, estado: val })} 
                      placeholder="Todos" 
                    />
                  </th>
                  <th style={{ textAlign: 'center' }}>PDF</th>
                  <th style={{ textAlign: 'center' }}>Acciones</th>
                </tr>
              </thead>

              <tbody>
                {loading ? (
                  <tr><td colSpan="10" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
                ) : filteredAndSortedComprobantes.length === 0 ? (
                  <tr><td colSpan="10" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>No hay comprobantes cargados.</td></tr>
                ) : (
                  filteredAndSortedComprobantes.map(c => {
                    let displayEstado = c.estado;
                    if (c.estado !== 'pagado' && c.fecha_vencimiento) {
                      const today = new Date();
                      const venc = new Date(c.fecha_vencimiento + 'T00:00:00');
                      today.setHours(0, 0, 0, 0);
                      if (venc < today) {
                        displayEstado = 'vencido';
                      }
                    }

                    let rowStyle = {};
                    if (displayEstado === 'pagado') rowStyle = { backgroundColor: 'rgba(81, 207, 102, 0.05)' };
                    else if (displayEstado === 'vencido') rowStyle = { backgroundColor: 'rgba(255, 107, 107, 0.08)' };
                    else if (displayEstado === 'parcial') rowStyle = { backgroundColor: 'rgba(252, 196, 25, 0.05)' };

                    return (
                      <tr key={c.id} style={rowStyle}>
                        <td style={{ textAlign: 'center' }}>{c.fecha_emision}</td>
                        <td style={{ textAlign: 'center' }}>{c.fecha_vencimiento || '-'}</td>
                        <td>{c.proveedor?.razon_social}</td>
                        <td style={{ textAlign: 'center' }}>{c.tipo_comprobante} {String(c.punto_venta).padStart(4, '0')}-{String(c.numero_comprobante).padStart(8, '0')}</td>
                        <td>{c.concepto?.name || '-'}</td>
                        <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{formatCurrency(c.importe_total)}</td>
                        <td style={{ textAlign: 'right', color: 'var(--primary-color)' }}>{formatCurrency(Math.max(0, parseFloat(c.importe_total) - parseFloat(c.importe_cancelado || 0)))}</td>
                        <td style={{ textAlign: 'center' }}>
                          <span className={`status-badge ${displayEstado === 'pagado' ? 'status-completed' : displayEstado === 'vencido' ? 'status-fallido' : displayEstado === 'parcial' ? 'status-active' : 'status-pendiente'}`}>
                            {displayEstado.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          {c.archivo_pdf ? (
                            <button className="btn-secondary" onClick={() => handleDownloadPdf(c.archivo_pdf)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver PDF">
                              📥
                            </button>
                          ) : '-'}
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                            <button className="btn-secondary" onClick={() => handleOpenCancelacionesListModal(c)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Historial de Pagos">
                              📑
                            </button>
                            {c.estado !== 'pagado' && (
                              <button className="btn-secondary" onClick={() => handleOpenCancelacionModal(c)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Registrar Pago">
                                💸
                              </button>
                            )}
                            <button className="btn-secondary" onClick={() => handleOpenComprobanteModal(c)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Editar">
                              ✏️
                            </button>
                            <button className="btn-secondary" onClick={() => handleDeleteComprobante(c.id)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar">
                              🗑️
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'proveedores' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>Listado de Proveedores</h3>
            <button className="btn btn-primary" onClick={() => handleOpenProveedorModal()} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={18} /> Nuevo Proveedor
            </button>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ textAlign: 'center' }}>ID</th>
                  <th style={{ textAlign: 'center' }}>Razón Social</th>
                  <th style={{ textAlign: 'center' }}>CUIT/Doc</th>
                  <th style={{ textAlign: 'center' }}>Categoría</th>
                  <th style={{ textAlign: 'center' }}>Concepto Predeterminado</th>
                  <th style={{ textAlign: 'center' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan="6" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
                ) : proveedores.length === 0 ? (
                  <tr><td colSpan="6" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>No hay proveedores cargados.</td></tr>
                ) : (
                  proveedores.map(p => (
                    <tr key={p.id}>
                      <td style={{ textAlign: 'center' }}>{p.id}</td>
                      <td>{p.razon_social}</td>
                      <td style={{ textAlign: 'center' }}>{p.nro_documento}</td>
                      <td>{p.categoria_impositiva}</td>
                      <td>{p.concepto?.name || '-'}</td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                          <button className="btn-secondary" onClick={() => handleOpenProveedorModal(p)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Editar">
                            ✏️
                          </button>
                          <button className="btn-secondary" onClick={() => handleDeleteProveedor(p.id)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar">
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'planes' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>Listado de Planes de Pago</h3>
            <button className="btn btn-primary" onClick={() => handleOpenPlanModal()} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Plus size={18} /> Nuevo Plan
            </button>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              
              <thead>
                <tr>
                  <th onClick={() => handleSortPlan('id_origen')} style={{ textAlign: 'center', cursor: 'pointer' }}>
                    ID Origen <SortIcon sortConfig={planSort} columnKey="id_origen" />
                    <input type="text" placeholder="Filtrar..." value={planFilter.id_origen} onChange={e => setPlanFilter({ ...planFilter, id_origen: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                  </th>
                  <th onClick={() => handleSortPlan('fecha')} style={{ textAlign: 'center', cursor: 'pointer' }}>Fecha <SortIcon sortConfig={planSort} columnKey="fecha" /></th>
                  <th onClick={() => handleSortPlan('proveedor')} style={{ textAlign: 'center', cursor: 'pointer' }}>
                    Proveedor <SortIcon sortConfig={planSort} columnKey="proveedor" />
                    <input type="text" placeholder="Filtrar..." value={planFilter.proveedor} onChange={e => setPlanFilter({ ...planFilter, proveedor: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                  </th>
                  <th onClick={() => handleSortPlan('capital')} style={{ textAlign: 'center', cursor: 'pointer' }}>Capital <SortIcon sortConfig={planSort} columnKey="capital" /></th>
                  <th onClick={() => handleSortPlan('anticipo')} style={{ textAlign: 'center', cursor: 'pointer' }}>Anticipo <SortIcon sortConfig={planSort} columnKey="anticipo" /></th>
                  <th onClick={() => handleSortPlan('plazo')} style={{ textAlign: 'center', cursor: 'pointer' }}>Cuotas <SortIcon sortConfig={planSort} columnKey="plazo" /></th>
                  <th onClick={() => handleSortPlan('valor_cuota')} style={{ textAlign: 'center', cursor: 'pointer' }}>Valor Cuota <SortIcon sortConfig={planSort} columnKey="valor_cuota" /></th>
                  <th onClick={() => handleSortPlan('tna')} style={{ textAlign: 'center', cursor: 'pointer' }}>TNA <SortIcon sortConfig={planSort} columnKey="tna" /></th>
                  <th style={{ textAlign: 'center' }}>Pendientes</th>
                  <th style={{ textAlign: 'center' }}>Acciones</th>
                </tr>
              </thead>

              <tbody>
                {loading ? (
                  <tr><td colSpan="9" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
                ) : filteredAndSortedPlanes.length === 0 ? (
                  <tr><td colSpan="9" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>No hay planes cargados.</td></tr>
                ) : (
                  filteredAndSortedPlanes.map(p => (
                    <Fragment key={p.id}>
                      <tr>
                        <td style={{ textAlign: 'center' }}>{p.id_origen}</td>
                        <td style={{ textAlign: 'center' }}>{p.fecha}</td>
                        <td>{p.proveedor?.razon_social || p.proveedor_id}</td>
                        <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{formatCurrency(p.capital)}</td>
                        <td style={{ textAlign: 'right' }}>{formatCurrency(p.anticipo)}</td>
                        <td style={{ textAlign: 'center' }}>{p.plazo}</td>
                        <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{formatCurrency(p.valor_cuota)}</td>
                        <td style={{ textAlign: 'center' }}>{(p.tna * 100).toFixed(2)}%</td>
                        <td style={{ textAlign: 'center' }}>
                          {p.cuotas_pendientes ? p.cuotas_pendientes.length : 0}
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                            {p.cuotas_pendientes && p.cuotas_pendientes.length > 0 && (
                              <button className="btn-secondary" onClick={() => togglePlanExpand(p.id)} style={{ padding: '4px 8px', fontSize: '14px' }} title={expandedPlanes[p.id] ? "Ocultar Cuotas" : "Ver Cuotas"}>
                                👁️
                              </button>
                            )}
                            <button className="btn-secondary" onClick={() => handleOpenPlanModal(p)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Editar">
                              ✏️
                            </button>
                            <button className="btn-secondary" onClick={() => handleDeletePlan(p.id)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar">
                              🗑️
                            </button>
                          </div>
                        </td>
                      </tr>
                      {expandedPlanes[p.id] && p.cuotas_pendientes && p.cuotas_pendientes.length > 0 && (
                        <tr>
                          <td colSpan="10" style={{ padding: '10px 20px', backgroundColor: 'var(--background-color)' }}>
                            <div style={{ padding: '10px', backgroundColor: 'var(--surface-color)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                              <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: 'var(--text-color)' }}>Cuotas Pendientes de Cancelar</h4>
                              <table className="data-table" style={{ width: '100%', fontSize: '13px' }}>
                                <thead>
                                  <tr>
                                    <th>Nro Comprobante</th>
                                    <th>Vencimiento</th>
                                    <th style={{ textAlign: 'right' }}>Importe Total</th>
                                    <th style={{ textAlign: 'right' }}>Cancelado</th>
                                    <th style={{ textAlign: 'right' }}>Saldo Restante</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {p.cuotas_pendientes.map(cuota => (
                                    <tr key={cuota.id}>
                                      <td>{cuota.numero_comprobante}</td>
                                      <td>{cuota.fecha_vencimiento}</td>
                                      <td style={{ textAlign: 'right' }}>{formatCurrency(cuota.importe_total)}</td>
                                      <td style={{ textAlign: 'right' }}>{formatCurrency(cuota.importe_cancelado)}</td>
                                      <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{formatCurrency(cuota.importe_total - cuota.importe_cancelado)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ComprobanteModal 
        isOpen={isComprobanteModalOpen} 
        onClose={() => setIsComprobanteModalOpen(false)} 
        comprobante={selectedComprobante} 
        proveedores={proveedores} 
        conceptos={conceptos}
        onSave={() => {
          setIsComprobanteModalOpen(false);
          fetchData();
        }} 
        onNewProveedor={() => setIsProveedorModalOpen(true)}
      />

      <ProveedorModal
        isOpen={isProveedorModalOpen}
        onClose={() => setIsProveedorModalOpen(false)}
        onSave={() => { setIsProveedorModalOpen(false); fetchData(); }}
        proveedor={selectedProveedor}
        conceptos={conceptos}
      />

      <CancelacionModal
        isOpen={isCancelacionModalOpen}
        onClose={() => setIsCancelacionModalOpen(false)}
        onSave={() => { setIsCancelacionModalOpen(false); fetchData(); }}
        comprobante={selectedComprobante}
      />

      <CancelacionesListModal
        isOpen={isCancelacionesListModalOpen}
        onClose={() => setIsCancelacionesListModalOpen(false)}
        onSave={() => { fetchData(); }}
        comprobante={selectedComprobante}
      />

      <PlanPagoForm
        isOpen={isPlanModalOpen}
        onClose={() => setIsPlanModalOpen(false)}
        proveedores={proveedores}
        conceptos={conceptos}
        editPlan={selectedPlan}
        onSave={() => { setIsPlanModalOpen(false); fetchData(); }}
      />
    </div>
  );
};

export default ComprobantesPage;
