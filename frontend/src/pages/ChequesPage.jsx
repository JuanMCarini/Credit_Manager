import React, { useState, useEffect, useMemo } from 'react';
import { useAuthStore } from '../store/useAuthStore';
import useAppStore from '../store/useAppStore';
import CurrencyInput from '../components/CurrencyInput';
import { FilterX } from 'lucide-react';
import ExcelListFilter from '../components/ExcelListFilter';
import ExcelDateFilter from '../components/ExcelDateFilter';

const ChequesPage = () => {
  const { user, token } = useAuthStore();
  const { apiStatus, bancos = [], fetchAuxiliares } = useAppStore();
  const [cheques, setCheques] = useState([]);
  const [operadores, setOperadores] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modales
  const [showNuevoCheque, setShowNuevoCheque] = useState(false);
  const [editingChequeId, setEditingChequeId] = useState(null);
  const [showOperarCheque, setShowOperarCheque] = useState(false);
  const [showNuevoOperador, setShowNuevoOperador] = useState(false);
  const [showImageModal, setShowImageModal] = useState(false);
  
  const [selectedCheque, setSelectedCheque] = useState(null);
  const [imagenFile, setImagenFile] = useState(null);
  const [showListadoOperaciones, setShowListadoOperaciones] = useState(false);
  const [operacionesList, setOperacionesList] = useState([]);
  const [editingOperacionId, setEditingOperacionId] = useState(null);
  const [minFechaOperacion, setMinFechaOperacion] = useState('');

  const [showModalMovimiento, setShowModalMovimiento] = useState(false);
  const [movimientos, setMovimientos] = useState([]);
  const [loadingMovimientos, setLoadingMovimientos] = useState(false);
  const [movimientoSearch, setMovimientoSearch] = useState('');

  // Filtros y Ordenamiento
  const [filter, setFilter] = useState({ ID: '', Emisor: [], Beneficiario: [], Numero: '', Pago: [], Estado: [] });
  const [sortConfig, setSortConfig] = useState({ key: 'ID', direction: 'desc' });

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key, direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, fontSize: '10px', marginLeft: '4px' }}>↕</span>;
    return sortConfig.direction === 'asc' ? <span style={{ fontSize: '10px', marginLeft: '4px' }}>↑</span> : <span style={{ fontSize: '10px', marginLeft: '4px' }}>↓</span>;
  };

  const filteredAndSortedCheques = useMemo(() => {
    let result = [...cheques];
    if (filter.ID) result = result.filter(c => c.id.toString().includes(filter.ID));
    if (filter.Emisor.length > 0) result = result.filter(c => filter.Emisor.includes(c.emisor?.razon_social));
    if (filter.Beneficiario.length > 0) result = result.filter(c => filter.Beneficiario.includes(c.beneficiario?.razon_social));
    if (filter.Numero) result = result.filter(c => c.numero.toLowerCase().includes(filter.Numero.toLowerCase()));
    if (filter.Pago.length > 0) result = result.filter(c => filter.Pago.includes(c.fecha_pago));
    if (filter.Estado.length > 0) result = result.filter(c => filter.Estado.includes(c.estado));

    if (sortConfig.key) {
      result.sort((a, b) => {
        let valA, valB;
        if (sortConfig.key === 'ID') { valA = a.id; valB = b.id; }
        else if (sortConfig.key === 'Emisor') { valA = a.emisor?.razon_social || ''; valB = b.emisor?.razon_social || ''; }
        else if (sortConfig.key === 'Beneficiario') { valA = a.beneficiario?.razon_social || ''; valB = b.beneficiario?.razon_social || ''; }
        else if (sortConfig.key === 'Número') { valA = a.numero; valB = b.numero; }
        else if (sortConfig.key === 'Monto') { valA = parseFloat(a.monto); valB = parseFloat(b.monto); }
        else if (sortConfig.key === 'Pago') { valA = a.fecha_pago; valB = b.fecha_pago; }
        else if (sortConfig.key === 'Estado') { valA = a.estado; valB = b.estado; }
        
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [cheques, filter, sortConfig]);

  const totalMonto = useMemo(() => {
    return filteredAndSortedCheques.reduce((sum, c) => sum + parseFloat(c.monto || 0), 0);
  }, [filteredAndSortedCheques]);

  const AVAILABLE_EMISORES = useMemo(() => [...new Set(cheques.map(c => c.emisor?.razon_social).filter(Boolean))].sort(), [cheques]);
  const AVAILABLE_BENEFICIARIOS = useMemo(() => [...new Set(cheques.map(c => c.beneficiario?.razon_social).filter(Boolean))].sort(), [cheques]);
  const AVAILABLE_ESTADOS = useMemo(() => [...new Set(cheques.map(c => c.estado).filter(Boolean))].sort(), [cheques]);
  const AVAILABLE_PAGOS = useMemo(() => [...new Set(cheques.map(c => c.fecha_pago).filter(Boolean))].sort(), [cheques]);
  
  // Initial Forms
  const initialChequeForm = {
    fecha_emision: '', fecha_pago: '', numero: '', monto: '', emisor_cuit: '', banco_id: ''
  };
  const initialOperadorForm = {
    cuit: '', razon_social: '', calificacion: 'BUENO', telefono: '', email: ''
  };
  const initialOperacionForm = {
    fecha_operacion: new Date().toISOString().split('T')[0],
    operador_cuil: '',
    tna_descuento: '',
    dias_castigo: 0,
    porcentaje_gastos: 2.8
  };

  const [chequeForm, setChequeForm] = useState(initialChequeForm);
  const [operadorForm, setOperadorForm] = useState(initialOperadorForm);
  const [operacionForm, setOperacionForm] = useState(initialOperacionForm);

  const fetchData = async () => {
    try {
      setLoading(true);
      const resCheques = await fetch('/api/cheques/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if(resCheques.ok) setCheques(await resCheques.json());
      
      const resOperadores = await fetch('/api/cheques/operadores', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if(resOperadores.ok) setOperadores(await resOperadores.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    if (bancos.length === 0) {
      fetchAuxiliares();
    }
  }, []);

  const handleCrearCheque = async (e) => {
    e.preventDefault();
    try {
      const isEditing = editingChequeId !== null;
      const url = isEditing ? `/api/cheques/${editingChequeId}` : '/api/cheques/';
      const method = isEditing ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify(chequeForm)
      });
      if(res.ok) {
        const resultData = await res.json();
        const chequeIdToUpload = isEditing ? editingChequeId : resultData.id;

        if (imagenFile) {
          const formData = new FormData();
          formData.append('file', imagenFile);
          await fetch(`/api/cheques/${chequeIdToUpload}/imagen`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
          });
        }

        setShowNuevoCheque(false);
        setEditingChequeId(null);
        setChequeForm(initialChequeForm);
        setImagenFile(null);
        fetchData();
      } else {
        alert(await res.text());
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleBorrarCheque = async (id) => {
    if (!window.confirm("¿Estás seguro de que querés borrar este cheque?")) return;
    try {
      const res = await fetch(`/api/cheques/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchData();
      } else {
        alert(await res.text());
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCrearOperador = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/cheques/operadores', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(operadorForm)
      });
      if(res.ok) {
        setShowNuevoOperador(false);
        setOperadorForm(initialOperadorForm);
        fetchData();
      } else {
        alert(await res.text());
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleOperarCheque = async (e) => {
    e.preventDefault();
    try {
      const tipo = editingOperacionId 
           ? operacionForm.tipo_operacion 
           : (selectedCheque.es_propio ? 'VENTA' : (selectedCheque.estado === 'PENDIENTE' ? 'COMPRA' : 'VENTA'));
           
      const payload = { 
        ...operacionForm, 
        tipo_operacion: tipo,
        tna_descuento: Number(operacionForm.tna_descuento) / 100,
        porcentaje_gastos: Number(operacionForm.porcentaje_gastos) / 100
      };
      
      const url = editingOperacionId 
           ? `/api/cheques/operaciones/${editingOperacionId}` 
           : `/api/cheques/${selectedCheque.id}/operaciones`;
      const method = editingOperacionId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method: method,
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      if(res.ok) {
        setShowOperarCheque(false);
        setOperacionForm(initialOperacionForm);
        setEditingOperacionId(null);
        fetchData();
        if (showListadoOperaciones) {
           abrirListadoOperaciones(selectedCheque);
        }
      } else {
        alert(await res.text());
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchMovimientos = async () => {
    setLoadingMovimientos(true);
    try {
      // Pedimos los ultimos movimientos (ej: limite de 200 para mostrar en la modal)
      const res = await fetch(`/api/finanzas/movimientos?limit=200`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMovimientos(data.items || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingMovimientos(false);
    }
  };

  const abrirModalMovimiento = (cheque) => {
    setSelectedCheque(cheque);
    setShowModalMovimiento(true);
    fetchMovimientos();
  };

  const handleAsignarMovimiento = async (movimientoId) => {
    try {
      const res = await fetch(`/api/cheques/${selectedCheque.id}/asignar_movimiento`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ movimiento_id: movimientoId })
      });
      if (res.ok) {
        setShowModalMovimiento(false);
        fetchData();
      } else {
        alert(await res.text());
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDesasignarMovimiento = async (cheque) => {
    if (!window.confirm(`¿Seguro que deseás desvincular el movimiento del cheque #${cheque.numero}?`)) return;
    try {
      const res = await fetch(`/api/cheques/${cheque.id}/desasignar_movimiento`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchData();
      } else {
        alert(await res.text());
      }
    } catch (err) {
      console.error(err);
    }
  };

  const abrirListadoOperaciones = async (cheque) => {
    setSelectedCheque(cheque);
    try {
      const res = await fetch(`/api/cheques/${cheque.id}/operaciones`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if(res.ok) {
        setOperacionesList(await res.json());
        setShowListadoOperaciones(true);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleEditarOperacion = (op) => {
    setEditingOperacionId(op.id);
    setOperacionForm({
      fecha_operacion: op.fecha_operacion,
      operador_cuil: op.operador_cuil,
      tna_descuento: (op.tna_descuento * 100).toFixed(2),
      dias_castigo: op.dias_castigo,
      porcentaje_gastos: (op.porcentaje_gastos * 100).toFixed(2),
      tipo_operacion: op.tipo_operacion
    });
    
    const prevOps = operacionesList.filter(o => o.id < op.id);
    const minFecha = prevOps.length > 0 
       ? prevOps.sort((a,b) => b.id - a.id)[0].fecha_operacion 
       : selectedCheque.fecha_emision;
    setMinFechaOperacion(minFecha);

    setShowListadoOperaciones(false);
    setShowOperarCheque(true);
  };

  const handleBorrarOperacion = async (op) => {
    if(window.confirm('¿Estás seguro de eliminar esta operación?')) {
      try {
        const res = await fetch(`/api/cheques/operaciones/${op.id}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if(res.ok) {
          abrirListadoOperaciones(selectedCheque);
          fetchData();
        } else {
          alert(await res.text());
        }
      } catch (err) {
        console.error(err);
      }
    }
  };

  const abrirModalOperacion = async (cheque) => {
    setSelectedCheque(cheque);
    setEditingOperacionId(null);
    
    let defaultFechaOp = cheque.fecha_emision;
    
    if (cheque.estado !== 'PENDIENTE') {
       try {
         const res = await fetch(`/api/cheques/${cheque.id}/operaciones`, {
           headers: { 'Authorization': `Bearer ${token}` }
         });
         if (res.ok) {
           const ops = await res.json();
           if (ops.length > 0) {
             // sort descending by id or fecha_operacion
             const lastOp = ops.sort((a, b) => b.id - a.id)[0];
             defaultFechaOp = lastOp.fecha_operacion;
           }
         }
       } catch (err) {
         console.error(err);
       }
    }

    setMinFechaOperacion(defaultFechaOp);

    setOperacionForm({ 
      ...initialOperacionForm,
      fecha_operacion: defaultFechaOp
    });
    setShowOperarCheque(true);
  };

  const abrirModalEditar = (cheque) => {
    setEditingChequeId(cheque.id);
    setSelectedCheque(cheque);
    setChequeForm({
      fecha_emision: cheque.fecha_emision,
      fecha_pago: cheque.fecha_pago,
      numero: cheque.numero,
      monto: cheque.monto,
      emisor_cuit: cheque.emisor_cuit,
      banco_id: cheque.banco_id
    });
    setImagenFile(null);
    setShowNuevoCheque(true);
  };

  const handleVerImagen = (cheque) => {
    setSelectedCheque(cheque);
    setImagenFile(null);
    setShowImageModal(true);
  };

  const handleUploadImagenIndependiente = async (e) => {
    e.preventDefault();
    if (!imagenFile) return;
    try {
      const formData = new FormData();
      formData.append('file', imagenFile);
      const res = await fetch(`/api/cheques/${selectedCheque.id}/imagen`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      if(res.ok) {
        alert("Imagen subida correctamente");
        setShowImageModal(false);
        setImagenFile(null);
        fetchData();
      } else {
        alert(await res.text());
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header glass-panel">
        <div>
          <h1 className="page-title">Cartera de Cheques</h1>
          <p className="page-subtitle">Gestión de cheques propios y de terceros</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            className="btn btn-secondary"
            onClick={() => setFilter({ ID: '', Emisor: [], Beneficiario: [], Numero: '', Pago: [], Estado: [] })}
            title="Limpiar todos los filtros"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <FilterX size={16} /> Limpiar Filtros
          </button>
          <button className="btn btn-primary" onClick={() => setShowNuevoCheque(true)}>
            Nuevo Cheque
          </button>
        </div>
      </div>

      <div className="glass-panel" style={{ marginTop: '20px' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('ID')} style={{ textAlign: 'center', cursor: 'pointer', verticalAlign: 'top', padding: '10px 5px' }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '8px', minHeight: '20px' }}>ID <SortIcon columnKey="ID" /></div>
                <div onClick={e => e.stopPropagation()} style={{ padding: '0 2px' }}>
                  <input type="text" placeholder="Filtrar..." value={filter.ID} onChange={e => setFilter({ ...filter, ID: e.target.value })} style={{ width: '100%', marginTop: '5px', padding: '4px 6px', fontSize: '11px', boxSizing: 'border-box', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-color)', color: 'var(--text-color)', height: '26px' }} />
                </div>
              </th>
              <th onClick={() => handleSort('Emisor')} style={{ textAlign: 'center', cursor: 'pointer', verticalAlign: 'top', padding: '10px 5px' }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '8px', minHeight: '20px' }}>Emisor <SortIcon columnKey="Emisor" /></div>
                <div onClick={e => e.stopPropagation()}>
                  <ExcelListFilter availableOptions={AVAILABLE_EMISORES} selectedOptions={filter.Emisor} onChange={val => setFilter({ ...filter, Emisor: val })} title="Filtrar Emisor..." />
                </div>
              </th>
              <th onClick={() => handleSort('Beneficiario')} style={{ textAlign: 'center', cursor: 'pointer', verticalAlign: 'top', padding: '10px 5px' }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '8px', minHeight: '20px' }}>Beneficiario <SortIcon columnKey="Beneficiario" /></div>
                <div onClick={e => e.stopPropagation()}>
                  <ExcelListFilter availableOptions={AVAILABLE_BENEFICIARIOS} selectedOptions={filter.Beneficiario} onChange={val => setFilter({ ...filter, Beneficiario: val })} title="Filtrar Beneficiario..." />
                </div>
              </th>
              <th onClick={() => handleSort('Número')} style={{ textAlign: 'center', cursor: 'pointer', verticalAlign: 'top', padding: '10px 5px' }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '8px', minHeight: '20px' }}>Número <SortIcon columnKey="Número" /></div>
                <div onClick={e => e.stopPropagation()} style={{ padding: '0 2px' }}>
                  <input type="text" placeholder="Filtrar..." value={filter.Numero} onChange={e => setFilter({ ...filter, Numero: e.target.value })} style={{ width: '100%', marginTop: '5px', padding: '4px 6px', fontSize: '11px', boxSizing: 'border-box', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-color)', color: 'var(--text-color)', height: '26px' }} />
                </div>
              </th>
              <th onClick={() => handleSort('Monto')} style={{ textAlign: 'center', cursor: 'pointer', verticalAlign: 'top', padding: '10px 5px' }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '8px', minHeight: '20px' }}>Monto <SortIcon columnKey="Monto" /></div>
                <div style={{ height: '31px' }}></div>
              </th>
              <th onClick={() => handleSort('Pago')} style={{ textAlign: 'center', cursor: 'pointer', verticalAlign: 'top', padding: '10px 5px' }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '8px', minHeight: '20px' }}>Pago <SortIcon columnKey="Pago" /></div>
                <div onClick={e => e.stopPropagation()}>
                  <ExcelDateFilter selectedDates={filter.Pago} onChange={val => setFilter({ ...filter, Pago: val })} availableDates={AVAILABLE_PAGOS} />
                </div>
              </th>
              <th onClick={() => handleSort('Estado')} style={{ textAlign: 'center', cursor: 'pointer', verticalAlign: 'top', padding: '10px 5px' }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '8px', minHeight: '20px' }}>Estado <SortIcon columnKey="Estado" /></div>
                <div onClick={e => e.stopPropagation()}>
                  <ExcelListFilter availableOptions={AVAILABLE_ESTADOS} selectedOptions={filter.Estado} onChange={val => setFilter({ ...filter, Estado: val })} title="Filtrar Estado..." />
                </div>
              </th>
              <th style={{ textAlign: 'center', verticalAlign: 'top', padding: '10px 5px' }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: '8px', minHeight: '20px' }}>Acciones</div>
                <div style={{ height: '31px' }}></div>
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedCheques.map(c => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>{c.emisor?.razon_social} {c.es_propio && <span className="badge">PROPIO</span>}</td>
                <td>{c.beneficiario?.razon_social}</td>
                <td>{c.numero}</td>
                <td style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  ${Number(c.monto).toLocaleString('es-AR', {minimumFractionDigits: 2})}
                </td>
                <td>{c.fecha_pago.split('-').reverse().join('/')}</td>
                <td><span className={`status-badge status-${c.estado.toLowerCase()}`}>{c.estado}</span></td>
                <td>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'nowrap', alignItems: 'center' }}>
                    {c.movimiento_id ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <span className="badge" style={{ backgroundColor: 'var(--success-color)', fontSize: '10px' }} title={`Movimiento Bancario ID: ${c.movimiento_id}`}>
                          🏦 Vinculado
                        </span>
                        <button 
                          className="btn-secondary"
                          style={{ padding: '2px 6px', fontSize: '12px', color: 'var(--danger-color)', border: 'none', background: 'transparent' }}
                          title="Desvincular Movimiento"
                          onClick={() => handleDesasignarMovimiento(c)}
                        >
                          ✖
                        </button>
                      </div>
                    ) : (
                      <>
                        {c.es_propio && c.estado !== 'DEBITADO' && (
                          <button 
                            className="btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }}
                            title="Debitar Cheque"
                            onClick={() => abrirModalMovimiento(c)}
                          >
                            💸
                          </button>
                        )}
                        {!c.es_propio && c.is_beneficiario_empresa && c.estado !== 'ACREDITADO' && (
                          <button 
                            className="btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--success-color)' }}
                            title="Acreditar Cheque"
                            onClick={() => abrirModalMovimiento(c)}
                          >
                            💰
                          </button>
                        )}
                      </>
                    )}
                    <button 
                      className="btn-secondary"
                      style={{ padding: '4px 8px', fontSize: '14px' }}
                      title="Ver/Subir Imagen"
                      onClick={() => handleVerImagen(c)}
                    >
                      🖼️
                    </button>
                    {c.estado !== 'PENDIENTE' && (
                      <button 
                        className="btn-secondary"
                        style={{ padding: '4px 8px', fontSize: '14px' }}
                        title="Ver Operaciones"
                        onClick={() => abrirListadoOperaciones(c)}
                      >
                        📋
                      </button>
                    )}
                    {(c.estado === 'PENDIENTE' || c.estado === 'COMPRADO') && (
                      <button 
                        className="btn-secondary"
                        style={{ padding: '4px 8px', fontSize: '14px' }}
                        title={c.estado === 'PENDIENTE' ? (c.es_propio ? 'Vender' : 'Comprar') : 'Vender'}
                        onClick={() => abrirModalOperacion(c)}
                      >
                        🔄
                      </button>
                    )}
                    {c.estado === 'PENDIENTE' && (
                      <>
                        <button 
                          className="btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '14px' }}
                          title="Editar"
                          onClick={() => abrirModalEditar(c)}
                        >
                          ✏️
                        </button>
                        <button 
                          className="btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }}
                          title="Eliminar"
                          onClick={() => handleBorrarCheque(c.id)}
                        >
                          🗑️
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {cheques.length === 0 && (
              <tr><td colSpan="8" style={{ textAlign: 'center', padding: '20px' }}>No hay cheques en cartera.</td></tr>
            )}
            {filteredAndSortedCheques.length === 0 && (
              <tr><td colSpan="8" style={{ textAlign: 'center', padding: '20px' }}>No hay cheques para los filtros seleccionados</td></tr>
            )}
          </tbody>
          <tfoot>
            <tr style={{ background: 'rgba(255,255,255,0.05)', fontWeight: 'bold' }}>
              <td colSpan="4" style={{ textAlign: 'right', padding: '15px' }}>TOTAL:</td>
              <td style={{ textAlign: 'right', padding: '15px' }}>
                ${totalMonto.toLocaleString('es-AR', {minimumFractionDigits: 2})}
              </td>
              <td colSpan="3"></td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* MODAL NUEVO CHEQUE */}
      {showNuevoCheque && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <h2>{editingChequeId ? 'Editar Cheque' : 'Nuevo Cheque'}</h2>
            </div>
            <form onSubmit={handleCrearCheque}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                <div className="form-group">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <label style={{ margin: 0 }}>Emisor (Quién firmó el cheque)</label>
                    <button type="button" className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '12px' }} onClick={() => setShowNuevoOperador(true)}>
                      + Nuevo
                    </button>
                  </div>
                  <select className="form-control" value={chequeForm.emisor_cuit} onChange={e => setChequeForm({...chequeForm, emisor_cuit: e.target.value})} required>
                    <option value="">Seleccione...</option>
                    {operadores.map(o => <option key={o.cuit} value={o.cuit}>{o.razon_social} ({o.cuit})</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Banco</label>
                  <select className="form-control" value={chequeForm.banco_id} onChange={e => setChequeForm({...chequeForm, banco_id: parseInt(e.target.value) || ''})} required>
                    <option value="">Seleccione Banco...</option>
                    {bancos.map(b => <option key={b.id} value={b.id}>{b.nombre_banco}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Número de Cheque</label>
                  <input type="text" className="form-control" value={chequeForm.numero} onChange={e => setChequeForm({...chequeForm, numero: e.target.value})} required />
                </div>
                <div className="form-group">
                  <label>Monto</label>
                  <CurrencyInput 
                    name="monto" 
                    value={chequeForm.monto} 
                    onChange={(val) => setChequeForm({...chequeForm, monto: val})} 
                    required 
                  />
                </div>
                <div className="form-group">
                  <label>Fecha Emisión</label>
                  <input type="date" className="form-control" value={chequeForm.fecha_emision} onChange={e => setChequeForm({...chequeForm, fecha_emision: e.target.value})} required />
                </div>
                <div className="form-group">
                  <label>Fecha Pago</label>
                  <input type="date" className="form-control" value={chequeForm.fecha_pago} onChange={e => setChequeForm({...chequeForm, fecha_pago: e.target.value})} required />
                </div>
                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                  <label>Imagen del Cheque (Opcional)</label>
                  <input type="file" className="form-control" accept="image/jpeg,image/png,application/pdf" onChange={e => setImagenFile(e.target.files[0])} />
                  {editingChequeId && selectedCheque?.imagen_path && (
                     <small style={{ color: 'var(--text-color)', opacity: 0.8, display: 'block', marginTop: '5px' }}>
                       Ya tiene una imagen subida. Seleccionar una nueva la reemplazará.
                     </small>
                  )}
                </div>
              </div>
              <div className="modal-footer" style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => { setShowNuevoCheque(false); setEditingChequeId(null); setChequeForm(initialChequeForm); setImagenFile(null); }}>Cancelar</button>
                <button type="submit" className="btn btn-primary">{editingChequeId ? 'Guardar Cambios' : 'Crear Cheque'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL NUEVA OPERACION */}
      {showOperarCheque && selectedCheque && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ maxWidth: '900px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="modal-header">
              <h2>{selectedCheque.es_propio ? 'Vender' : 'Comprar'} Cheque #{selectedCheque.numero}</h2>
            </div>
            <div style={{ 
              marginBottom: '20px', 
              padding: '12px 15px', 
              background: 'rgba(255,255,255,0.05)', 
              borderRadius: '8px', 
              border: '1px solid var(--border-color)', 
              display: 'flex', 
              gap: '20px', 
              fontSize: '14px',
              flexWrap: 'wrap'
            }}>
               <div><span style={{color: 'var(--text-color)', opacity: 0.7}}>Emisor:</span> <strong>{selectedCheque.emisor?.razon_social} {selectedCheque.es_propio && <span className="badge">PROPIO</span>}</strong></div>
               <div><span style={{color: 'var(--text-color)', opacity: 0.7}}>Fecha Emisión:</span> <strong>{selectedCheque.fecha_emision.split('-').reverse().join('/')}</strong></div>
               <div><span style={{color: 'var(--text-color)', opacity: 0.7}}>Fecha Pago:</span> <strong>{selectedCheque.fecha_pago.split('-').reverse().join('/')}</strong></div>
               <div><span style={{color: 'var(--text-color)', opacity: 0.7}}>Monto:</span> <strong style={{color: 'var(--success-color)'}}>${Number(selectedCheque.monto).toLocaleString('es-AR', {minimumFractionDigits: 2})}</strong></div>
            </div>
            <form onSubmit={handleOperarCheque}>
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
                
                {/* Columna Izquierda: Inputs */}
                <div>
                  <div className="form-group">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <label style={{ margin: 0 }}>Operador (Con quién se opera)</label>
                      <button type="button" className="btn btn-secondary" style={{ padding: '2px 8px', fontSize: '12px' }} onClick={() => setShowNuevoOperador(true)}>
                        + Nuevo
                      </button>
                    </div>
                    <select className="form-control" value={operacionForm.operador_cuil} onChange={e => setOperacionForm({...operacionForm, operador_cuil: e.target.value})} required>
                      <option value="">Seleccione...</option>
                      {operadores.map(o => <option key={o.cuit} value={o.cuit}>{o.razon_social} ({o.cuit})</option>)}
                    </select>
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                    <div className="form-group">
                      <label>TNA (Descuento)</label>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <input type="number" step="0.01" className="form-control" value={operacionForm.tna_descuento} onChange={e => setOperacionForm({...operacionForm, tna_descuento: e.target.value})} required />
                        <span style={{ fontWeight: 'bold' }}>%</span>
                      </div>
                    </div>
                    
                    <div className="form-group">
                      <label>% Gastos</label>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <input type="number" step="0.01" className="form-control" value={operacionForm.porcentaje_gastos} onChange={e => setOperacionForm({...operacionForm, porcentaje_gastos: e.target.value})} required />
                        <span style={{ fontWeight: 'bold' }}>%</span>
                      </div>
                    </div>
                    
                    <div className="form-group">
                      <label>Fecha Operación</label>
                      <input type="date" className="form-control" value={operacionForm.fecha_operacion} min={minFechaOperacion} onChange={e => setOperacionForm({...operacionForm, fecha_operacion: e.target.value})} required />
                    </div>
                    
                    {(!selectedCheque?.es_propio) ? (
                      <div className="form-group">
                        <label>Días Castigo</label>
                        <input type="number" className="form-control" value={operacionForm.dias_castigo} onChange={e => setOperacionForm({...operacionForm, dias_castigo: e.target.value})} required />
                      </div>
                    ) : (
                      <div /> /* Empty div */
                    )}
                  </div>
                </div>

                {/* Columna Derecha: Vista Previa */}
                <div>
                  {(() => {
                    const monto = parseFloat(selectedCheque.monto) || 0;
                    const tna = parseFloat(operacionForm.tna_descuento) / 100 || 0;
                    const gastos_pct = parseFloat(operacionForm.porcentaje_gastos) / 100 || 0;
                    const castigo = parseInt(operacionForm.dias_castigo) || 0;
                    
                    let plazo = 0;
                    if (operacionForm.fecha_operacion && selectedCheque.fecha_pago) {
                      const [oYear, oMonth, oDay] = operacionForm.fecha_operacion.split('-');
                      const fechaOp = new Date(oYear, oMonth - 1, oDay);
                      const [pYear, pMonth, pDay] = selectedCheque.fecha_pago.split('-');
                      const fechaPago = new Date(pYear, pMonth - 1, pDay);
                      plazo = Math.ceil((fechaPago.getTime() - fechaOp.getTime()) / (1000 * 60 * 60 * 24));
                      if (plazo < 0) plazo = 0;
                    }

                    const gastos = monto * gastos_pct;
                    const dias_totales = plazo + castigo;
                    const valor_actual = monto / (1 + (tna / 365) * dias_totales);
                    const intereses = monto - valor_actual;
                    const iva = (intereses + gastos) * 0.21;
                    const monto_descontado = intereses + gastos + iva;
                    const importe_neto = monto - monto_descontado;

                    const formatter = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' });

                    return (
                      <div style={{ 
                        height: '100%',
                        padding: '15px', 
                        background: 'rgba(0,0,0,0.2)', 
                        borderRadius: '8px', 
                        border: '1px solid var(--border-color)',
                        fontSize: '14px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center'
                      }}>
                        <h4 style={{ margin: '0 0 15px 0', fontSize: '15px', color: 'var(--primary-color)', textAlign: 'center' }}>Vista Previa de Liquidación</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>Plazo Calculado:</span> <strong>{plazo} días</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>Valor Nominal:</span> <strong>{formatter.format(monto)}</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>Intereses:</span> <strong style={{ color: 'var(--danger-color)' }}>- {formatter.format(intereses)}</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>Gastos:</span> <strong style={{ color: 'var(--danger-color)' }}>- {formatter.format(gastos)}</strong>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>IVA (21%):</span> <strong style={{ color: 'var(--danger-color)' }}>- {formatter.format(iva)}</strong>
                          </div>
                        </div>
                        <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '15px 0' }} />
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '16px', fontWeight: 'bold' }}>
                          <span>Neto a {selectedCheque.es_propio ? 'Recibir' : 'Pagar'}:</span> 
                          <span style={{ color: 'var(--success-color)' }}>{formatter.format(importe_neto)}</span>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => { setShowOperarCheque(false); setOperacionForm(initialOperacionForm); }}>Cancelar</button>
                <button type="submit" className="btn btn-primary">Registrar Operación</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL NUEVO OPERADOR */}
      {showNuevoOperador && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <h2>Nuevo Emisor/Operador</h2>
            </div>
            <form onSubmit={handleCrearOperador}>
              <div className="form-group">
                <label>CUIT (11 dígitos sin guiones)</label>
                <input type="text" className="form-control" maxLength="11" value={operadorForm.cuit} onChange={e => setOperadorForm({...operadorForm, cuit: e.target.value})} required />
              </div>
              <div className="form-group">
                <label>Razón Social</label>
                <input type="text" className="form-control" value={operadorForm.razon_social} onChange={e => setOperadorForm({...operadorForm, razon_social: e.target.value})} required />
              </div>
              <div className="form-group">
                <label>Calificación</label>
                <select className="form-control" value={operadorForm.calificacion} onChange={e => setOperadorForm({...operadorForm, calificacion: e.target.value})} required>
                  <option value="EXCELENTE">EXCELENTE</option>
                  <option value="BUENO">BUENO</option>
                  <option value="REGULAR">REGULAR</option>
                  <option value="MALO">MALO</option>
                  <option value="RECHAZADO">RECHAZADO</option>
                </select>
              </div>
              <div className="form-group">
                <label>Teléfono</label>
                <input type="text" className="form-control" value={operadorForm.telefono} onChange={e => setOperadorForm({...operadorForm, telefono: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input type="email" className="form-control" value={operadorForm.email} onChange={e => setOperadorForm({...operadorForm, email: e.target.value})} />
              </div>
              <div className="modal-footer" style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => { setShowNuevoOperador(false); setOperadorForm(initialOperadorForm); }}>Cancelar</button>
                <button type="submit" className="btn btn-primary">Crear</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL VER/SUBIR IMAGEN */}
      {showImageModal && selectedCheque && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h2>Imagen del Cheque #{selectedCheque.numero}</h2>
            </div>
            
            {selectedCheque.imagen_path ? (
               <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                  {selectedCheque.imagen_path.endsWith('.pdf') ? (
                     <a href={`/static/${selectedCheque.imagen_path}`} target="_blank" rel="noreferrer" className="btn btn-primary" style={{ display: 'inline-block' }}>
                        Abrir PDF en nueva pestaña
                     </a>
                  ) : (
                     <img src={`/static/${selectedCheque.imagen_path}`} alt="Cheque" style={{ maxWidth: '100%', maxHeight: '400px', borderRadius: '8px' }} />
                  )}
               </div>
            ) : (
               <p style={{ textAlign: 'center', color: 'var(--text-color)', opacity: 0.8, marginBottom: '20px' }}>
                  No hay imagen subida para este cheque.
               </p>
            )}

            <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '20px 0' }} />
            
            <form onSubmit={handleUploadImagenIndependiente}>
              <div className="form-group">
                <label>{selectedCheque.imagen_path ? 'Reemplazar Imagen' : 'Subir Imagen'}</label>
                <input type="file" className="form-control" accept="image/jpeg,image/png,application/pdf" onChange={e => setImagenFile(e.target.files[0])} required />
              </div>
              <div className="modal-footer" style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => { setShowImageModal(false); setImagenFile(null); }}>Cerrar</button>
                <button type="submit" className="btn btn-primary">Subir</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* MODAL LISTADO OPERACIONES */}
      {showListadoOperaciones && selectedCheque && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ maxWidth: '1000px', padding: '30px' }}>
            <div className="modal-header" style={{ marginBottom: '20px' }}>
              <h2>Operaciones del Cheque #{selectedCheque.numero}</h2>
              <button className="btn-secondary" onClick={() => setShowListadoOperaciones(false)}>Cerrar</button>
            </div>
            {operacionesList.length === 0 ? (
              <p>No hay operaciones registradas.</p>
            ) : (
              <div className="table-responsive" style={{ overflowX: 'auto', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', padding: '10px' }}>
                {(() => {
                  const formatter = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' });
                  return (
                    <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 8px' }}>
                      <thead>
                    <tr>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Fecha Op.</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Tipo</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Operador</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>TNA</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Plazo</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Interés</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Gastos</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>IVA</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Desc. Total</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Neto</th>
                      <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {operacionesList.map(op => (
                      <tr key={op.id} style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '8px', fontSize: '13px' }}>
                        <td style={{ padding: '15px 12px' }}>{op.fecha_operacion.split('-').reverse().join('/')}</td>
                        <td style={{ padding: '15px 12px' }}><span className={`badge`} style={{ background: op.tipo_operacion === 'COMPRA' ? 'var(--primary-color)' : 'var(--secondary-color)', fontSize: '11px'}}>{op.tipo_operacion}</span></td>
                        <td style={{ padding: '15px 12px', fontWeight: 'bold' }}>{operadores.find(o => o.cuit === op.operador_cuil)?.razon_social || op.operador_cuil}</td>
                        <td style={{ padding: '15px 12px', textAlign: 'right' }}>{(op.tna_descuento * 100).toFixed(2)}%</td>
                        <td style={{ padding: '15px 12px', textAlign: 'right' }}>{op.plazo_dias + op.dias_castigo} d</td>
                        <td style={{ padding: '15px 12px', textAlign: 'right', color: 'var(--danger-color)' }}>{formatter.format(op.intereses)}</td>
                        <td style={{ padding: '15px 12px', textAlign: 'right', color: 'var(--danger-color)' }}>{formatter.format(op.gastos)} <br/><span style={{fontSize: '10px', opacity: 0.7}}>({(op.porcentaje_gastos * 100).toFixed(2)}%)</span></td>
                        <td style={{ padding: '15px 12px', textAlign: 'right', color: 'var(--danger-color)' }}>{formatter.format(op.iva)}</td>
                        <td style={{ padding: '15px 12px', textAlign: 'right', fontWeight: 'bold', color: 'var(--danger-color)' }}>{formatter.format(op.monto_descontado)}</td>
                        <td style={{ padding: '15px 12px', textAlign: 'right', fontWeight: 'bold', color: 'var(--success-color)' }}>{formatter.format(op.importe_neto_recibir)}</td>
                        <td style={{ padding: '15px 12px' }}>
                          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                            <button className="btn-secondary" style={{ padding: '6px 10px', fontSize: '15px' }} title="Editar" onClick={() => handleEditarOperacion(op)}>✏️</button>
                            <button className="btn-secondary" style={{ padding: '6px 10px', fontSize: '15px', color: 'var(--danger-color)' }} title="Eliminar" onClick={() => handleBorrarOperacion(op)}>🗑️</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                  );
                })()}
              </div>
            )}
          </div>
        </div>
      )}
      {/* MODAL ASIGNAR MOVIMIENTO */}
      {showModalMovimiento && selectedCheque && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="modal-header" style={{ marginBottom: '20px' }}>
              <h2>Asignar Movimiento Bancario - Cheque #{selectedCheque.numero}</h2>
              <button className="btn-secondary" onClick={() => setShowModalMovimiento(false)}>Cerrar</button>
            </div>
            
            <div style={{ marginBottom: '15px' }}>
              <input 
                type="text" 
                className="form-control" 
                placeholder="Buscar movimiento por descripción, monto..." 
                value={movimientoSearch}
                onChange={(e) => setMovimientoSearch(e.target.value)}
              />
            </div>
            
            {loadingMovimientos ? (
              <p>Cargando movimientos bancarios...</p>
            ) : movimientos.length === 0 ? (
              <p>No se encontraron movimientos bancarios recientes.</p>
            ) : (
              <div className="table-responsive" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                <table className="data-table" style={{ width: '100%', fontSize: '13px' }}>
                  <thead style={{ position: 'sticky', top: 0, zIndex: 1, background: 'var(--surface-color)' }}>
                    <tr>
                      <th>Fecha</th>
                      <th>Banco/Cuenta</th>
                      <th>Concepto</th>
                      <th>Nro. Comp</th>
                      <th>Monto</th>
                      <th>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {movimientos
                      .filter(m => {
                        const searchLower = movimientoSearch.toLowerCase();
                        return (
                          (m.descripcion || '').toLowerCase().includes(searchLower) ||
                          (m.monto || '').toString().includes(searchLower) ||
                          (m.concepto?.name || '').toLowerCase().includes(searchLower) ||
                          (m.nro_comprobante || '').toLowerCase().includes(searchLower)
                        );
                      })
                      .map(m => (
                      <tr key={m.id}>
                        <td>{m.fecha?.split('-').reverse().join('/')}</td>
                        <td>{m.cuenta?.banco?.nombre_banco} ({m.cuenta?.nro})</td>
                        <td>
                          {m.concepto?.name}
                          {m.descripcion && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{m.descripcion}</div>}
                        </td>
                        <td>{m.nro_comprobante || '-'}</td>
                        <td style={{ color: m.monto < 0 ? 'var(--danger-color)' : 'var(--success-color)', fontWeight: 'bold' }}>
                          ${Number(m.monto).toLocaleString('es-AR', {minimumFractionDigits: 2})}
                        </td>
                        <td>
                          <button 
                            className="btn btn-primary" 
                            style={{ padding: '4px 10px', fontSize: '12px' }}
                            onClick={() => handleAsignarMovimiento(m.id)}
                          >
                            Seleccionar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
};

export default ChequesPage;
