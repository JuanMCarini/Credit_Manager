import { useState, useEffect } from 'react';
import { X, Save, FileText, Upload } from 'lucide-react';
import axiosClient from '../../api/axiosClient';
import CurrencyInput from '../CurrencyInput';

const ComprobanteModal = ({ isOpen, onClose, onSave, comprobante = null, proveedores = [], conceptos = [], onNewProveedor }) => {
  const [formData, setFormData] = useState({
    proveedor_id: '',
    tipo_comprobante: 'A',
    punto_venta: '',
    numero_comprobante: '',
    fecha_contable: new Date().toISOString().substring(0, 10),
    fecha_emision: new Date().toISOString().substring(0, 10),
    fecha_vencimiento: '',
    importe_no_gravado: 0,
    importe_exento: 0,
    neto_gravado_21: 0,
    neto_gravado_105: 0,
    neto_gravado_27: 0,
    iva_21: 0,
    iva_105: 0,
    iva_27: 0,
    percepcion_iva: 0,
    percepcion_iibb: 0,
    percepcion_ganancias: 0,
    otros_impuestos: 0,
  });

  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      if (comprobante) {
        setFormData(comprobante);
      } else {
        setFormData({
          proveedor_id: proveedores.length > 0 ? proveedores[0].id : '',
          tipo_comprobante: 'A',
          punto_venta: '',
          numero_comprobante: '',
          fecha_contable: new Date().toISOString().substring(0, 10),
          fecha_emision: new Date().toISOString().substring(0, 10),
          fecha_vencimiento: '',
          importe_no_gravado: 0,
          importe_exento: 0,
          neto_gravado_21: 0,
          neto_gravado_105: 0,
          neto_gravado_27: 0,
          iva_21: 0,
          iva_105: 0,
          iva_27: 0,
          percepcion_iva: 0,
          percepcion_iibb: 0,
          percepcion_ganancias: 0,
          otros_impuestos: 0,
          importe_total: 0,
          concepto_id: '',
        });
      }
      setSelectedFile(null);
      setError('');
    }
  }, [isOpen, comprobante, proveedores]);

  // Autocalculate IVA when neto changes
  useEffect(() => {
    const parseNum = (val) => {
      const parsed = parseFloat(val);
      return isNaN(parsed) ? 0 : parsed;
    };
    setFormData(prev => ({
      ...prev,
      iva_21: (parseNum(prev.neto_gravado_21) * 0.21).toFixed(2),
      iva_105: (parseNum(prev.neto_gravado_105) * 0.105).toFixed(2),
      iva_27: (parseNum(prev.neto_gravado_27) * 0.27).toFixed(2),
    }));
  }, [formData.neto_gravado_21, formData.neto_gravado_105, formData.neto_gravado_27]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const updates = { [name]: value };
      
      // Auto-fill concepto if proveedor is selected
      if (name === 'proveedor_id' && value) {
        const proveedor = proveedores.find(p => p.id === parseInt(value));
        if (proveedor && proveedor.concepto_id) {
          updates.concepto_id = proveedor.concepto_id;
        }
      }
      
      return { ...prev, ...updates };
    });
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const calcularTotal = () => {
    const parseNum = (val) => {
      const parsed = parseFloat(val);
      return isNaN(parsed) ? 0 : parsed;
    };
    const total = 
      parseNum(formData.importe_no_gravado) +
      parseNum(formData.importe_exento) +
      parseNum(formData.neto_gravado_21) +
      parseNum(formData.neto_gravado_105) +
      parseNum(formData.neto_gravado_27) +
      parseNum(formData.iva_21) +
      parseNum(formData.iva_105) +
      parseNum(formData.iva_27) +
      parseNum(formData.percepcion_iva) +
      parseNum(formData.percepcion_iibb) +
      parseNum(formData.percepcion_ganancias) +
      parseNum(formData.otros_impuestos);
    return new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(total);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      let savedComprobante = null;
      
      const payload = { ...formData };
      const decimalFields = [
        'importe_no_gravado', 'importe_exento', 'neto_gravado_21', 
        'neto_gravado_105', 'neto_gravado_27', 'iva_21', 'iva_105', 'iva_27',
        'percepcion_iva', 'percepcion_iibb', 'percepcion_ganancias', 'otros_impuestos'
      ];
      
      decimalFields.forEach(f => {
        const parsed = parseFloat(payload[f]);
        payload[f] = isNaN(parsed) ? 0 : parsed;
      });
      
      const isDetailed = ['A', 'M', 'NOTA_DEBITO_A', 'NOTA_CREDITO_A'].includes(payload.tipo_comprobante);
      
      if (!isDetailed) {
        payload.importe_no_gravado = 0;
        payload.importe_exento = 0;
        payload.neto_gravado_21 = 0;
        payload.neto_gravado_105 = 0;
        payload.neto_gravado_27 = 0;
        payload.iva_21 = 0;
        payload.iva_105 = 0;
        payload.iva_27 = 0;
        payload.percepcion_iva = 0;
        payload.percepcion_iibb = 0;
        payload.percepcion_ganancias = 0;
        payload.otros_impuestos = 0;
        payload.importe_total = parseFloat(payload.importe_total) || 0;
      } else {
        payload.importe_total = parseFloat(calcularTotal()) || 0;
      }
      
      if (!payload.concepto_id) {
        payload.concepto_id = null;
      }

      if (!payload.fecha_vencimiento) {
        payload.fecha_vencimiento = null;
      }

      if (comprobante) {
        const res = await axiosClient.put(`/api/finanzas/comprobantes/${comprobante.id}`, payload);
        savedComprobante = res.data;
      } else {
        const res = await axiosClient.post('/api/finanzas/comprobantes', payload);
        savedComprobante = res.data;
      }

      // Upload file if selected
      if (selectedFile && savedComprobante) {
        const uploadData = new FormData();
        uploadData.append('file', selectedFile);
        await axiosClient.post(`/api/finanzas/comprobantes/${savedComprobante.id}/upload`, uploadData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });
      }

      onSave();
    } catch (err) {
      let errorMsg = 'Error al guardar el comprobante';
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join(', ');
        } else {
          errorMsg = err.response.data.detail;
        }
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const requiresDetailedTaxes = ['A', 'M', 'NOTA_DEBITO_A', 'NOTA_CREDITO_A'].includes(formData.tipo_comprobante);

  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="modal-content" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto', boxShadow: 'var(--shadow-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0 }}>{comprobante ? 'Editar Comprobante' : 'Nuevo Comprobante'}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={24} /></button>
        </div>
        
        {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>{error}</div>}
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {/* Cabecera */}
          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Proveedor *</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <select required className="form-control" name="proveedor_id" value={formData.proveedor_id} onChange={handleChange}>
                  <option value="">Seleccione...</option>
                  {proveedores.map(p => (
                    <option key={p.id} value={p.id}>{p.razon_social} ({p.cuit || p.nro_documento})</option>
                  ))}
                </select>
                <button type="button" className="btn btn-outline" onClick={onNewProveedor}>Nuevo</button>
              </div>
            </div>
            
            <div style={{ flex: 1 }}>
              <label className="form-label">Concepto (Opcional)</label>
              <select className="form-control" name="concepto_id" value={formData.concepto_id || ''} onChange={handleChange}>
                <option value="">Sin clasificar...</option>
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
              <label className="form-label">Tipo *</label>
              <select required className="form-control" name="tipo_comprobante" value={formData.tipo_comprobante} onChange={handleChange}>
                <option value="A">A</option>
                <option value="B">B</option>
                <option value="C">C</option>
                <option value="E">E</option>
                <option value="M">M</option>
                <option value="TICKET">TICKET</option>
                <option value="NOTA_DEBITO_A">NOTA DÉBITO A</option>
                <option value="NOTA_DEBITO_B">NOTA DÉBITO B</option>
                <option value="NOTA_CREDITO_A">NOTA CRÉDITO A</option>
                <option value="NOTA_CREDITO_B">NOTA CRÉDITO B</option>
                <option value="RECIBO">RECIBO</option>
                <option value="VEP">VEP</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Punto Venta *</label>
              <input required type="number" className="form-control" name="punto_venta" value={formData.punto_venta} onChange={handleChange} min="1" max="99999" />
            </div>
            <div style={{ flex: 2 }}>
              <label className="form-label">Número *</label>
              <input required type="number" className="form-control" name="numero_comprobante" value={formData.numero_comprobante} onChange={handleChange} min="1" />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Fecha Contable *</label>
              <input required type="date" className="form-control" name="fecha_contable" value={formData.fecha_contable} onChange={handleChange} />
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Fecha Emisión *</label>
              <input required type="date" className="form-control" name="fecha_emision" value={formData.fecha_emision} onChange={handleChange} />
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Fecha Vencimiento</label>
              <input type="date" className="form-control" name="fecha_vencimiento" value={formData.fecha_vencimiento || ''} onChange={handleChange} />
            </div>
          </div>

          <hr style={{ margin: '8px 0', borderColor: 'var(--border-color)' }} />
          <h4 style={{ margin: '0', fontWeight: '600', color: 'var(--primary-color)' }}>Importes</h4>

          {/* Importes */}
          {requiresDetailedTaxes ? (
            <>
              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label className="form-label">No Gravado</label>
                  <CurrencyInput className="form-control" name="importe_no_gravado" value={formData.importe_no_gravado} onChange={(val, e) => handleChange(e)} />
                </div>
                <div style={{ flex: 1 }}>
                  <label className="form-label">Exento</label>
                  <CurrencyInput className="form-control" name="importe_exento" value={formData.importe_exento} onChange={(val, e) => handleChange(e)} />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label className="form-label">Neto 21%</label>
                  <CurrencyInput className="form-control" name="neto_gravado_21" value={formData.neto_gravado_21} onChange={(val, e) => handleChange(e)} />
                </div>
                <div style={{ flex: 1 }}>
                  <label className="form-label">IVA 21%</label>
                  <CurrencyInput className="form-control" name="iva_21" value={formData.iva_21} readOnly style={{ backgroundColor: 'var(--surface-color)' }} />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label className="form-label">Neto 10.5%</label>
                  <CurrencyInput className="form-control" name="neto_gravado_105" value={formData.neto_gravado_105} onChange={(val, e) => handleChange(e)} />
                </div>
                <div style={{ flex: 1 }}>
                  <label className="form-label">IVA 10.5%</label>
                  <CurrencyInput className="form-control" name="iva_105" value={formData.iva_105} readOnly style={{ backgroundColor: 'var(--surface-color)' }} />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label className="form-label">Neto 27%</label>
                  <CurrencyInput className="form-control" name="neto_gravado_27" value={formData.neto_gravado_27} onChange={(val, e) => handleChange(e)} />
                </div>
                <div style={{ flex: 1 }}>
                  <label className="form-label">IVA 27%</label>
                  <CurrencyInput className="form-control" name="iva_27" value={formData.iva_27} readOnly style={{ backgroundColor: 'var(--surface-color)' }} />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label className="form-label">Percepción IVA</label>
                  <CurrencyInput className="form-control" name="percepcion_iva" value={formData.percepcion_iva} onChange={(val, e) => handleChange(e)} />
                </div>
                <div style={{ flex: 1 }}>
                  <label className="form-label">Percepción IIBB</label>
                  <CurrencyInput className="form-control" name="percepcion_iibb" value={formData.percepcion_iibb} onChange={(val, e) => handleChange(e)} />
                </div>
                <div style={{ flex: 1 }}>
                  <label className="form-label">Otras Percepciones</label>
                  <CurrencyInput className="form-control" name="otros_impuestos" value={formData.otros_impuestos} onChange={(val, e) => handleChange(e)} />
                </div>
              </div>

              <div className="alert alert-info" style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: '600' }}>TOTAL CALCULADO:</span>
                <span style={{ fontSize: '1.2em', fontWeight: 'bold' }}>$ {calcularTotal()}</span>
              </div>
            </>
          ) : (
            <div style={{ display: 'flex', gap: '16px' }}>
              <div style={{ flex: 1 }}>
                <label className="form-label">Importe Total *</label>
                <CurrencyInput required className="form-control" name="importe_total" value={formData.importe_total} onChange={(val, e) => handleChange(e || { target: { name: 'importe_total', value: val }})} style={{ fontSize: '1.1em', fontWeight: 'bold', border: '1px solid var(--primary-color)' }} />
              </div>
              <div style={{ flex: 2 }}>
                {/* Espaciador para mantener alineación */}
              </div>
            </div>
          )}

          <hr style={{ margin: '8px 0', borderColor: 'var(--border-color)' }} />
          <h4 style={{ margin: '0', fontWeight: '600', color: 'var(--primary-color)' }}>Archivo PDF</h4>
          <div>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Upload size={16} />
              Subir PDF / Imagen
            </label>
            <input type="file" className="form-control" accept=".pdf,image/*" onChange={handleFileChange} />
            {comprobante?.archivo_pdf && (
              <div style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
                <FileText size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
                Archivo actual: {comprobante.archivo_pdf.split('/').pop()}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              <Save size={18} style={{ marginRight: '8px' }} />
              {loading ? 'Guardando...' : 'Guardar Comprobante'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ComprobanteModal;
