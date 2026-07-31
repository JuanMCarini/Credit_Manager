import React, { useState } from 'react';
import useAppStore from '../store/useAppStore';
import { downloadFile } from '../api/axiosClient';

const BcraReportsPage = () => {
  const { socios } = useAppStore();
  const [loading, setLoading] = useState(false);

  const getLastDayOfPreviousMonth = () => {
    const today = new Date();
    const lastDay = new Date(today.getFullYear(), today.getMonth(), 0);
    return lastDay.toISOString().split('T')[0];
  };

  const [filters, setFilters] = useState({
    fecha_corte: new Date().toISOString().split('T')[0],
    vto_hasta: getLastDayOfPreviousMonth(),
    origen: 'Propios',
    socio_originador: 'Todos',
    comprado: 'Ambas',
    nro_orden: '1',
    sit_mora: 'Todas',
    min_monto_mora: '2500',
    tipo_reporte: 'NORMAL',
    cliente: ''
  });

  const handleChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  const buildParams = () => {
    const params = new URLSearchParams();
    params.append('fecha_corte', filters.fecha_corte);
    if (filters.vto_hasta) params.append('vto_hasta', filters.vto_hasta);
    if (filters.origen !== 'Ambos') params.append('origen', filters.origen);
    if (filters.socio_originador !== 'Todos') params.append('socio_originador', filters.socio_originador);
    if (filters.comprado !== 'Ambas') params.append('comprado', filters.comprado);
    if (filters.nro_orden) params.append('nro_orden', filters.nro_orden);
    if (filters.sit_mora !== 'Todas') params.append('sit_mora', filters.sit_mora);
    if (filters.min_monto_mora !== '') params.append('min_monto_mora', filters.min_monto_mora);
    params.append('tipo_reporte', filters.tipo_reporte);
    if (filters.tipo_reporte === 'RECTIFICATORIO' && filters.cliente) {
      params.append('cliente', filters.cliente);
    }
    return params;
  };

  const handleDownloadBCRA = async () => {
    setLoading(true);
    try {
      const params = buildParams();
      await downloadFile(`/api/v1/bcra/export`, params, `reporte_bcra_${filters.fecha_corte}.zip`);
    } catch (error) {
      alert("Error descargando reporte BCRA: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadNormal = async () => {
    setLoading(true);
    try {
      const params = buildParams();
      await downloadFile(`/api/v1/bcra/excel`, params, `reporte_normal_${filters.fecha_corte}.xlsx`);
    } catch (error) {
      alert("Error descargando reporte normal: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Reportes BCRA</h2>
        <p>Genere los archivos del Régimen Informativo BCRA 00006 - PNFC o exporte un reporte normal aplicando los filtros deseados.</p>
      </header>

      <div className="glass-panel form-container" style={{ maxWidth: '900px', margin: '0 auto', padding: '32px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '32px' }}>
          
          <div className="form-group">
            <label>Fecha de Información / Corte (Requerida)</label>
            <input 
              type="date" 
              name="fecha_corte" 
              value={filters.fecha_corte} 
              onChange={handleChange} 
              required
            />
          </div>

          <div className="form-group">
            <label>Fecha de Vto. Hasta (Requerida)</label>
            <input 
              type="date" 
              name="vto_hasta" 
              value={filters.vto_hasta} 
              onChange={handleChange} 
              required
            />
          </div>

          <div className="form-group">
            <label>Propiedad del Crédito</label>
            <select name="comprado" value={filters.comprado} onChange={handleChange}>
              <option value="Ambas">Ambas (Propias y Terceros)</option>
              <option value="Propias">Solo Propias</option>
              <option value="Terceros">Solo Terceros (Vendidas)</option>
            </select>
          </div>

          <div className="form-group">
            <label>Origen del Crédito</label>
            <select name="origen" value={filters.origen} onChange={handleChange}>
              <option value="Ambos">Ambos</option>
              <option value="Comprados">Comprados a Terceros</option>
              <option value="Propios">Originados por Nosotros</option>
            </select>
          </div>

          <div className="form-group">
            <label>Socio Originador</label>
            <select name="socio_originador" value={filters.socio_originador} onChange={handleChange}>
              <option value="Todos">Todos</option>
              {socios?.map(s => (
                <option key={s.id} value={s.razon_social}>{s.razon_social}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Nro. de Orden (Interno)</label>
            <input 
              type="text" 
              name="nro_orden" 
              value={filters.nro_orden} 
              onChange={handleChange} 
              placeholder="Ej: 1"
            />
          </div>

          <div className="form-group">
            <label>Situación de Mora (BCRA)</label>
            <select name="sit_mora" value={filters.sit_mora} onChange={handleChange}>
              <option value="Todas">Todas</option>
              <option value="01">01 - Normal (0 a 31 días)</option>
              <option value="02">02 - Riesgo Bajo (32 a 90 días)</option>
              <option value="03">03 - Riesgo Medio (91 a 180 días)</option>
              <option value="04">04 - Riesgo Alto (181 a 365 días)</option>
              <option value="05">05 - Irrecuperable (&gt; 365 días)</option>
            </select>
          </div>
          <div className="form-group">
            <label>Monto mínimo de mora ($)</label>
            <input 
              type="number" 
              name="min_monto_mora" 
              value={filters.min_monto_mora} 
              onChange={handleChange} 
              placeholder="Ej. 2500"
              min="0"
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '32px' }}>
          <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label>Tipo de Reporte</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px' }}>
              <span style={{ 
                fontSize: '14px', 
                color: filters.tipo_reporte === 'NORMAL' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: filters.tipo_reporte === 'NORMAL' ? '600' : '400'
              }}>
                Normal
              </span>
              
              <label style={{ position: 'relative', display: 'inline-block', width: '44px', height: '24px', margin: 0, cursor: 'pointer' }}>
                <input 
                  type="checkbox" 
                  style={{ opacity: 0, width: 0, height: 0, position: 'absolute' }}
                  checked={filters.tipo_reporte === 'RECTIFICATORIO'}
                  onChange={(e) => handleChange({ target: { name: 'tipo_reporte', value: e.target.checked ? 'RECTIFICATORIO' : 'NORMAL' } })}
                />
                <span style={{
                  position: 'absolute',
                  top: 0, left: 0, right: 0, bottom: 0,
                  backgroundColor: filters.tipo_reporte === 'RECTIFICATORIO' ? 'var(--primary-color, #4CAF50)' : '#ccc',
                  transition: '0.3s',
                  borderRadius: '24px'
                }}>
                  <span style={{
                    position: 'absolute',
                    height: '18px',
                    width: '18px',
                    left: filters.tipo_reporte === 'RECTIFICATORIO' ? '23px' : '3px',
                    bottom: '3px',
                    backgroundColor: 'white',
                    transition: '0.3s',
                    borderRadius: '50%',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                  }} />
                </span>
              </label>

              <span style={{ 
                fontSize: '14px', 
                color: filters.tipo_reporte === 'RECTIFICATORIO' ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: filters.tipo_reporte === 'RECTIFICATORIO' ? '600' : '400'
              }}>
                Rectificatorio
              </span>
            </div>
          </div>

          {filters.tipo_reporte === 'RECTIFICATORIO' && (
            <div className="form-group">
              <label>Cliente (ID, CUIL o DNI)</label>
              <input 
                type="text" 
                name="cliente" 
                value={filters.cliente} 
                onChange={handleChange}
                placeholder="Ingrese ID, CUIL o DNI del cliente"
                required={filters.tipo_reporte === 'RECTIFICATORIO'}
              />
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '16px', justifyContent: 'flex-end', marginTop: '24px' }}>
          <button 
            type="button" 
            className="btn-secondary" 
            onClick={handleDownloadNormal} 
            disabled={loading}
            style={{ minWidth: '200px', padding: '12px 24px', fontSize: '1.05rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
          >
            {loading ? "Generando..." : "📊 Descargar Reporte Normal (Excel)"}
          </button>
          
          <button 
            type="button" 
            className="btn-primary" 
            onClick={handleDownloadBCRA} 
            disabled={loading}
            style={{ minWidth: '200px', padding: '12px 24px', fontSize: '1.05rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
          >
            {loading ? "Generando..." : "🏛️ Descargar Archivos BCRA (ZIP)"}
          </button>
        </div>
      </div>
    </section>
  );
};

export default BcraReportsPage;
