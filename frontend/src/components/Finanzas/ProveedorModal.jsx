import { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import axiosClient from '../../api/axiosClient';

const ProveedorModal = ({ isOpen, onClose, onSave, proveedor = null, conceptos = [] }) => {
  const [formData, setFormData] = useState({
    razon_social: '',
    tipo_documento: 'CUIT',
    nro_documento: '',
    personeria: 'JURIDICA',
    provincia_id: 1, // Default, assuming 1 exists
    localidad: '',
    domicilio: '',
    piso: '',
    depto: '',
    codigo_postal: '',
    telefono: '',
    email: '',
    categoria_impositiva: 'RESPONSABLE INSCRIPTO',
    concepto_id: ''
  });
  
  const [provincias, setProvincias] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Fetch provincias
    const fetchProvincias = async () => {
      try {
        const res = await axiosClient.get('/api/v1/auxiliares/provincias');
        setProvincias(res.data);
      } catch (err) {
        console.error("Error fetching provincias", err);
      }
    };
    if (isOpen) {
      fetchProvincias();
      if (proveedor) {
        setFormData(proveedor);
      } else {
        setFormData({
          razon_social: '',
          tipo_documento: 'CUIT',
          nro_documento: '',
          personeria: 'JURIDICA',
          provincia_id: 1,
          localidad: '',
          domicilio: '',
          piso: '',
          depto: '',
          codigo_postal: '',
          telefono: '',
          email: '',
          categoria_impositiva: 'RESPONSABLE INSCRIPTO',
          concepto_id: ''
        });
      }
      setError('');
    }
  }, [isOpen, proveedor]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (proveedor) {
        await axiosClient.put(`/api/finanzas/proveedores/${proveedor.id}`, formData);
      } else {
        await axiosClient.post('/api/finanzas/proveedores', formData);
      }
      onSave();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar el proveedor');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="modal-content" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto', boxShadow: 'var(--shadow-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0 }}>{proveedor ? 'Editar Proveedor' : 'Nuevo Proveedor'}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={24} /></button>
        </div>
        
        {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>{error}</div>}
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Razón Social *</label>
              <input required type="text" className="form-control" name="razon_social" value={formData.razon_social} onChange={handleChange} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Tipo Doc *</label>
              <select className="form-control" name="tipo_documento" value={formData.tipo_documento} onChange={handleChange}>
                <option value="CUIT">CUIT</option>
                <option value="CUIL">CUIL</option>
                <option value="DNI">DNI</option>
              </select>
            </div>
            <div style={{ flex: 2 }}>
              <label className="form-label">Nro Documento *</label>
              <input required type="text" className="form-control" name="nro_documento" value={formData.nro_documento} onChange={handleChange} maxLength="11" />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Personería *</label>
              <select className="form-control" name="personeria" value={formData.personeria} onChange={handleChange}>
                <option value="FISICA">Física</option>
                <option value="JURIDICA">Jurídica</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Categoría Impositiva *</label>
              <select className="form-control" name="categoria_impositiva" value={formData.categoria_impositiva} onChange={handleChange}>
                <option value="CONSUMIDOR FINAL">Consumidor Final</option>
                <option value="RESPONSABLE INSCRIPTO">Responsable Inscripto</option>
                <option value="MONOTRIBUTISTA">Monotributista</option>
                <option value="EXENTO">Exento</option>
                <option value="IVA NO ALCANZADO">IVA No Alcanzado</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Concepto Predeterminado (Opcional)</label>
              <select className="form-control" name="concepto_id" value={formData.concepto_id || ''} onChange={handleChange}>
                <option value="">Sin concepto...</option>
                {Array.from(new Map(conceptos?.filter(c => c.clasificacion).map(c => [c.clasificacion.id, c.clasificacion])).values()).map(cl => (
                  <optgroup key={cl.id} label={cl.name}>
                    {conceptos
                      .filter(c => c.clasificacion_id === cl.id)
                      .map(c => <option key={c.id} value={c.id}>{c.name} ({c.tipo_movimiento})</option>)}
                  </optgroup>
                ))}
                <optgroup label="Sin Clasificación">
                  {conceptos
                    ?.filter(c => !c.clasificacion_id)
                    .map(c => <option key={c.id} value={c.id}>{c.name} ({c.tipo_movimiento})</option>)}
                </optgroup>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Provincia *</label>
              <select className="form-control" name="provincia_id" value={formData.provincia_id} onChange={handleChange}>
                {provincias.map(p => (
                  <option key={p.id} value={p.id}>{p.nombre}</option>
                ))}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Localidad</label>
              <input type="text" className="form-control" name="localidad" value={formData.localidad || ''} onChange={handleChange} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 2 }}>
              <label className="form-label">Domicilio</label>
              <input type="text" className="form-control" name="domicilio" value={formData.domicilio || ''} onChange={handleChange} />
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Piso</label>
              <input type="text" className="form-control" name="piso" value={formData.piso || ''} onChange={handleChange} />
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Depto</label>
              <input type="text" className="form-control" name="depto" value={formData.depto || ''} onChange={handleChange} />
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Teléfono</label>
              <input type="text" className="form-control" name="telefono" value={formData.telefono || ''} onChange={handleChange} />
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Email</label>
              <input type="email" className="form-control" name="email" value={formData.email || ''} onChange={handleChange} />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              <Save size={18} style={{ marginRight: '8px' }} />
              {loading ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProveedorModal;
