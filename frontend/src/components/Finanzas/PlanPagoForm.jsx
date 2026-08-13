import { useState, useEffect } from 'react';
import { Save, X } from 'lucide-react';
import axiosClient from '../../api/axiosClient';
import CurrencyInput from '../CurrencyInput';

// Newton-Raphson para calcular la tasa (equivalente a npf.rate)
const calculateRate = (nper, pmt, pv) => {
    let rate = 0.1; // guess inicial
    for (let i = 0; i < 100; i++) {
        let f = pv * Math.pow(1 + rate, nper) + pmt * ((Math.pow(1 + rate, nper) - 1) / rate);
        let df = nper * pv * Math.pow(1 + rate, nper - 1) + pmt * ((nper * Math.pow(1 + rate, nper - 1) * rate - (Math.pow(1 + rate, nper) - 1)) / (rate * rate));
        let newRate = rate - f / df;
        if (Math.abs(newRate - rate) < 0.0000001) return newRate;
        rate = newRate;
    }
    return rate;
};

const PlanPagoForm = ({ isOpen, onClose, proveedores, conceptos, editPlan, onSave }) => {
    const [formData, setFormData] = useState({
        id_origen: '',
        fecha: new Date().toISOString().split('T')[0],
        proveedor_id: '',
        concepto_id: '',
        capital: 0,
        anticipo: 0,
        vencimiento_anticipo: '',
        plazo: 1,
        valor_cuota: 0,
        primer_vencimiento: '',
        sistema: 'Sistema Francés',
        denominador: '12'
    });

    const [tna, setTna] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        const capital = parseFloat(formData.capital) || 0;
        const anticipo = parseFloat(formData.anticipo) || 0;
        const plazo = parseInt(formData.plazo) || 1;
        const valor_cuota = parseFloat(formData.valor_cuota) || 0;
        const denominador = formData.denominador === '12' ? 12 : (365/30);
        
        const capitalFinanciar = capital - anticipo;
        if (capitalFinanciar <= 0 || valor_cuota <= 0 || plazo <= 0) {
            setTna(0);
            return;
        }

        try {
            if (formData.sistema === 'Amortización lineal directa (cuotas fijas)') {
                const t = ((valor_cuota * plazo / capitalFinanciar) - 1) / plazo * denominador;
                setTna(t * 100); // porcentaje
            } else if (formData.sistema === 'Sistema Francés') {
                // npf.rate(nper=self.plazo, pmt=self.valor_cuota, pv=-(self.capital - self.anticipo))
                const rate = calculateRate(plazo, valor_cuota, -capitalFinanciar);
                const t = rate * denominador;
                setTna(t * 100);
            }
        } catch (e) {
            console.error(e);
            setTna(0);
        }
    }, [formData.capital, formData.anticipo, formData.plazo, formData.valor_cuota, formData.sistema, formData.denominador]);

    useEffect(() => {
        if (isOpen) {
            if (editPlan) {
                setFormData({
                    id_origen: editPlan.id_origen || '',
                    fecha: editPlan.fecha || new Date().toISOString().split('T')[0],
                    proveedor_id: editPlan.proveedor_id || '',
                    concepto_id: editPlan.concepto_id || '',
                    capital: editPlan.capital || 0,
                    anticipo: editPlan.anticipo || 0,
                    vencimiento_anticipo: editPlan.vencimiento_anticipo || '',
                    plazo: editPlan.plazo || 1,
                    valor_cuota: editPlan.valor_cuota || 0,
                    primer_vencimiento: editPlan.primer_vencimiento || '',
                    sistema: editPlan.sistema || 'Sistema Francés',
                    denominador: editPlan.denominador || '12'
                });
            } else {
                setFormData({
                    id_origen: '',
                    fecha: new Date().toISOString().split('T')[0],
                    proveedor_id: '',
                    concepto_id: '',
                    capital: 0,
                    anticipo: 0,
                    vencimiento_anticipo: '',
                    plazo: 1,
                    valor_cuota: 0,
                    primer_vencimiento: '',
                    sistema: 'Sistema Francés',
                    denominador: '12'
                });
            }
            setError('');
        }
    }, [isOpen, editPlan]);

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
            const dataToSubmit = {
                ...formData,
                tna: (tna / 100).toFixed(4)
            };
            
            // Validate required
            if (!dataToSubmit.proveedor_id || !dataToSubmit.id_origen) {
                throw new Error("ID Origen y Proveedor son obligatorios.");
            }

            if (dataToSubmit.anticipo > 0 && !dataToSubmit.vencimiento_anticipo) {
                throw new Error("Debe ingresar un vencimiento para el anticipo.");
            }

            // Fix empty string dates turning to null if not provided
            if (!dataToSubmit.vencimiento_anticipo) {
                dataToSubmit.vencimiento_anticipo = null;
            }

            if (!dataToSubmit.concepto_id) {
                dataToSubmit.concepto_id = null;
            }

            if (editPlan) {
                await axiosClient.put(`/api/finanzas/planes/${editPlan.id}`, dataToSubmit);
            } else {
                await axiosClient.post('/api/finanzas/planes', dataToSubmit);
            }
            
            if (onSave) onSave();
            
            // Reset form
            setFormData({
                id_origen: '',
                fecha: new Date().toISOString().split('T')[0],
                proveedor_id: '',
                concepto_id: '',
                capital: 0,
                anticipo: 0,
                vencimiento_anticipo: '',
                plazo: 1,
                valor_cuota: 0,
                primer_vencimiento: '',
                sistema: 'Sistema Francés',
                denominador: '12'
            });
            alert("Plan guardado correctamente.");
        } catch (err) {
            setError(err.response?.data?.detail || err.message || 'Error al guardar el plan');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
            <div className="modal-content" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto', boxShadow: 'var(--shadow-lg)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                    <h3 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>{editPlan ? 'Editar Plan de Pago' : 'Generar Nuevo Plan de Pago'}</h3>
                    <button type="button" onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}><X size={24} /></button>
                </div>
                
                {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>{error}</div>}

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                        <label className="form-label">ID Origen *</label>
                        <input required type="text" className="form-control" name="id_origen" value={formData.id_origen} onChange={handleChange} placeholder="Ej. PLAN-001" />
                    </div>
                    <div>
                        <label className="form-label">Fecha del Plan *</label>
                        <input required type="date" className="form-control" name="fecha" value={formData.fecha} onChange={handleChange} />
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                        <label className="form-label">Proveedor *</label>
                        <select required className="form-control" name="proveedor_id" value={formData.proveedor_id} onChange={handleChange}>
                            <option value="">Seleccione proveedor...</option>
                            {proveedores.map(p => (
                                <option key={p.id} value={p.id}>{p.razon_social} ({p.nro_documento})</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="form-label">Concepto (Opcional)</label>
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

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', background: 'var(--background-color)', padding: '16px', borderRadius: '8px' }}>
                    <div>
                        <label className="form-label">Capital Total *</label>
                        <CurrencyInput required className="form-control" name="capital" value={formData.capital} onChange={(val, e) => handleChange(e)} />
                    </div>
                    <div>
                        <label className="form-label">Anticipo *</label>
                        <CurrencyInput required className="form-control" name="anticipo" value={formData.anticipo} onChange={(val, e) => handleChange(e)} />
                    </div>
                    <div>
                        <label className="form-label">Vencimiento Anticipo</label>
                        <input type="date" className="form-control" name="vencimiento_anticipo" value={formData.vencimiento_anticipo} onChange={handleChange} disabled={!formData.anticipo || parseFloat(formData.anticipo) <= 0} required={parseFloat(formData.anticipo) > 0} />
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
                    <div>
                        <label className="form-label">Plazo (Cuotas) *</label>
                        <input required type="number" min="1" className="form-control" name="plazo" value={formData.plazo} onChange={handleChange} />
                    </div>
                    <div>
                        <label className="form-label">Valor Cuota *</label>
                        <CurrencyInput required className="form-control" name="valor_cuota" value={formData.valor_cuota} onChange={(val, e) => handleChange(e)} />
                    </div>
                    <div>
                        <label className="form-label">Primer Vencimiento *</label>
                        <input required type="date" className="form-control" name="primer_vencimiento" value={formData.primer_vencimiento} onChange={handleChange} />
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                        <label className="form-label">Sistema *</label>
                        <select required className="form-control" name="sistema" value={formData.sistema} onChange={handleChange}>
                            <option value="Sistema Francés">Sistema Francés</option>
                            <option value="Amortización lineal directa (cuotas fijas)">Amortización lineal directa (cuotas fijas)</option>
                        </select>
                    </div>
                    <div>
                        <label className="form-label">Denominador *</label>
                        <select required className="form-control" name="denominador" value={formData.denominador} onChange={handleChange}>
                            <option value="12">Mensual (12)</option>
                            <option value="365/30">Diario (365/30)</option>
                        </select>
                    </div>
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: '16px' }}>
                    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', padding: '12px 16px', borderRadius: '8px', display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>TNA Calculado (Live Preview)</span>
                        <span style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--accent-primary)' }}>{isFinite(tna) ? tna.toFixed(2) + '%' : '0.00%'}</span>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <button type="button" className="btn btn-outline" onClick={onClose} disabled={loading}>
                            Cancelar
                        </button>
                        <button type="submit" className="btn btn-primary" disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <Save size={18} />
                            {loading ? 'Procesando...' : 'Guardar Plan'}
                        </button>
                    </div>
                </div>
            </form>
            </div>
        </div>
    );
};

export default PlanPagoForm;
