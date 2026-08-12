import { useState, useCallback, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import { FileText, Users, Plus, Download, Edit, Trash2, CreditCard } from 'lucide-react';
import ComprobanteModal from '../components/Finanzas/ComprobanteModal';
import ProveedorModal from '../components/Finanzas/ProveedorModal';
import CancelacionModal from '../components/Finanzas/CancelacionModal';

const ComprobantesPage = () => {
  const [activeTab, setActiveTab] = useState('comprobantes');

  const [comprobantes, setComprobantes] = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [conceptos, setConceptos] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Modals state
  const [isComprobanteModalOpen, setIsComprobanteModalOpen] = useState(false);
  const [isProveedorModalOpen, setIsProveedorModalOpen] = useState(false);
  const [isCancelacionModalOpen, setIsCancelacionModalOpen] = useState(false);
  const [selectedComprobante, setSelectedComprobante] = useState(null);
  const [selectedProveedor, setSelectedProveedor] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [resComp, resProv, resConceptos] = await Promise.all([
        axiosClient.get('/api/finanzas/comprobantes'),
        axiosClient.get('/api/finanzas/proveedores'),
        axiosClient.get('/api/finanzas/conceptos')
      ]);
      setComprobantes(resComp.data);
      setProveedores(resProv.data);
      setConceptos(resConceptos.data);
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

  const handleOpenCancelacionModal = (comp) => {
    setSelectedComprobante(comp);
    setIsCancelacionModalOpen(true);
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
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>{error}</div>}

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
                  <th style={{ textAlign: 'center' }}>Fecha Emisión</th>
                  <th style={{ textAlign: 'center' }}>Proveedor</th>
                  <th style={{ textAlign: 'center' }}>Comprobante</th>
                  <th style={{ textAlign: 'center' }}>Concepto</th>
                  <th style={{ textAlign: 'center' }}>Total</th>
                  <th style={{ textAlign: 'center' }}>Saldo</th>
                  <th style={{ textAlign: 'center' }}>Estado</th>
                  <th style={{ textAlign: 'center' }}>PDF</th>
                  <th style={{ textAlign: 'center' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan="9" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
                ) : comprobantes.length === 0 ? (
                  <tr><td colSpan="9" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>No hay comprobantes cargados.</td></tr>
                ) : (
                  comprobantes.map(c => {
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
                        <td>{c.fecha_emision}</td>
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
    </div>
  );
};

export default ComprobantesPage;
