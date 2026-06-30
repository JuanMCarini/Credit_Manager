import { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import useAppStore from '../store/useAppStore';
import ExportExcelButton from '../components/ExportExcelButton';
import ExcelNumberRangeFilter from '../components/ExcelNumberRangeFilter';

const PortfolioOriginationPage = () => {
  const { editingCompra, setEditingCompra } = useAppStore();
  const [tipoOperacion, setTipoOperacion] = useState('VENTA');
  const [socios, setSocios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState({ type: '', message: '' });
  
  // Preview Modal State
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [previewTab, setPreviewTab] = useState('resumen'); // 'creditos', 'cuotas', 'resumen'
  const [filterCreditos, setFilterCreditos] = useState({});
  const [filterCuotas, setFilterCuotas] = useState({});
  const [filterResumen, setFilterResumen] = useState({});
  const [showPreviewEstadoFilter, setShowPreviewEstadoFilter] = useState(false);
  const [showPreviewIncluidaFilter, setShowPreviewIncluidaFilter] = useState(false);
  const [showPreviewCompradaFilter, setShowPreviewCompradaFilter] = useState(false);
  const [creditosExcluidos, setCreditosExcluidos] = useState([]);

  // New Socio Modal State
  const [showNewSocioModal, setShowNewSocioModal] = useState(false);
  const [creatingSocio, setCreatingSocio] = useState(false);
  const [newSocio, setNewSocio] = useState({
    razon_social: '', cuit: '', domicilio_legal: '', contacto_nombre: '', mail: '', telefono: '', dia_corte: ''
  });

  // Form Venta
  const [ventaData, setVentaData] = useState({
    nombre: '', fecha: '', tna: '', socio: '',
    emision_desde: '', emision_hasta: '', vto_desde: '', vto_hasta: '',
    mora: false, recurso: true, iva: false, cuotas_completas: true,
  });

  // Form Compra
  const [compraData, setCompraData] = useState({
    nombre: '', fecha: '', tna: '', socio: '',
    personasCsv: null, prestamosCsv: null, cuotasCsv: null
  });

  useEffect(() => {
    const loadSocios = async () => {
      try {
        const res = await axiosClient.get('/api/v1/auxiliares/socios');
        setSocios(res.data);
      } catch (err) {
        console.error("Error loading socios:", err);
      }
    };
    loadSocios();
  }, []);

  useEffect(() => {
    if (editingCompra && socios.length > 0) {
      setTipoOperacion('COMPRA');
      
      const socioMatch = socios.find(s => s.razon_social === editingCompra.socio || s.cuit === editingCompra.cuit_vendedor);
      
      setCompraData({
        ...compraData,
        nombre: editingCompra.nombre || '',
        fecha: editingCompra.fecha_compra || '',
        tna: editingCompra.tna_descuento ? (editingCompra.tna_descuento * 100).toFixed(2) : '',
        socio: socioMatch ? socioMatch.id : ''
      });
    }
  }, [editingCompra, socios]);

  const handleConfirmVenta = async (e) => {
    e.preventDefault();
    setLoading(true);
    setFeedback({ type: '', message: '' });

    try {
      const selectedSocio = socios.find(s => s.id === parseInt(ventaData.socio));
      const payload = {
        creditos_excluidos: creditosExcluidos,
        nombre_cartera: ventaData.nombre,
        fecha_venta: ventaData.fecha,
        tna_descuento: parseFloat(ventaData.tna) / 100, // as decimal
        cuit_comprador: selectedSocio ? selectedSocio.cuit : '',
        razon_social_comprador: selectedSocio ? selectedSocio.razon_social : '',
        mora: ventaData.mora,
        recurso: ventaData.recurso,
        iva: ventaData.iva,
        cuotas_completas: ventaData.cuotas_completas,
        fecha_emision_desde: ventaData.emision_desde || null,
        fecha_emision_hasta: ventaData.emision_hasta || null,
        fecha_vencimiento_desde: ventaData.vto_desde || null,
        fecha_vencimiento_hasta: ventaData.vto_hasta || null,
      };

      const res = await axiosClient.post('/api/v1/carteras/venta', payload);
      setFeedback({ type: 'success', message: `Venta registrada con éxito. ID: ${res.data.message || res.data.id}` });
      setShowPreviewModal(false);
    } catch (error) {
      const msg = error.response?.data?.detail || error.message;
      setFeedback({ type: 'error', message: `Error: ${msg}` });
    } finally {
      setLoading(false);
    }
  };

  const handleSimularVenta = async (e) => {
    if (e) e.preventDefault();
    if (!ventaData.socio) {
        setFeedback({ type: 'error', message: 'Debe seleccionar un socio comercial' });
        return;
    }
    setLoading(true);
    setFeedback({ type: '', message: '' });

    try {
      const selectedSocio = socios.find(s => s.id === parseInt(ventaData.socio));
      const payload = {
        creditos_excluidos: creditosExcluidos,
        nombre_cartera: ventaData.nombre,
        fecha_venta: ventaData.fecha,
        tna_descuento: parseFloat(ventaData.tna) / 100,
        cuit_comprador: selectedSocio ? selectedSocio.cuit : '',
        razon_social_comprador: selectedSocio ? selectedSocio.razon_social : '',
        mora: ventaData.mora,
        recurso: ventaData.recurso,
        iva: ventaData.iva,
        cuotas_completas: ventaData.cuotas_completas,
        fecha_emision_desde: ventaData.emision_desde || null,
        fecha_emision_hasta: ventaData.emision_hasta || null,
        fecha_vencimiento_desde: ventaData.vto_desde || null,
        fecha_vencimiento_hasta: ventaData.vto_hasta || null,
      };

      const res = await axiosClient.post('/api/v1/carteras/venta/preview', payload);
      setPreviewData(res.data);
      setShowPreviewModal(true);
    } catch (error) {
      const msg = error.response?.data?.detail || error.message;
      setFeedback({ type: 'error', message: `Error en simulación: ${msg}` });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleExcluir = (id) => {
    setCreditosExcluidos(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  useEffect(() => {
    if (showPreviewModal && tipoOperacion === 'VENTA' && ventaData.socio && !loading && !previewData) {
      // Avoid infinite loop by checking if previewData is null
      handleSimularVenta();
    }
  }, [creditosExcluidos]);

  const handleConfirmCompra = async (e) => {
    if (e) e.preventDefault();
    if (!compraData.personasCsv || !compraData.prestamosCsv || !compraData.cuotasCsv) {
      setFeedback({ type: 'error', message: 'Debe cargar los 3 archivos CSV para la compra.' });
      return;
    }
    setLoading(true);
    setFeedback({ type: '', message: '' });

    const selectedSocio = socios.find(s => s.id === parseInt(compraData.socio));
    const formData = new FormData();
    formData.append('nombre_cartera', compraData.nombre);
    formData.append('fecha_compra', compraData.fecha);
    formData.append('tna_descuento', parseFloat(compraData.tna) / 100);
    formData.append('cuit_vendedor', selectedSocio ? selectedSocio.cuit : '');
    formData.append('razon_social_vendedor', selectedSocio ? selectedSocio.razon_social : '');
    formData.append('personas_csv', compraData.personasCsv);
    formData.append('prestamos_csv', compraData.prestamosCsv);
    formData.append('cuotas_csv', compraData.cuotasCsv);

    try {
      if (editingCompra) {
        await axiosClient.delete(`/api/v1/carteras/${editingCompra.id}`);
      }
      const res = await axiosClient.post('/api/v1/carteras/compra', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setFeedback({ type: 'success', message: res.data.message || `Compra ${editingCompra ? 'actualizada' : 'registrada'} con éxito.` });
      setShowPreviewModal(false);
      setEditingCompra(null);
      setCompraData({ nombre: '', fecha: '', tna: '', socio: '', personasCsv: null, prestamosCsv: null, cuotasCsv: null });
    } catch (error) {
      const data = error.response?.data;
      const msg = data?.detail || error.message;
      const fileName = data?.report_file;

      if (fileName) {
        setFeedback({ 
          type: 'error', 
          message: (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <span>Error: {msg}</span>
              <button 
                type="button" 
                onClick={() => downloadReport(fileName)} 
                className="btn-primary"
                style={{ width: 'fit-content', backgroundColor: 'var(--danger-color)', border: 'none' }}
              >
                Descargar Reporte de Errores
              </button>
            </div>
          ) 
        });
      } else {
        setFeedback({ type: 'error', message: `Error: ${msg}` });
      }
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = async (fileName) => {
    try {
      const response = await axiosClient.get(`/api/v1/carteras/compra/reportes/${fileName}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

      if (window.showSaveFilePicker) {
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: fileName,
            types: [{
              description: 'Archivo Excel',
              accept: {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']},
            }],
          });
          const writable = await handle.createWritable();
          await writable.write(blob);
          await writable.close();
          return;
        } catch (err) {
          if (err.name === 'AbortError') return;
          console.error("SaveFilePicker fallback:", err);
        }
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Error al descargar el reporte.");
    }
  };

  const handleSimularCompra = async (e) => {
    if (e) e.preventDefault();
    if (!compraData.personasCsv || !compraData.prestamosCsv || !compraData.cuotasCsv) {
      setFeedback({ type: 'error', message: 'Debe cargar los 3 archivos CSV para la compra.' });
      return;
    }
    if (!compraData.socio) {
        setFeedback({ type: 'error', message: 'Debe seleccionar un socio comercial' });
        return;
    }
    setLoading(true);
    setFeedback({ type: '', message: '' });

    const selectedSocio = socios.find(s => s.id === parseInt(compraData.socio));
    const formData = new FormData();
    formData.append('nombre_cartera', compraData.nombre);
    formData.append('fecha_compra', compraData.fecha);
    formData.append('tna_descuento', parseFloat(compraData.tna) / 100);
    formData.append('cuit_vendedor', selectedSocio ? selectedSocio.cuit : '');
    formData.append('razon_social_vendedor', selectedSocio ? selectedSocio.razon_social : '');
    formData.append('personas_csv', compraData.personasCsv);
    formData.append('prestamos_csv', compraData.prestamosCsv);
    formData.append('cuotas_csv', compraData.cuotasCsv);

    try {
      const res = await axiosClient.post('/api/v1/carteras/compra/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setPreviewData(res.data);
      setPreviewTab('resumen');
      setShowPreviewModal(true);
    } catch (error) {
      const data = error.response?.data;
      const msg = data?.detail || error.message;
      const fileName = data?.report_file;

      if (fileName) {
        setFeedback({ 
          type: 'error', 
          message: (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <span>Error en simulación: {msg}</span>
              <button 
                type="button" 
                onClick={() => downloadReport(fileName)} 
                className="btn-primary"
                style={{ width: 'fit-content', backgroundColor: 'var(--danger-color)', border: 'none' }}
              >
                Descargar Reporte de Errores
              </button>
            </div>
          ) 
        });
      } else {
        setFeedback({ type: 'error', message: `Error en simulación: ${msg}` });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSocio = async (e) => {
    e.preventDefault();
    setCreatingSocio(true);
    try {
      const payload = {
        ...newSocio,
        dia_corte: newSocio.dia_corte ? parseInt(newSocio.dia_corte, 10) : null
      };
      const res = await axiosClient.post('/api/v1/auxiliares/socios', payload);
      
      // Reload socios
      const sociosRes = await axiosClient.get('/api/v1/auxiliares/socios');
      setSocios(sociosRes.data);
      
      // Auto-select the newly created socio
      if (tipoOperacion === 'VENTA') setVentaData({...ventaData, socio: res.data.id});
      else setCompraData({...compraData, socio: res.data.id});
      
      setShowNewSocioModal(false);
      setNewSocio({ razon_social: '', cuit: '', domicilio_legal: '', contacto_nombre: '', mail: '', telefono: '', dia_corte: '' });
      setFeedback({ type: 'success', message: 'Socio Comercial agregado exitosamente.' });
    } catch (error) {
      const msg = error.response?.data?.detail || error.message;
      alert("Error al crear socio: " + msg);
    } finally {
      setCreatingSocio(false);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Nueva Operación de Cartera</h2>
        <p>Ingrese los datos para registrar una nueva venta o compra de cartera.</p>
      </header>

      <div className="glass-panel" style={{ maxWidth: '800px', margin: '0 auto', padding: '32px' }}>
        <div className="form-group" style={{ marginBottom: '32px' }}>
          <label style={{ fontSize: '1.1em', marginBottom: '8px' }}>Seleccione el Tipo de Operación</label>
          <select value={tipoOperacion} onChange={(e) => { setTipoOperacion(e.target.value); setFeedback({type: '', message: ''}); }} className="input-field" style={{ fontSize: '1.1em', padding: '12px' }}>
            <option value="VENTA">Venta de Cartera</option>
            <option value="COMPRA">Compra de Cartera {editingCompra ? '(Edición)' : ''}</option>
          </select>
        </div>

        {tipoOperacion === 'VENTA' && (
          <form onSubmit={handleSimularVenta}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
              <div className="form-group">
                <label>Nombre de Cartera</label>
                <input type="text" className="input-field" required value={ventaData.nombre} onChange={(e) => setVentaData({...ventaData, nombre: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Fecha de Venta</label>
                <input type="date" className="input-field" required value={ventaData.fecha} onChange={(e) => setVentaData({...ventaData, fecha: e.target.value})} />
              </div>
              <div className="form-group">
                <label>TNA Descuento (%)</label>
                <input type="number" step="0.01" className="input-field" required value={ventaData.tna} onChange={(e) => setVentaData({...ventaData, tna: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Socio Comercial (Comprador)</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <select className="input-field" required value={ventaData.socio} onChange={(e) => setVentaData({...ventaData, socio: e.target.value})} style={{ flex: 1 }}>
                    <option value="" disabled>Seleccione socio...</option>
                    {socios.map(s => <option key={s.id} value={s.id}>{s.razon_social}</option>)}
                  </select>
                  <button type="button" className="btn-secondary" onClick={() => setShowNewSocioModal(true)} style={{ padding: '0 12px' }}>
                    + Nuevo
                  </button>
                </div>
              </div>

              {/* Filtros de Fechas */}
              <div className="form-group">
                <label>Emisión Crédito Desde</label>
                <input type="date" className="input-field" required value={ventaData.emision_desde} onChange={(e) => setVentaData({...ventaData, emision_desde: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Emisión Crédito Hasta</label>
                <input type="date" className="input-field" required value={ventaData.emision_hasta} onChange={(e) => setVentaData({...ventaData, emision_hasta: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Vencimiento Cuota Desde</label>
                <input type="date" className="input-field" required value={ventaData.vto_desde} onChange={(e) => setVentaData({...ventaData, vto_desde: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Vencimiento Cuota Hasta</label>
                <input type="date" className="input-field" required value={ventaData.vto_hasta} onChange={(e) => setVentaData({...ventaData, vto_hasta: e.target.value})} />
              </div>

              {/* Switches */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '24px', gridColumn: 'span 2', background: 'rgba(255,255,255,0.05)', padding: '24px', borderRadius: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '12px', fontWeight: 500, cursor: 'pointer' }}>
                  <div className="toggle-switch">
                    <input type="checkbox" checked={ventaData.mora} onChange={(e) => setVentaData({...ventaData, mora: e.target.checked})} />
                    <span className="slider"></span>
                  </div>
                  Incluir Mora
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '12px', fontWeight: 500, cursor: 'pointer' }}>
                  <div className="toggle-switch">
                    <input type="checkbox" checked={ventaData.recurso} onChange={(e) => setVentaData({...ventaData, recurso: e.target.checked})} />
                    <span className="slider"></span>
                  </div>
                  Con Recurso
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '12px', fontWeight: 500, cursor: 'pointer' }}>
                  <div className="toggle-switch">
                    <input type="checkbox" checked={ventaData.iva} onChange={(e) => setVentaData({...ventaData, iva: e.target.checked})} />
                    <span className="slider"></span>
                  </div>
                  Incluir IVA
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '12px', fontWeight: 500, cursor: 'pointer' }}>
                  <div className="toggle-switch">
                    <input type="checkbox" checked={ventaData.cuotas_completas} onChange={(e) => setVentaData({...ventaData, cuotas_completas: e.target.checked})} />
                    <span className="slider"></span>
                  </div>
                  Cuotas Completas
                </label>
              </div>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '16px', marginTop: '32px', paddingTop: '24px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
              <button type="submit" className="btn-primary" style={{ padding: '12px 32px', fontSize: '1.1em' }} disabled={loading}>
                {loading ? 'Procesando...' : 'Simular Venta'}
              </button>
            </div>
          </form>
        )}

        {tipoOperacion === 'COMPRA' && (
          <form onSubmit={handleSimularCompra}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>
              <div className="form-group">
                <label>Nombre de Cartera</label>
                <input type="text" className="input-field" required value={compraData.nombre} onChange={(e) => setCompraData({...compraData, nombre: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Fecha de Compra</label>
                <input type="date" className="input-field" required value={compraData.fecha} onChange={(e) => setCompraData({...compraData, fecha: e.target.value})} />
              </div>
              <div className="form-group">
                <label>TNA Descuento (%)</label>
                <input type="number" step="0.01" className="input-field" required value={compraData.tna} onChange={(e) => setCompraData({...compraData, tna: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Socio Comercial (Vendedor)</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <select className="input-field" required value={compraData.socio} onChange={(e) => setCompraData({...compraData, socio: e.target.value})} style={{ flex: 1 }}>
                    <option value="" disabled>Seleccione socio...</option>
                    {socios.map(s => <option key={s.id} value={s.id}>{s.razon_social}</option>)}
                  </select>
                  <button type="button" className="btn-secondary" onClick={() => setShowNewSocioModal(true)} style={{ padding: '0 12px' }}>
                    + Nuevo
                  </button>
                </div>
              </div>
            </div>

            <div style={{ marginBottom: '24px', background: 'rgba(0,0,0,0.2)', padding: '24px', borderRadius: '8px' }}>
              <h4 style={{ marginBottom: '16px', fontSize: '1.1em' }}>Archivos a Importar (CSV)</h4>
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Personas (personas.csv)</label>
                <input type="file" accept=".csv" className="input-field" required onChange={(e) => setCompraData({...compraData, personasCsv: e.target.files[0]})} />
              </div>
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label>Préstamos (prestamos.csv)</label>
                <input type="file" accept=".csv" className="input-field" required onChange={(e) => setCompraData({...compraData, prestamosCsv: e.target.files[0]})} />
              </div>
              <div className="form-group">
                <label>Cuotas (cuotas.csv)</label>
                <input type="file" accept=".csv" className="input-field" required onChange={(e) => setCompraData({...compraData, cuotasCsv: e.target.files[0]})} />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '16px', marginTop: '32px', paddingTop: '24px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
              {editingCompra && (
                <button type="button" onClick={() => { setEditingCompra(null); setTipoOperacion('VENTA'); }} className="btn-secondary" style={{ padding: '12px 32px', fontSize: '1.1em' }} disabled={loading}>
                  Cancelar Edición
                </button>
              )}
              <button type="submit" className="btn-primary" style={{ padding: '12px 32px', fontSize: '1.1em' }} disabled={loading}>
                {loading ? 'Procesando...' : (editingCompra ? 'Re-Simular Compra' : 'Simular Compra')}
              </button>
            </div>
          </form>
        )}

        {feedback.message && (
          <div style={{ marginTop: '24px', padding: '16px', borderRadius: '8px', fontSize: '15px', fontWeight: 500, backgroundColor: feedback.type === 'error' ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)', color: feedback.type === 'error' ? 'var(--danger-color)' : 'var(--success-color)' }}>
            {feedback.message}
          </div>
        )}

      </div>

      {showNewSocioModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
          backdropFilter: 'blur(4px)'
        }}>
          <div className="glass-panel" style={{
            width: '100%', maxWidth: '500px', padding: '32px', position: 'relative',
            maxHeight: '90vh', overflowY: 'auto'
          }}>
            <button onClick={() => setShowNewSocioModal(false)} className="btn-secondary" style={{
              position: 'absolute', top: '16px', right: '16px', padding: '4px 12px'
            }}>X</button>
            <h3 style={{ marginBottom: '24px', fontFamily: 'var(--font-heading)' }}>Nuevo Socio Comercial</h3>
            
            <form onSubmit={handleCreateSocio} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="form-group">
                <label>Razón Social *</label>
                <input type="text" className="input-field" required value={newSocio.razon_social} onChange={(e) => setNewSocio({...newSocio, razon_social: e.target.value})} />
              </div>
              <div className="form-group">
                <label>CUIT (Solo números) *</label>
                <input type="text" className="input-field" required value={newSocio.cuit} onChange={(e) => setNewSocio({...newSocio, cuit: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Día de Corte *</label>
                <input type="number" className="input-field" required min="1" max="31" value={newSocio.dia_corte} onChange={(e) => setNewSocio({...newSocio, dia_corte: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Domicilio Legal</label>
                <input type="text" className="input-field" value={newSocio.domicilio_legal} onChange={(e) => setNewSocio({...newSocio, domicilio_legal: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Contacto (Nombre)</label>
                <input type="text" className="input-field" value={newSocio.contacto_nombre} onChange={(e) => setNewSocio({...newSocio, contacto_nombre: e.target.value})} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="form-group">
                  <label>Email</label>
                  <input type="email" className="input-field" value={newSocio.mail} onChange={(e) => setNewSocio({...newSocio, mail: e.target.value})} />
                </div>
                <div className="form-group">
                  <label>Teléfono</label>
                  <input type="text" className="input-field" value={newSocio.telefono} onChange={(e) => setNewSocio({...newSocio, telefono: e.target.value})} />
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
                <button type="button" onClick={() => setShowNewSocioModal(false)} className="btn-secondary">Cancelar</button>
                <button type="submit" className="btn-primary" disabled={creatingSocio}>
                  {creatingSocio ? 'Creando...' : 'Crear Socio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showPreviewModal && previewData && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.8)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '10px',
          backdropFilter: 'blur(8px)'
        }}>
          <div className="glass-panel" style={{
            width: '100%', maxWidth: '1200px', height: '95vh', display: 'flex', flexDirection: 'column', position: 'relative'
          }}>
            <button onClick={() => setShowPreviewModal(false)} className="btn-secondary" style={{
              position: 'absolute', top: '16px', right: '16px', padding: '4px 12px', zIndex: 10
            }}>X</button>
            
            <div style={{ padding: '16px 24px 0' }}>
              <h3 style={{ marginBottom: '8px', fontFamily: 'var(--font-heading)' }}>
                Simulación de {tipoOperacion === 'VENTA' ? 'Venta' : 'Compra'} de Cartera
              </h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
                Revise los créditos y cuotas {tipoOperacion === 'VENTA' ? 'que serán cedidos' : 'importados'} antes de confirmar la operación.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Créditos Involucrados</div>
                  <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{previewData.creditos.length}</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.05)', padding: '16px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Cuotas a {tipoOperacion === 'VENTA' ? 'Ceder' : 'Adquirir'}</div>
                  <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
                    {tipoOperacion === 'VENTA' ? previewData.cuotas.filter(c => c.incluida).length : previewData.cuotas.filter(c => c.comprada).length}
                  </div>
                </div>
                <div style={{ background: 'var(--accent-glow)', padding: '16px', borderRadius: '8px', textAlign: 'center', border: '1px solid var(--accent-primary)' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-primary)' }}>Valor Actual (Precio)</div>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                    {new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(
                      previewData.resumen.reduce((acc, r) => acc + (r.valor_actual || 0), 0)
                    )}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                <button type="button" onClick={() => setPreviewTab('creditos')} className={previewTab === 'creditos' ? 'btn-primary' : 'btn-secondary'} style={{ flex: 1 }}>Créditos</button>
                <button type="button" onClick={() => setPreviewTab('cuotas')} className={previewTab === 'cuotas' ? 'btn-primary' : 'btn-secondary'} style={{ flex: 1 }}>Cuotas</button>
                <button type="button" onClick={() => setPreviewTab('resumen')} className={previewTab === 'resumen' ? 'btn-primary' : 'btn-secondary'} style={{ flex: 1 }}>Vencimientos</button>
              </div>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 16px', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
              {previewTab === 'creditos' && (() => {
                const filtered = previewData.creditos.filter(c => {
                  return Object.keys(filterCreditos).every(key => {
                    const filterVal = filterCreditos[key];
                    if (filterVal === undefined || filterVal === null || filterVal === '' || (Array.isArray(filterVal) && filterVal.length === 0)) return true;
                    if (typeof filterVal === 'object' && !Array.isArray(filterVal) && ('min' in filterVal || 'max' in filterVal)) {
                      const val = Number(c[key] || 0);
                      if (filterVal.min !== undefined && filterVal.min !== null && filterVal.min !== '' && val < Number(filterVal.min)) return false;
                      if (filterVal.max !== undefined && filterVal.max !== null && filterVal.max !== '' && val > Number(filterVal.max)) return false;
                      return true;
                    }
                    if (Array.isArray(filterVal)) {
                      return filterVal.includes(String(c[key] || ''));
                    }
                    return String(c[key] || '').toLowerCase().includes(filterVal.toLowerCase());
                  });
                });
                const totalMonto = filtered.reduce((acc, c) => acc + (tipoOperacion === 'VENTA' ? c.monto_otorgado : c.capital_vendido) || 0, 0);
                const totalCuotas = filtered.reduce((acc, c) => acc + (tipoOperacion === 'VENTA' ? c.total_cuotas : c.plazo) || 0, 0);
                const totalCeder = filtered.reduce((acc, c) => acc + (tipoOperacion === 'VENTA' ? c.cuotas_a_ceder : c.cuotas_compradas) || 0, 0);
                const totalVa = filtered.reduce((acc, c) => acc + (c.valor_actual || 0), 0);
                
                const handleFilterChange = (key, value) => {
                  setFilterCreditos(prev => ({ ...prev, [key]: value }));
                };

                return (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                    <ExportExcelButton data={previewData.creditos} filteredData={filtered} filename="preview_creditos" />
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', overflowY: 'auto', flex: 1 }}>
                    <table className="data-table" style={{ width: '100%', fontSize: '13px' }}>
                      <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                        {tipoOperacion === 'VENTA' ? (
                          <tr>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              ID
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.id || ''} onChange={e => handleFilterChange('id', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Cliente
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.cliente || ''} onChange={e => handleFilterChange('cliente', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top', position: 'relative' }}>
                              Estado
                              <div onClick={e => { e.stopPropagation(); setShowPreviewEstadoFilter(!showPreviewEstadoFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                                {!(filterCreditos.estado?.length) ? "Todos" : `${filterCreditos.estado.length} selec.`}
                              </div>
                              {showPreviewEstadoFilter && (
                                <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px', minWidth: '120px' }}>
                                  {Array.from(new Set(previewData.creditos.map(c => c.estado))).filter(Boolean).map(est => (
                                    <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer', margin: 0 }}>
                                      <input type="checkbox" checked={filterCreditos.estado?.includes(est) || false} onChange={() => {
                                        const current = filterCreditos.estado || [];
                                        handleFilterChange('estado', current.includes(est) ? current.filter(x => x !== est) : [...current, est]);
                                      }} />
                                      {est}
                                    </label>
                                  ))}
                                </div>
                              )}
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Monto Orig.
                              <ExcelNumberRangeFilter selectedRange={filterCreditos.monto_otorgado || {}} onChange={r => handleFilterChange('monto_otorgado', r)} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Cuotas
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.total_cuotas || ''} onChange={e => handleFilterChange('total_cuotas', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              A Ceder
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.cuotas_a_ceder || ''} onChange={e => handleFilterChange('cuotas_a_ceder', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Valor Actual
                              <ExcelNumberRangeFilter selectedRange={filterCreditos.valor_actual || {}} onChange={r => handleFilterChange('valor_actual', r)} />
                            </th>
                          </tr>
                        ) : (
                          <tr>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              ID Externo
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.id_externo || ''} onChange={e => handleFilterChange('id_externo', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Cliente
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.cliente_nombre || ''} onChange={e => handleFilterChange('cliente_nombre', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Cap. Vendido
                              <ExcelNumberRangeFilter selectedRange={filterCreditos.capital_vendido || {}} onChange={r => handleFilterChange('capital_vendido', r)} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Plazo
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.plazo || ''} onChange={e => handleFilterChange('plazo', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Adquiridas
                              <input type="text" placeholder="Filtrar..." value={filterCreditos.cuotas_compradas || ''} onChange={e => handleFilterChange('cuotas_compradas', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Valor Actual
                              <ExcelNumberRangeFilter selectedRange={filterCreditos.valor_actual || {}} onChange={r => handleFilterChange('valor_actual', r)} />
                            </th>
                          </tr>
                        )}
                      </thead>
                      <tbody>
                        {filtered.length === 0 && (
                          <tr><td colSpan="7" style={{ textAlign: 'center', padding: '16px' }}>No hay créditos que coincidan.</td></tr>
                        )}
                        {filtered.map((c, i) => (
                          tipoOperacion === 'VENTA' ? (
                            <tr key={i} style={{ opacity: creditosExcluidos.includes(c.id) ? 0.5 : 1 }}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.id}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.cliente}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.estado}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.monto_otorgado||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.total_cuotas}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.cuotas_a_ceder}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(c.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>
                                <button 
                                  type="button"
                                  onClick={() => handleToggleExcluir(c.id)}
                                  style={{
                                    padding: '4px 8px',
                                    fontSize: '12px',
                                    borderRadius: '4px',
                                    border: '1px solid',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease',
                                    backgroundColor: creditosExcluidos.includes(c.id) ? 'var(--bg-panel)' : 'rgba(239, 68, 68, 0.1)',
                                    borderColor: creditosExcluidos.includes(c.id) ? 'var(--border-color)' : 'var(--danger-color)',
                                    color: creditosExcluidos.includes(c.id) ? 'var(--text-secondary)' : 'var(--danger-color)'
                                  }}
                                >
                                  {creditosExcluidos.includes(c.id) ? 'Incluir' : 'Excluir'}
                                </button>
                              </td>
                            </tr>
                          ) : (
                            <tr key={i}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.id_externo}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.cliente_nombre}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.capital_vendido||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.plazo}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.cuotas_compradas}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(c.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                            </tr>
                          )
                        ))}
                      </tbody>
                      <tfoot style={{ position: 'sticky', bottom: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 -2px 4px rgba(0,0,0,0.2)' }}>
                        <tr>
                          <td colSpan={tipoOperacion === 'VENTA' ? 3 : 2} style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>Totales:</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalMonto.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'center', padding: '12px', fontWeight: 'bold' }}>{totalCuotas}</td>
                          <td style={{ textAlign: 'center', padding: '12px', fontWeight: 'bold' }}>{totalCeder}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold', color: 'var(--accent-secondary)' }}>${totalVa.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
                );
              })()}

              {previewTab === 'cuotas' && (() => {
                const filtered = previewData.cuotas.filter(c => {
                  return Object.keys(filterCuotas).every(key => {
                    const filterVal = filterCuotas[key];
                    if (filterVal === undefined || filterVal === null || filterVal === '' || (Array.isArray(filterVal) && filterVal.length === 0)) return true;
                    if (typeof filterVal === 'object' && !Array.isArray(filterVal) && ('min' in filterVal || 'max' in filterVal)) {
                      const val = Number(c[key] || 0);
                      if (filterVal.min !== undefined && filterVal.min !== null && filterVal.min !== '' && val < Number(filterVal.min)) return false;
                      if (filterVal.max !== undefined && filterVal.max !== null && filterVal.max !== '' && val > Number(filterVal.max)) return false;
                      return true;
                    }
                    if (Array.isArray(filterVal)) {
                      if (key === 'incluida' || key === 'comprada') return filterVal.includes(c[key] ? 'Sí' : 'No');
                      return filterVal.includes(String(c[key] || ''));
                    }
                    return String(c[key] || '').toLowerCase().includes(filterVal.toLowerCase());
                  });
                });
                const totalCap = filtered.reduce((acc, c) => acc + (c.capital || 0), 0);
                const totalInt = filtered.reduce((acc, c) => acc + (c.interes || 0), 0);
                const totalIva = filtered.reduce((acc, c) => acc + (c.iva || 0), 0);
                const totalTotal = filtered.reduce((acc, c) => acc + (tipoOperacion === 'VENTA' ? c.total_cuota : c.total) || 0, 0);
                const totalVa = filtered.reduce((acc, c) => acc + (c.valor_actual || 0), 0);
                
                const handleFilterChange = (key, value) => {
                  setFilterCuotas(prev => ({ ...prev, [key]: value }));
                };

                return (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                    <ExportExcelButton data={previewData.cuotas} filteredData={filtered} filename="preview_cuotas" />
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', overflowY: 'auto', flex: 1 }}>
                    <table className="data-table" style={{ width: '100%', fontSize: '13px' }}>
                      <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                        {tipoOperacion === 'VENTA' ? (
                          <tr>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Crédito ID
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.credito_id || ''} onChange={e => handleFilterChange('credito_id', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Nro Cuota
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.nro_cuota || ''} onChange={e => handleFilterChange('nro_cuota', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Vencimiento
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.fecha_vencimiento || ''} onChange={e => handleFilterChange('fecha_vencimiento', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Capital
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.capital || {}} onChange={r => handleFilterChange('capital', r)} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Interés
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.interes || {}} onChange={r => handleFilterChange('interes', r)} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              IVA
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.iva || {}} onChange={r => handleFilterChange('iva', r)} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Total Cuota
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.total_cuota || {}} onChange={r => handleFilterChange('total_cuota', r)} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Valor Actual
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.valor_actual || {}} onChange={r => handleFilterChange('valor_actual', r)} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top', position: 'relative' }}>
                              Incluida
                              <div onClick={e => { e.stopPropagation(); setShowPreviewIncluidaFilter(!showPreviewIncluidaFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                                {!(filterCuotas.incluida?.length) ? "Todos" : `${filterCuotas.incluida.length} selec.`}
                              </div>
                              {showPreviewIncluidaFilter && (
                                <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px', minWidth: '80px', textAlign: 'left' }}>
                                  {['Sí', 'No'].map(est => (
                                    <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer', margin: 0 }}>
                                      <input type="checkbox" checked={filterCuotas.incluida?.includes(est) || false} onChange={() => {
                                        const current = filterCuotas.incluida || [];
                                        handleFilterChange('incluida', current.includes(est) ? current.filter(x => x !== est) : [...current, est]);
                                      }} />
                                      {est}
                                    </label>
                                  ))}
                                </div>
                              )}
                            </th>
                          </tr>
                        ) : (
                          <tr>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              ID Ext.
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.credito_id_externo || ''} onChange={e => handleFilterChange('credito_id_externo', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top' }}>
                              Cuota
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.nro_cuota || ''} onChange={e => handleFilterChange('nro_cuota', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                              Vencimiento
                              <input type="text" placeholder="Filtrar..." value={filterCuotas.fecha_vencimiento || ''} onChange={e => handleFilterChange('fecha_vencimiento', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Capital
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.capital || {}} onChange={r => handleFilterChange('capital', r)} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Interés
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.interes || {}} onChange={r => handleFilterChange('interes', r)} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              IVA
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.iva || {}} onChange={r => handleFilterChange('iva', r)} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              Total
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.total || {}} onChange={r => handleFilterChange('total', r)} />
                            </th>
                            <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                              V. Actual
                              <ExcelNumberRangeFilter selectedRange={filterCuotas.valor_actual || {}} onChange={r => handleFilterChange('valor_actual', r)} />
                            </th>
                            <th style={{ textAlign: 'center', padding: '12px', verticalAlign: 'top', position: 'relative' }}>
                              Comprada
                              <div onClick={e => { e.stopPropagation(); setShowPreviewCompradaFilter(!showPreviewCompradaFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                                {!(filterCuotas.comprada?.length) ? "Todos" : `${filterCuotas.comprada.length} selec.`}
                              </div>
                              {showPreviewCompradaFilter && (
                                <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px', minWidth: '80px', textAlign: 'left' }}>
                                  {['Sí', 'No'].map(est => (
                                    <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer', margin: 0 }}>
                                      <input type="checkbox" checked={filterCuotas.comprada?.includes(est) || false} onChange={() => {
                                        const current = filterCuotas.comprada || [];
                                        handleFilterChange('comprada', current.includes(est) ? current.filter(x => x !== est) : [...current, est]);
                                      }} />
                                      {est}
                                    </label>
                                  ))}
                                </div>
                              )}
                            </th>
                          </tr>
                        )}
                      </thead>
                      <tbody>
                        {filtered.length === 0 && (
                          <tr><td colSpan="9" style={{ textAlign: 'center', padding: '16px' }}>No hay cuotas que coincidan.</td></tr>
                        )}
                        {filtered.map((c, i) => (
                          tipoOperacion === 'VENTA' ? (
                            <tr key={i} style={{ opacity: c.incluida ? 1 : 0.5 }}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.credito_id}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.nro_cuota}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.fecha_vencimiento}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.capital||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.interes||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.iva||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.total_cuota||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(c.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.incluida ? 'Sí' : 'No'}</td>
                            </tr>
                          ) : (
                            <tr key={i} style={{ opacity: c.comprada ? 1 : 0.5 }}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.credito_id_externo}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.nro_cuota}</td>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{c.fecha_vencimiento}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.capital||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.interes||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.iva||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(c.total||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(c.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'center', padding: '12px' }}>{c.comprada ? 'Sí' : 'No'}</td>
                            </tr>
                          )
                        ))}
                      </tbody>
                      <tfoot style={{ position: 'sticky', bottom: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 -2px 4px rgba(0,0,0,0.2)' }}>
                        <tr>
                          <td colSpan={3} style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>Totales:</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalCap.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalInt.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalIva.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalTotal.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold', color: 'var(--accent-secondary)' }}>${totalVa.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td></td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
                );
              })()}

              {previewTab === 'resumen' && (() => {
                const filtered = previewData.resumen.filter(c => {
                  return Object.keys(filterResumen).every(key => {
                    if (!filterResumen[key]) return true;
                    return String(c[key] || '').toLowerCase().includes(filterResumen[key].toLowerCase());
                  });
                });
                const totalCuotas = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.cantidad : r.cantidad_cuotas) || 0, 0);
                const totalCap = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.capital : r.capital_total) || 0, 0);
                const totalInt = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.interes : r.interes_total) || 0, 0);
                const totalIva = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.iva : r.iva_total) || 0, 0);
                const totalTot = filtered.reduce((acc, r) => acc + (tipoOperacion === 'VENTA' ? r.total_cuota : r.monto_total) || 0, 0);
                const totalVa = filtered.reduce((acc, r) => acc + (r.valor_actual || 0), 0);
                
                const handleFilterChange = (key, value) => {
                  setFilterResumen(prev => ({ ...prev, [key]: value }));
                };

                return (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                    <ExportExcelButton data={previewData.resumen} filteredData={filtered} filename="preview_vencimientos" />
                  </div>
                  <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px', overflowY: 'auto', flex: 1 }}>
                    <table className="data-table" style={{ width: '100%', fontSize: '13px' }}>
                      <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 2px 4px rgba(0,0,0,0.2)' }}>
                        <tr>
                          <th style={{ textAlign: 'left', padding: '12px', verticalAlign: 'top' }}>
                            {tipoOperacion === 'VENTA' ? 'Mes Vto.' : 'Mes'}
                            <input type="text" placeholder="Filtrar..." value={tipoOperacion === 'VENTA' ? (filterResumen.fecha_vencimiento || '') : (filterResumen.mes || '')} onChange={e => handleFilterChange(tipoOperacion === 'VENTA' ? 'fecha_vencimiento' : 'mes', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Cuotas
                            <input type="text" placeholder="Filtrar..." value={tipoOperacion === 'VENTA' ? (filterResumen.cantidad || '') : (filterResumen.cantidad_cuotas || '')} onChange={e => handleFilterChange(tipoOperacion === 'VENTA' ? 'cantidad' : 'cantidad_cuotas', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Capital Total
                            <ExcelNumberRangeFilter selectedRange={tipoOperacion === 'VENTA' ? (filterResumen.capital || {}) : (filterResumen.capital_total || {})} onChange={r => handleFilterChange(tipoOperacion === 'VENTA' ? 'capital' : 'capital_total', r)} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Interés Total
                            <ExcelNumberRangeFilter selectedRange={tipoOperacion === 'VENTA' ? (filterResumen.interes || {}) : (filterResumen.interes_total || {})} onChange={r => handleFilterChange(tipoOperacion === 'VENTA' ? 'interes' : 'interes_total', r)} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            IVA Total
                            <ExcelNumberRangeFilter selectedRange={tipoOperacion === 'VENTA' ? (filterResumen.iva || {}) : (filterResumen.iva_total || {})} onChange={r => handleFilterChange(tipoOperacion === 'VENTA' ? 'iva' : 'iva_total', r)} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Monto Total
                            <ExcelNumberRangeFilter selectedRange={tipoOperacion === 'VENTA' ? (filterResumen.total_cuota || {}) : (filterResumen.monto_total || {})} onChange={r => handleFilterChange(tipoOperacion === 'VENTA' ? 'total_cuota' : 'monto_total', r)} />
                          </th>
                          <th style={{ textAlign: 'right', padding: '12px', verticalAlign: 'top' }}>
                            Valor Actual
                            <ExcelNumberRangeFilter selectedRange={filterResumen.valor_actual || {}} onChange={r => handleFilterChange('valor_actual', r)} />
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.length === 0 && (
                          <tr><td colSpan="7" style={{ textAlign: 'center', padding: '16px' }}>No hay vencimientos que coincidan.</td></tr>
                        )}
                        {filtered.map((r, i) => {
                          const cant = tipoOperacion === 'VENTA' ? r.cantidad : r.cantidad_cuotas;
                          const cap = tipoOperacion === 'VENTA' ? r.capital : r.capital_total;
                          const int = tipoOperacion === 'VENTA' ? r.interes : r.interes_total;
                          const iva = tipoOperacion === 'VENTA' ? r.iva : r.iva_total;
                          const tot = tipoOperacion === 'VENTA' ? r.total_cuota : r.monto_total;
                          return (
                            <tr key={i}>
                              <td style={{ textAlign: 'left', padding: '12px' }}>{tipoOperacion === 'VENTA' ? r.fecha_vencimiento : r.mes}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>{cant}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(cap||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(int||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(iva||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px' }}>${(tot||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                              <td style={{ textAlign: 'right', padding: '12px', color: 'var(--accent-secondary)' }}>${(r.valor_actual||0).toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot style={{ position: 'sticky', bottom: 0, zIndex: 10, background: 'var(--bg-panel)', boxShadow: '0 -2px 4px rgba(0,0,0,0.2)' }}>
                        <tr>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>Totales:</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>{totalCuotas}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalCap.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalInt.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalIva.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold' }}>${totalTot.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 'bold', color: 'var(--accent-secondary)' }}>${totalVa.toLocaleString('es-AR', {minimumFractionDigits: 2})}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
                );
              })()}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', padding: '16px 32px', borderTop: '1px solid rgba(255,255,255,0.1)', background: 'var(--bg-panel)' }}>
                <button type="button" onClick={() => setShowPreviewModal(false)} className="btn-secondary">Volver al Formulario</button>
                <button type="button" onClick={tipoOperacion === 'VENTA' ? handleConfirmVenta : handleConfirmCompra} className="btn-primary" disabled={loading || previewData.resumen.length === 0}>
                  {loading ? 'Confirmando...' : (tipoOperacion === 'VENTA' ? 'Confirmar Venta' : (editingCompra ? 'Actualizar Compra' : 'Confirmar Compra'))}
                </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default PortfolioOriginationPage;
