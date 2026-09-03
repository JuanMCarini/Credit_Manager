import { useState, useCallback, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import { Calendar, Save, FileText, CheckCircle, Clock, Percent } from 'lucide-react';
import Swal from 'sweetalert2';

const CurrencyInput = ({ value, onChange, className, style }) => {
  const [isFocused, setIsFocused] = useState(false);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'decimal',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(val || 0);
  };

  return (
    <input
      type={isFocused ? "number" : "text"}
      className={className}
      style={style}
      value={isFocused ? (value === 0 ? '' : value) : formatCurrency(value)}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      onChange={(e) => {
        const parsed = parseFloat(e.target.value);
        onChange(isNaN(parsed) ? 0 : parsed);
      }}
      step="0.01"
    />
  );
};

const PosicionIibbPage = () => {
  const [mes, setMes] = useState(
    new Date().toISOString().substring(0, 7)
  );
  
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [posiciones, setPosiciones] = useState([]);
  
  // Form State
  const [posicionId, setPosicionId] = useState(null);
  const [iibbVentas, setIibbVentas] = useState(0);
  const [retenciones, setRetenciones] = useState(0);
  const [percepciones, setPercepciones] = useState(0);
  const [pagosVep, setPagosVep] = useState(0);
  const [saldoAnterior, setSaldoAnterior] = useState(0);
  const [detalleProvincias, setDetalleProvincias] = useState([]);
  const [estadoPosicion, setEstadoPosicion] = useState('Borrador');

  const handleAlicuotaChange = (provincia_id, newAlicuotaStr) => {
    const updated = detalleProvincias.map(p => {
      if (p.provincia_id === provincia_id) {
        const parsed = parseFloat(newAlicuotaStr);
        const alicuotaVal = isNaN(parsed) ? 0 : parsed;
        return { ...p, alicuota: newAlicuotaStr, impuesto: (p.neto * alicuotaVal) / 100.0 };
      }
      return p;
    });
    setDetalleProvincias(updated);
    const totalIIBB = updated.reduce((acc, curr) => acc + curr.impuesto, 0);
    setIibbVentas(totalIIBB);
  };
  
  // derived
  const saldoAPagar = Number(iibbVentas) - Number(retenciones) - Number(percepciones) + Number(saldoAnterior) - Number(pagosVep);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  const loadHistorial = useCallback(async () => {
    try {
      const res = await axiosClient.get('/api/finanzas/posicion-iibb');
      setPosiciones(res.data);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    loadHistorial();
  }, [loadHistorial]);

  const handleCalcular = useCallback(async () => {
    if (!mes) return;
    setLoading(true);
    setPosicionId(null);
    try {
      const [yearStr, monthStr] = mes.split('-');
      const anio = parseInt(yearStr);
      const m = parseInt(monthStr);

      // Check if already saved
      const existing = posiciones.find(p => p.anio === anio && p.mes === m);
      if (existing) {
        setPosicionId(existing.id);
        setIibbVentas(existing.iibb_ventas);
        setRetenciones(existing.retenciones_bancarias);
        setPercepciones(existing.percepciones_compras);
        setPagosVep(existing.pagos_vep);
        setSaldoAnterior(existing.saldo_anterior);
        setEstadoPosicion(existing.estado || 'Borrador');
        
        if (existing.detalle_provincias) {
           const det = Array.isArray(existing.detalle_provincias) 
              ? existing.detalle_provincias 
              : Object.values(existing.detalle_provincias);
           setDetalleProvincias(det);
        } else {
           setDetalleProvincias([]);
        }
        
        Swal.fire('Posición Cargada', 'Se cargó la posición guardada previamente.', 'info');
      } else {
        const res = await axiosClient.get('/api/finanzas/posicion-iibb/calcular', { 
          params: { anio, mes: m } 
        });
        
        const ventas = res.data.ventas_por_provincia || [];
        const detInit = ventas.map(v => ({
           provincia: v.provincia,
           provincia_id: v.provincia_id,
           neto: v.neto,
           alicuota: 0,
           impuesto: 0
        }));
        
        setDetalleProvincias(detInit);
        setIibbVentas(0);
        setRetenciones(res.data.retenciones_bancarias);
        setPercepciones(res.data.percepciones_compras);
        setPagosVep(res.data.pagos_vep);
        setSaldoAnterior(res.data.saldo_anterior);
        setEstadoPosicion('Borrador');
        Swal.fire('Cálculo Finalizado', 'Se trajeron los valores automáticos según comprobantes y bancos. Por favor ingrese las alícuotas por provincia.', 'success');
      }
    } catch (err) {
      console.error(err);
      Swal.fire('Error', 'No se pudo calcular la posición de IIBB.', 'error');
    } finally {
      setLoading(false);
    }
  }, [mes, posiciones]);

  const handleRecalcular = useCallback(async () => {
    if (!mes) return;
    
    const result = await Swal.fire({
      title: '¿Forzar recálculo?',
      text: "Esto traerá nuevamente las facturas y comprobantes del sistema. Perderás los porcentajes de alícuotas que no hayas guardado.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, recalcular',
      cancelButtonText: 'Cancelar'
    });
    
    if (!result.isConfirmed) return;

    setLoading(true);
    try {
      const [yearStr, monthStr] = mes.split('-');
      const anio = parseInt(yearStr);
      const m = parseInt(monthStr);

      const res = await axiosClient.get('/api/finanzas/posicion-iibb/calcular', { 
        params: { anio, mes: m } 
      });
      
      const ventas = res.data.ventas_por_provincia || [];
      const detInit = ventas.map(v => ({
         provincia: v.provincia,
         provincia_id: v.provincia_id,
         neto: v.neto,
         alicuota: 0,
         impuesto: 0
      }));
      
      setDetalleProvincias(detInit);
      setIibbVentas(0);
      setRetenciones(res.data.retenciones_bancarias);
      setPercepciones(res.data.percepciones_compras);
      setPagosVep(res.data.pagos_vep);
      setSaldoAnterior(res.data.saldo_anterior);
      setEstadoPosicion('Borrador');
      Swal.fire('Recálculo Finalizado', 'Se trajeron los valores automáticos según comprobantes y bancos. Por favor ingrese las alícuotas por provincia.', 'success');
    } catch (err) {
      console.error(err);
      Swal.fire('Error', 'No se pudo recalcular la posición de IIBB.', 'error');
    } finally {
      setLoading(false);
    }
  }, [mes]);

  const handleSave = async (estado = 'Borrador') => {
    if (!mes) return;
    setSaving(true);
    try {
      const [yearStr, monthStr] = mes.split('-');
      const payload = {
        anio: parseInt(yearStr),
        mes: parseInt(monthStr),
        iibb_ventas: Number(iibbVentas),
        retenciones_bancarias: Number(retenciones),
        percepciones_compras: Number(percepciones),
        pagos_vep: Number(pagosVep),
        saldo_anterior: Number(saldoAnterior),
        saldo_a_pagar: saldoAPagar,
        detalle_provincias: detalleProvincias,
        estado: estado
      };

      if (posicionId) {
        await axiosClient.put(`/api/finanzas/posicion-iibb/${posicionId}`, payload);
        Swal.fire('Guardado', 'La posición de IIBB fue actualizada.', 'success');
      } else {
        const res = await axiosClient.post('/api/finanzas/posicion-iibb', payload);
        setPosicionId(res.data.id);
        Swal.fire('Guardado', 'La posición de IIBB fue creada.', 'success');
      }
      loadHistorial();
    } catch (err) {
      console.error(err);
      let errorMsg = 'No se pudo guardar la posición.';
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMsg = err.response.data.detail.map(d => `${d.loc.join(' > ')}: ${d.msg}`).join(', ');
        } else {
          errorMsg = err.response.data.detail;
        }
      }
      Swal.fire('Error', errorMsg, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-container" style={{ padding: '24px', margin: '0 auto', maxWidth: '1200px' }}>
      <header className="page-header" style={{ marginBottom: '32px' }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '28px', fontWeight: 'bold' }}>
          <FileText size={32} color="var(--primary-color)" />
          Posición de IIBB (Ingresos Brutos)
        </h1>
        <p className="page-description" style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px' }}>
          Calcule los Ingresos Brutos a pagar mensual cruzando facturas emitidas, comprobantes de compra y retenciones bancarias (SIRCREB/IIBB).
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '24px' }}>
        {/* Main Form Area */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          <div className="card">
            <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Calendar size={20} /> Período
            </h3>
            <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div style={{ flex: '1', minWidth: '150px' }}>
                <label className="form-label">Mes de Posición</label>
                <input 
                  type="month" 
                  className="form-control" 
                  value={mes} 
                  onChange={(e) => {
                    setMes(e.target.value);
                    setPosicionId(null);
                    setEstadoPosicion('Borrador');
                    setDetalleProvincias([]);
                  }}
                  max={new Date().toISOString().substring(0, 7)}
                />
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  className="btn btn-primary" 
                  onClick={handleCalcular} 
                  disabled={loading || !mes}
                  style={{ height: '42px', padding: '0 24px', display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  {loading ? <span className="spinner" /> : <Clock size={18} />}
                  {loading ? 'Calculando...' : 'Cargar Posición'}
                </button>
                {posicionId && (
                  <button 
                    className="btn btn-outline" 
                    onClick={handleRecalcular} 
                    disabled={loading || !mes}
                    style={{ height: '42px', padding: '0 16px', display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid var(--border-color)', background: 'transparent' }}
                    title="Recalcular desde los comprobantes originales (Sobrescribe datos de pantalla)"
                  >
                    Recalcular
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: '600' }}>Detalle de la Posición</h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <div>
                <label className="form-label" style={{ color: 'var(--text-color)' }}>IIBB Ventas (+)</label>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>$</span>
                  <CurrencyInput 
                    className="form-control" 
                    style={{ paddingLeft: '28px', background: 'var(--surface-hover)' }}
                    value={iibbVentas} 
                    onChange={setIibbVentas} 
                  />
                </div>
                <small style={{ color: 'var(--text-muted)' }}>Suma del detalle por provincia (intereses).</small>
              </div>

              <div>
                <label className="form-label" style={{ color: 'var(--primary-color)' }}>Retenciones Bancarias (SIRCREB/IIBB) (-)</label>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>$</span>
                  <CurrencyInput 
                    className="form-control" 
                    style={{ paddingLeft: '28px' }}
                    value={retenciones} 
                    onChange={setRetenciones} 
                  />
                </div>
                <small style={{ color: 'var(--text-muted)' }}>Movimientos donde el concepto incluye 'IIBB' o 'SIRCREB'.</small>
              </div>

              <div>
                <label className="form-label" style={{ color: 'var(--primary-color)' }}>Percepciones Sufridas (-)</label>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>$</span>
                  <CurrencyInput 
                    className="form-control" 
                    style={{ paddingLeft: '28px' }}
                    value={percepciones} 
                    onChange={setPercepciones} 
                  />
                </div>
                <small style={{ color: 'var(--text-muted)' }}>Percepciones de IIBB en comprobantes de compra.</small>
              </div>

              <div>
                <label className="form-label" style={{ color: 'var(--primary-color)' }}>Saldo Anterior (+/-)</label>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>$</span>
                  <CurrencyInput 
                    className="form-control" 
                    style={{ paddingLeft: '28px' }}
                    value={saldoAnterior} 
                    onChange={setSaldoAnterior} 
                  />
                </div>
              </div>

              <div>
                <label className="form-label" style={{ color: 'var(--primary-color)' }}>Pagos VEP (Banco/Comprobantes) (-)</label>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>$</span>
                  <CurrencyInput 
                    className="form-control" 
                    style={{ paddingLeft: '28px' }}
                    value={pagosVep} 
                    onChange={setPagosVep} 
                  />
                </div>
                <small style={{ color: 'var(--text-muted)' }}>Suma de pagos VEP de IIBB detectados.</small>
              </div>
            </div>

            <div style={{ marginTop: '24px' }}>
              <h4 style={{ marginBottom: '12px', fontSize: '16px', fontWeight: '600' }}>Alícuotas por Provincia</h4>
              {detalleProvincias.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Haga clic en Calcular para traer el detalle de facturación.</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                        <th style={{ padding: '8px' }}>Provincia</th>
                        <th style={{ padding: '8px', textAlign: 'right' }}>Neto (Intereses)</th>
                        <th style={{ padding: '8px', width: '120px' }}>Alícuota (%)</th>
                        <th style={{ padding: '8px', textAlign: 'right' }}>Impuesto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {detalleProvincias.map(p => (
                        <tr key={p.provincia_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '8px' }}>{p.provincia}</td>
                          <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(p.neto)}</td>
                          <td style={{ padding: '8px' }}>
                            <input
                              type="number"
                              step="0.1"
                              className="form-control"
                              style={{ padding: '4px 8px', height: '32px' }}
                              value={p.alicuota}
                              onChange={(e) => handleAlicuotaChange(p.provincia_id, e.target.value)}
                              disabled={estadoPosicion === 'Guardado'}
                            />
                          </td>
                          <td style={{ padding: '8px', textAlign: 'right', fontWeight: 'bold', color: 'var(--primary-color)' }}>
                            {formatCurrency(p.impuesto)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div style={{ 
              marginTop: '24px', 
              padding: '24px', 
              background: saldoAPagar > 0 ? 'rgba(var(--danger-rgb), 0.05)' : 'rgba(var(--success-rgb), 0.05)',
              border: `1px solid ${saldoAPagar > 0 ? 'var(--danger-color)' : 'var(--success-color)'}`,
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <p style={{ margin: 0, fontSize: '14px', fontWeight: 'bold', color: saldoAPagar > 0 ? 'var(--danger-color)' : 'var(--success-color)', textTransform: 'uppercase' }}>
                  {saldoAPagar > 0 ? 'Saldo a Pagar a AGIP/ARBA' : 'Saldo a Favor Técnico'}
                </p>
                <h2 style={{ margin: '8px 0 0 0', fontSize: '32px', color: 'var(--text-color)' }}>
                  {formatCurrency(Math.abs(saldoAPagar))}
                </h2>
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button 
                  className="btn btn-outline" 
                  onClick={() => handleSave('Borrador')} 
                  disabled={saving || loading}
                  style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
                >
                  <Save size={18} /> Guardar Borrador
                </button>
                <button 
                  className="btn btn-success" 
                  onClick={() => handleSave('Guardado')} 
                  disabled={saving || loading}
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--success-color)', color: 'white', border: 'none' }}
                >
                  <CheckCircle size={18} /> Posición Definitiva
                </button>
              </div>
            </div>
          </div>

        </div>

        {/* Sidebar History */}
        <div className="card">
          <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: '600' }}>Historial de Posiciones</h3>
          {posiciones.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No hay posiciones guardadas aún.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {posiciones.map(p => (
                <div 
                  key={p.id} 
                  style={{ 
                    padding: '12px', 
                    border: '1px solid var(--border-color)', 
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    background: p.anio === parseInt(mes.split('-')[0]) && p.mes === parseInt(mes.split('-')[1]) ? 'var(--surface-hover)' : 'transparent'
                  }}
                  onClick={() => {
                    setMes(`${p.anio}-${p.mes.toString().padStart(2, '0')}`);
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <strong style={{ fontSize: '15px' }}>{p.mes.toString().padStart(2, '0')} / {p.anio}</strong>
                    <span style={{ 
                      fontSize: '11px', 
                      padding: '2px 8px', 
                      borderRadius: '12px',
                      background: p.estado === 'Guardado' ? 'rgba(var(--success-rgb), 0.1)' : 'rgba(var(--warning-rgb), 0.1)',
                      color: p.estado === 'Guardado' ? 'var(--success-color)' : 'var(--warning-color)',
                      fontWeight: 'bold'
                    }}>
                      {p.estado}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-muted)' }}>
                    <span>A Pagar:</span>
                    <span style={{ fontWeight: '600', color: p.saldo_a_pagar > 0 ? 'var(--danger-color)' : 'var(--success-color)' }}>
                      {formatCurrency(p.saldo_a_pagar)}
                    </span>
                  </div>
                  {p.pagos_vep > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      <span>Pagos VEP:</span>
                      <span style={{ color: 'var(--primary-color)' }}>
                        {formatCurrency(p.pagos_vep)}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PosicionIibbPage;
