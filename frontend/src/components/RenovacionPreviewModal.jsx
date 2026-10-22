import { useState, useMemo } from 'react';
import { X, ArrowLeft, CheckCircle2, Search, ArrowRight } from 'lucide-react';
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

const RenovacionPreviewModal = ({ previewData, onConfirm, onBack, onClose, isLoadingConfirm }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('todas'); // 'todas', 'rescates', 'suscripciones', 'solo_renovacion'

  const { serie_vieja, serie_nueva, resumen, filas } = previewData;

  const filteredFilas = useMemo(() => {
    return filas.filter((f) => {
      const matchesSearch =
        searchTerm === '' ||
        f.id_cuenta.toLowerCase().includes(searchTerm.toLowerCase()) ||
        f.razon_social.toLowerCase().includes(searchTerm.toLowerCase()) ||
        f.cuit.toLowerCase().includes(searchTerm.toLowerCase());

      if (!matchesSearch) return false;

      if (activeTab === 'rescates') return f.rescate >= 0.01;
      if (activeTab === 'suscripciones') return f.suscripcion >= 0.01;
      if (activeTab === 'solo_renovacion') return f.rescate < 0.01 && f.suscripcion < 0.01;
      return true;
    });
  }, [filas, searchTerm, activeTab]);

  const exportData = useMemo(() => {
    return filteredFilas.map((f) => ({
      'ID Cta. Cte.': f.id_cuenta,
      'Razón Social': f.razon_social,
      'CUIT/CUIL': f.cuit,
      'Capital Vencido': f.capital,
      'Interés Vencido': f.interes,
      'Rescate': f.rescate,
      'Renovación': f.renovacion,
      'Nueva Suscripción': f.suscripcion,
      'Total Nueva Serie': f.total,
      'Acción': f.accion,
      'Observación': f.observacion
    }));
  }, [filteredFilas]);

  const getBadgeStyle = (tipo_badge) => {
    switch (tipo_badge) {
      case 'danger':
        return { backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)' };
      case 'warning':
        return { backgroundColor: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', border: '1px solid rgba(245, 158, 11, 0.3)' };
      case 'info':
        return { backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', border: '1px solid rgba(59, 130, 246, 0.3)' };
      case 'success':
      default:
        return { backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)' };
    }
  };

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
          width: '1350px',
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
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>{serie_vieja.name}</span>
                <ArrowRight size={16} style={{ color: 'var(--accent-primary, #6366f1)' }} />
                <span style={{ color: 'var(--accent-primary, #6366f1)' }}>{serie_nueva.name}</span>
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
                Vista Previa de Liquidación (Sin Confirmar)
              </span>
            </div>
            <p style={{ margin: '4px 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
              Verifique los importes de liquidación, rescates y suscripciones antes de impactar en la base de datos.
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

        {/* Metadatos Comparativos */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: previewData.series_viejas?.length > 1 ? '1.2fr 0.8fr' : '1fr 1fr',
            gap: '10px',
            marginBottom: '10px',
            flexShrink: 0
          }}
        >
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: 'rgba(255,255,255,0.02)',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.06)',
              fontSize: '11px'
            }}
          >
            {previewData.series_viejas?.length > 1 ? (
              <>
                <div style={{ fontWeight: '600', color: 'var(--accent-primary, #6366f1)', marginBottom: '4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span>FUSIÓN DE {previewData.series_viejas.length} SERIES</span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Vto: {serie_vieja.fecha_vencimiento}</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '72px', overflowY: 'auto' }}>
                  {previewData.series_viejas.map((s) => (
                    <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.04)', paddingBottom: '2px', fontSize: '10px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-color)' }}>{s.name}</span>
                      <span style={{ color: 'var(--text-muted)' }}>
                        TNA: {(s.tna * 100).toFixed(2)}% | Plazo: {s.plazo}d | Cap: {formatCurrency(s.capital)} | Int: {formatCurrency(s.interes)}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <>
                <div style={{ fontWeight: '600', color: 'var(--text-muted)', marginBottom: '3px' }}>
                  SERIE ANTERIOR: {serie_vieja.name}
                </div>
                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                  <span>TNA: <strong>{serie_vieja.tna !== null && serie_vieja.tna !== undefined ? `${(serie_vieja.tna * 100).toFixed(2)}%` : '-'}</strong></span>
                  <span>Plazo: <strong>{serie_vieja.plazo ?? '-'} días</strong></span>
                  <span>Suscripción: <strong>{serie_vieja.fecha_suscripcion || '-'}</strong></span>
                  <span>Vencimiento: <strong>{serie_vieja.fecha_vencimiento || '-'}</strong></span>
                </div>
              </>
            )}
          </div>

          <div
            style={{
              padding: '8px 12px',
              backgroundColor: 'rgba(99, 102, 241, 0.05)',
              borderRadius: '8px',
              border: '1px solid rgba(99, 102, 241, 0.2)',
              fontSize: '11px'
            }}
          >
            <div style={{ fontWeight: '600', color: 'var(--accent-primary, #6366f1)', marginBottom: '3px' }}>
              NUEVA SERIE A EMITIR: {serie_nueva.name}
            </div>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <span>TNA: <strong>{(serie_nueva.tna * 100).toFixed(2)}%</strong></span>
              <span>Plazo: <strong>{serie_nueva.plazo} días</strong></span>
              <span>Fecha: <strong>{serie_nueva.fecha_suscripcion}</strong></span>
            </div>
          </div>
        </div>

        {/* KPI Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '8px',
            marginBottom: '10px',
            flexShrink: 0
          }}
        >
          <div
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Capital Vencido
            </div>
            <div style={{ fontSize: '14px', fontWeight: '700', marginTop: '2px' }}>
              {formatCurrency(resumen.total_capital_anterior)}
            </div>
          </div>

          <div
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Intereses Devengados
            </div>
            <div style={{ fontSize: '14px', fontWeight: '700', marginTop: '2px' }}>
              {formatCurrency(resumen.total_interes_anterior)}
            </div>
          </div>

          <div
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: 'rgba(239, 68, 68, 0.05)',
              border: '1px solid rgba(239, 68, 68, 0.2)'
            }}
          >
            <div style={{ fontSize: '10px', color: '#ef4444', textTransform: 'uppercase', fontWeight: '600' }}>
              Total Rescates
            </div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: '#ef4444', marginTop: '2px' }}>
              {formatCurrency(resumen.total_rescates)}{' '}
              <span style={{ fontSize: '10px', fontWeight: 'normal' }}>
                ({resumen.cuentas_con_rescate} ctas)
              </span>
            </div>
          </div>

          <div
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)'
            }}
          >
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: '600' }}>
              Total Renovado (Reinvertido)
            </div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--success-color, #10b981)', marginTop: '2px' }}>
              {formatCurrency(resumen.total_renovado)}
            </div>
          </div>

          <div
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: 'rgba(59, 130, 246, 0.05)',
              border: '1px solid rgba(59, 130, 246, 0.2)'
            }}
          >
            <div style={{ fontSize: '10px', color: '#3b82f6', textTransform: 'uppercase', fontWeight: '600' }}>
              Nuevas Suscripciones
            </div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: '#3b82f6', marginTop: '2px' }}>
              {formatCurrency(resumen.total_nuevas_suscripciones)}{' '}
              <span style={{ fontSize: '10px', fontWeight: 'normal' }}>
                ({resumen.cuentas_con_suscripcion} ctas)
              </span>
            </div>
          </div>

          <div
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: 'rgba(99, 102, 241, 0.08)',
              border: '1px solid rgba(99, 102, 241, 0.3)'
            }}
          >
            <div style={{ fontSize: '10px', color: 'var(--accent-primary, #6366f1)', textTransform: 'uppercase', fontWeight: '700' }}>
              Nuevo Capital Serie
            </div>
            <div style={{ fontSize: '14px', fontWeight: '700', color: 'var(--accent-primary, #6366f1)', marginTop: '2px' }}>
              {formatCurrency(resumen.total_nuevo_capital)}
            </div>
          </div>
        </div>

        {/* Toolbar: Search + Filter Tabs + Excel Export */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginBottom: '10px', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', width: '260px' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Buscar cuenta, titular o CUIT..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ paddingLeft: '32px', width: '100%', height: '32px', fontSize: '12px' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setActiveTab('todas')}
                style={{
                  height: '32px',
                  padding: '0 8px',
                  fontSize: '11px',
                  backgroundColor: activeTab === 'todas' ? 'var(--accent-primary, #6366f1)' : 'transparent',
                  color: activeTab === 'todas' ? '#fff' : 'var(--text-secondary)'
                }}
              >
                Todas ({resumen.cantidad_cuentas})
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setActiveTab('rescates')}
                style={{
                  height: '32px',
                  padding: '0 8px',
                  fontSize: '11px',
                  backgroundColor: activeTab === 'rescates' ? '#ef4444' : 'transparent',
                  color: activeTab === 'rescates' ? '#fff' : 'var(--text-secondary)'
                }}
              >
                Con Rescates ({resumen.cuentas_con_rescate})
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setActiveTab('suscripciones')}
                style={{
                  height: '32px',
                  padding: '0 8px',
                  fontSize: '11px',
                  backgroundColor: activeTab === 'suscripciones' ? '#3b82f6' : 'transparent',
                  color: activeTab === 'suscripciones' ? '#fff' : 'var(--text-secondary)'
                }}
              >
                Con Nuevos Aportes ({resumen.cuentas_con_suscripcion})
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setActiveTab('solo_renovacion')}
                style={{
                  height: '32px',
                  padding: '0 8px',
                  fontSize: '11px',
                  backgroundColor: activeTab === 'solo_renovacion' ? 'rgba(255,255,255,0.15)' : 'transparent',
                  color: activeTab === 'solo_renovacion' ? '#fff' : 'var(--text-secondary)'
                }}
              >
                Solo Renovación ({resumen.cuentas_solo_renovacion})
              </button>
            </div>
          </div>

          <ExportExcelButton data={exportData} filename={`Preview_Renovacion_${serie_nueva.name}`} />
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
          <table className="data-table" style={{ width: '100%', minWidth: '1350px', fontSize: '12px' }}>
            <thead style={{ position: 'sticky', top: 0, zIndex: 2, background: 'var(--surface-color, #1e1e24)' }}>
              <tr>
                <th style={{ padding: '8px 10px', whiteSpace: 'nowrap' }}>Cta. Cte.</th>
                <th style={{ padding: '8px 10px', minWidth: '220px', textAlign: 'left' }}>Titular / Razón Social</th>
                <th style={{ padding: '8px 10px', whiteSpace: 'nowrap' }}>CUIT/CUIL</th>
                <th style={{ padding: '8px 10px', textAlign: 'right', whiteSpace: 'nowrap' }}>Capital Vencido</th>
                <th style={{ padding: '8px 10px', textAlign: 'right', whiteSpace: 'nowrap' }}>Interés</th>
                <th style={{ padding: '8px 10px', textAlign: 'right', whiteSpace: 'nowrap' }}>Rescate</th>
                <th style={{ padding: '8px 10px', textAlign: 'right', whiteSpace: 'nowrap' }}>Renovación</th>
                <th style={{ padding: '8px 10px', textAlign: 'right', whiteSpace: 'nowrap' }}>Nueva Suscripción</th>
                <th style={{ padding: '8px 10px', textAlign: 'right', whiteSpace: 'nowrap' }}>Total Nueva Serie</th>
                <th style={{ padding: '8px 10px', textAlign: 'center', whiteSpace: 'nowrap' }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {filteredFilas.length === 0 ? (
                <tr>
                  <td colSpan="10" style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                    No se encontraron registros para la búsqueda o filtro seleccionado.
                  </td>
                </tr>
              ) : (
                filteredFilas.map((f, idx) => (
                  <tr key={idx}>
                    <td style={{ padding: '8px 10px', fontWeight: '600', whiteSpace: 'nowrap' }}>{f.id_cuenta}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'left' }}>
                      <div style={{ fontWeight: '500' }}>{f.razon_social}</div>
                      {f.observacion && <small style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{f.observacion}</small>}
                    </td>
                    <td style={{ padding: '8px 10px', whiteSpace: 'nowrap' }}>{f.cuit}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right', whiteSpace: 'nowrap' }}>{formatCurrency(f.capital)}</td>
                    <td style={{ padding: '8px 10px', textAlign: 'right', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{formatCurrency(f.interes)}</td>
                    <td
                      style={{
                        padding: '8px 10px',
                        textAlign: 'right',
                        whiteSpace: 'nowrap',
                        fontWeight: f.rescate >= 0.01 ? '700' : 'normal',
                        color: f.rescate >= 0.01 ? '#ef4444' : 'var(--text-muted)'
                      }}
                    >
                      {formatCurrency(f.rescate)}
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: '500', whiteSpace: 'nowrap' }}>
                      {formatCurrency(f.renovacion)}
                    </td>
                    <td
                      style={{
                        padding: '8px 10px',
                        textAlign: 'right',
                        whiteSpace: 'nowrap',
                        fontWeight: f.suscripcion >= 0.01 ? '700' : 'normal',
                        color: f.suscripcion >= 0.01 ? '#3b82f6' : 'var(--text-muted)'
                      }}
                    >
                      {formatCurrency(f.suscripcion)}
                    </td>
                    <td
                      style={{
                        padding: '8px 10px',
                        textAlign: 'right',
                        whiteSpace: 'nowrap',
                        fontWeight: '700',
                        color: 'var(--accent-primary, #6366f1)'
                      }}
                    >
                      {formatCurrency(f.total)}
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '10px',
                          fontSize: '11px',
                          fontWeight: '600',
                          ...getBadgeStyle(f.tipo_badge)
                        }}
                      >
                        {f.accion}
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

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={isLoadingConfirm}
              style={{ minWidth: '90px' }}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={onConfirm}
              disabled={isLoadingConfirm}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '0 20px',
                backgroundColor: 'var(--success-color, #10b981)',
                borderColor: 'var(--success-color, #10b981)',
                color: '#fff',
                fontWeight: '600'
              }}
            >
              <CheckCircle2 size={16} />
              {isLoadingConfirm ? 'Procesando en base de datos...' : 'Aprobar y Confirmar Renovación'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RenovacionPreviewModal;
