import { useState, useMemo } from 'react';
import { X, ArrowLeft, CheckCircle2, Search, Calendar, Percent, Clock } from 'lucide-react';
import ExportExcelButton from './ExportExcelButton';

const formatCurrency = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '$ 0,00';
  const num = Number(val);
  if (Math.abs(num) < 0.005) return '$ 0,00';
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num);
};

const NuevaSeriePreviewModal = ({ previewData, onConfirm, onBack, onClose, isLoadingConfirm }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('todas'); // 'todas', 'nuevas', 'existentes'

  const { serie, resumen, filas } = previewData;

  const filteredFilas = useMemo(() => {
    return filas.filter((f) => {
      const matchesSearch =
        searchTerm === '' ||
        f.id_cuenta.toLowerCase().includes(searchTerm.toLowerCase()) ||
        f.razon_social.toLowerCase().includes(searchTerm.toLowerCase()) ||
        f.cuit.toLowerCase().includes(searchTerm.toLowerCase());

      if (!matchesSearch) return false;

      if (filterType === 'nuevas') return f.es_cuenta_nueva;
      if (filterType === 'existentes') return !f.es_cuenta_nueva;
      return true;
    });
  }, [filas, searchTerm, filterType]);

  const exportData = useMemo(() => {
    return filteredFilas.map((f) => ({
      'ID Cta. Cte.': f.id_cuenta,
      'Razón Social': f.razon_social,
      'CUIT/CUIL': f.cuit,
      'Dirección': f.direccion,
      'Capital': f.capital,
      'Interés': f.interes,
      'Total': f.total,
      'Es Cuenta Nueva': f.es_cuenta_nueva ? 'SÍ' : 'NO',
      'Inversores Nuevos': f.inversores_nuevos
    }));
  }, [filteredFilas]);

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 1100,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '16px',
        overflowY: 'auto'
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '1200px',
          maxWidth: '96vw',
          height: '92vh',
          maxHeight: '94vh',
          minHeight: '480px',
          display: 'flex',
          flexDirection: 'column',
          padding: '20px 24px',
          position: 'relative',
          borderRadius: '12px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px', flexShrink: 0 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600' }}>
                Vista Previa: Nueva Serie <span style={{ color: 'var(--accent-primary, #6366f1)' }}>{serie.name}</span>
              </h3>
              <span
                style={{
                  backgroundColor: 'rgba(99, 102, 241, 0.15)',
                  color: 'var(--accent-primary, #6366f1)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: '600'
                }}
              >
                Verificación Previa (Sin Guardar)
              </span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
              Verifique los datos y totales extraídos del archivo antes de impactar en la base de datos.
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isLoadingConfirm}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              padding: '4px'
            }}
            title="Cerrar modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Serie Meta Badges */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '14px',
            padding: '8px 12px',
            backgroundColor: 'rgba(255,255,255,0.03)',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.08)',
            marginBottom: '10px',
            fontSize: '12px',
            flexShrink: 0
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Calendar size={14} style={{ opacity: 0.7 }} />
            <span style={{ color: 'var(--text-muted)' }}>Fecha Suscripción:</span>
            <strong>{serie.fecha_suscripcion}</strong>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Percent size={14} style={{ opacity: 0.7 }} />
            <span style={{ color: 'var(--text-muted)' }}>TNA:</span>
            <strong>{(serie.tna * 100).toFixed(2)}%</strong>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Clock size={14} style={{ opacity: 0.7 }} />
            <span style={{ color: 'var(--text-muted)' }}>Plazo:</span>
            <strong>{serie.plazo} días</strong>
          </div>
        </div>

        {/* KPI Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '10px',
            marginBottom: '10px',
            flexShrink: 0
          }}
        >
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Capital Total a Suscribir
            </div>
            <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--success-color, #10b981)', marginTop: '4px' }}>
              {formatCurrency(resumen.total_capital)}
            </div>
          </div>

          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Intereses Estimados
            </div>
            <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text-color)', marginTop: '4px' }}>
              {formatCurrency(resumen.total_interes)}
            </div>
          </div>

          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Monto Total (Cap + Int)
            </div>
            <div style={{ fontSize: '18px', fontWeight: '700', color: '#6366f1', marginTop: '4px' }}>
              {formatCurrency(resumen.total_monto)}
            </div>
          </div>

          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Cuentas Comitentes
            </div>
            <div style={{ fontSize: '18px', fontWeight: '700', marginTop: '4px' }}>
              {resumen.cantidad_cuentas}{' '}
              <span style={{ fontSize: '12px', fontWeight: 'normal', color: 'var(--text-muted)' }}>
                ({resumen.cuentas_nuevas} nuevas, {resumen.cuentas_existentes} existentes)
              </span>
            </div>
          </div>

          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Inversores / Titulares
            </div>
            <div style={{ fontSize: '18px', fontWeight: '700', marginTop: '4px' }}>
              {resumen.total_inversores}{' '}
              <span style={{ fontSize: '12px', fontWeight: 'normal', color: 'var(--text-muted)' }}>
                ({resumen.inversores_nuevos} nuevos)
              </span>
            </div>
          </div>
        </div>

        {/* Toolbar: Search + Quick Filter Tabs + Excel Export */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginBottom: '10px', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
            <div style={{ position: 'relative', width: '280px' }}>
              <Search size={15} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Buscar cuenta, titular o CUIT..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ paddingLeft: '32px', width: '100%', height: '34px', fontSize: '12px' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setFilterType('todas')}
                style={{
                  height: '34px',
                  padding: '0 10px',
                  fontSize: '12px',
                  backgroundColor: filterType === 'todas' ? 'var(--accent-primary, #6366f1)' : 'transparent',
                  color: filterType === 'todas' ? '#fff' : 'var(--text-secondary)'
                }}
              >
                Todas ({resumen.cantidad_cuentas})
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setFilterType('nuevas')}
                style={{
                  height: '34px',
                  padding: '0 10px',
                  fontSize: '12px',
                  backgroundColor: filterType === 'nuevas' ? 'var(--accent-primary, #6366f1)' : 'transparent',
                  color: filterType === 'nuevas' ? '#fff' : 'var(--text-secondary)'
                }}
              >
                Nuevas ({resumen.cuentas_nuevas})
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setFilterType('existentes')}
                style={{
                  height: '34px',
                  padding: '0 10px',
                  fontSize: '12px',
                  backgroundColor: filterType === 'existentes' ? 'var(--accent-primary, #6366f1)' : 'transparent',
                  color: filterType === 'existentes' ? '#fff' : 'var(--text-secondary)'
                }}
              >
                Existentes ({resumen.cuentas_existentes})
              </button>
            </div>
          </div>

          <ExportExcelButton data={exportData} filename={`Preview_${serie.name}`} />
        </div>

        {/* Scrollable Table */}
        <div
          className="table-responsive"
          style={{
            flex: '1 1 0px',
            minHeight: 0,
            overflowX: 'auto',
            overflowY: 'auto',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '6px'
          }}
        >
          <table className="data-table" style={{ width: '100%', minWidth: '1050px', fontSize: '12px' }}>
            <thead style={{ position: 'sticky', top: 0, zIndex: 2, background: 'var(--surface-color, #1e1e24)' }}>
              <tr>
                <th style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>Cta. Cte.</th>
                <th style={{ padding: '8px 12px', minWidth: '220px', textAlign: 'left' }}>Titular / Razón Social</th>
                <th style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>CUIT/CUIL</th>
                <th style={{ padding: '8px 12px', textAlign: 'right', whiteSpace: 'nowrap' }}>Capital</th>
                <th style={{ padding: '8px 12px', textAlign: 'right', whiteSpace: 'nowrap' }}>Interés</th>
                <th style={{ padding: '8px 12px', textAlign: 'right', whiteSpace: 'nowrap' }}>Total</th>
                <th style={{ padding: '8px 12px', textAlign: 'center', whiteSpace: 'nowrap' }}>Estado</th>
              </tr>
            </thead>
            <tbody>
              {filteredFilas.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                    No se encontraron filas que coincidan con la búsqueda o filtro.
                  </td>
                </tr>
              ) : (
                filteredFilas.map((f, idx) => (
                  <tr key={idx}>
                    <td style={{ padding: '8px 12px', fontWeight: '600', whiteSpace: 'nowrap' }}>{f.id_cuenta}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'left' }}>
                      <div style={{ fontWeight: '500' }}>{f.razon_social}</div>
                      {f.direccion && <small style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{f.direccion}</small>}
                    </td>
                    <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>{f.cuit}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '500', whiteSpace: 'nowrap' }}>{formatCurrency(f.capital)}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{formatCurrency(f.interes)}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: '600', color: 'var(--accent-primary, #6366f1)', whiteSpace: 'nowrap' }}>
                      {formatCurrency(f.total)}
                    </td>
                    <td style={{ padding: '8px 12px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '10px',
                          fontSize: '11px',
                          fontWeight: '600',
                          backgroundColor: f.es_cuenta_nueva ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.08)',
                          color: f.es_cuenta_nueva ? '#10b981' : 'var(--text-muted)'
                        }}
                      >
                        {f.es_cuenta_nueva ? 'Nueva' : 'Existente'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Footer Actions */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: '12px',
            paddingTop: '12px',
            borderTop: '1px solid rgba(255,255,255,0.08)',
            flexShrink: 0
          }}
        >
          <button
            type="button"
            className="btn-secondary"
            onClick={onBack}
            disabled={isLoadingConfirm}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <ArrowLeft size={16} /> Volver a Modificar
          </button>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoadingConfirm}>
              Cancelar
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={onConfirm}
              disabled={isLoadingConfirm}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0 20px' }}
            >
              <CheckCircle2 size={16} />
              {isLoadingConfirm ? 'Creando serie en base de datos...' : 'Confirmar y Crear Serie'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NuevaSeriePreviewModal;
