import React, { useState, useEffect } from 'react';
import { Clock, User, ArrowRight, FileText, CheckCircle2 } from 'lucide-react';
import axiosClient from '../api/axiosClient';

const getEstadoColor = (estado) => {
  switch (estado?.toUpperCase()) {
    case 'APROBADO':
      return { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', border: 'rgba(16, 185, 129, 0.3)' };
    case 'FIRMADO':
      return { bg: 'rgba(99, 102, 241, 0.15)', text: '#818cf8', border: 'rgba(99, 102, 241, 0.3)' };
    case 'ACTIVO':
      return { bg: 'rgba(6, 182, 212, 0.15)', text: '#06b6d4', border: 'rgba(6, 182, 212, 0.3)' };
    case 'MOROSO':
      return { bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' };
    case 'JUDICIAL':
      return { bg: 'rgba(234, 88, 12, 0.15)', text: '#ea580c', border: 'rgba(234, 88, 12, 0.3)' };
    case 'INCOBRABLE':
      return { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444', border: 'rgba(239, 68, 68, 0.3)' };
    case 'RECHAZADO':
      return { bg: 'rgba(244, 63, 94, 0.15)', text: '#f43f5e', border: 'rgba(244, 63, 94, 0.3)' };
    case 'CANCELADO':
      return { bg: 'rgba(148, 163, 184, 0.15)', text: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)' };
    default:
      return { bg: 'rgba(148, 163, 184, 0.1)', text: 'var(--text-secondary)', border: 'var(--border-color)' };
  }
};

const formatFecha = (isoString) => {
  if (!isoString) return '-';
  try {
    const d = new Date(isoString);
    return d.toLocaleString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
};

const CreditHistorialModal = ({ creditoId, onClose }) => {
  const [historial, setHistorial] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHistorial = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await axiosClient.get(`/api/v1/creditos/${creditoId}/historial-estados`);
        setHistorial(res.data || []);
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Error cargando historial de estados');
      } finally {
        setLoading(false);
      }
    };
    if (creditoId) {
      fetchHistorial();
    }
  }, [creditoId]);

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.6)', zIndex: 1100,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
      backdropFilter: 'blur(6px)'
    }}>
      <div className="glass-panel" style={{
        width: '100%', maxWidth: '640px', maxHeight: '85vh',
        display: 'flex', flexDirection: 'column',
        position: 'relative', padding: '24px', borderRadius: '12px'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '8px',
              backgroundColor: 'rgba(99, 102, 241, 0.15)', display: 'flex',
              alignItems: 'center', justifyContent: 'center', color: '#818cf8'
            }}>
              <Clock size={20} />
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: '18px', fontFamily: 'var(--font-heading)' }}>
                Historial de Estados
              </h2>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Crédito #{creditoId}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', color: 'var(--text-secondary)',
              cursor: 'pointer', fontSize: '20px', padding: '4px'
            }}
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '6px' }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)' }}>
              Cargando historial de transiciones...
            </div>
          )}

          {error && (
            <div style={{ padding: '12px 16px', borderRadius: '8px', backgroundColor: 'rgba(239,68,68,0.1)', color: 'var(--error)', marginBottom: '16px' }}>
              {error}
            </div>
          )}

          {!loading && !error && historial.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)' }}>
              No se encontraron registros de cambios de estado para este crédito.
            </div>
          )}

          {!loading && !error && historial.length > 0 && (
            <div style={{ position: 'relative', paddingLeft: '24px' }}>
              {/* Timeline continuous vertical line */}
              <div style={{
                position: 'absolute', top: '16px', bottom: '16px', left: '7px',
                width: '2px', backgroundColor: 'var(--border-color)'
              }} />

              {historial.map((item, idx) => {
                const colorNuevo = getEstadoColor(item.estado_nuevo);
                const colorAnterior = item.estado_anterior ? getEstadoColor(item.estado_anterior) : null;
                const isFirst = idx === 0;

                return (
                  <div key={item.id} style={{ position: 'relative', marginBottom: '22px' }}>
                    {/* Bullet marker */}
                    <div style={{
                      position: 'absolute', left: '-24px', top: '4px',
                      width: '16px', height: '16px', borderRadius: '50%',
                      backgroundColor: isFirst ? colorNuevo.text : 'var(--bg-secondary)',
                      border: `3px solid ${colorNuevo.text}`,
                      boxShadow: isFirst ? `0 0 10px ${colorNuevo.text}66` : 'none',
                      zIndex: 2
                    }} />

                    {/* Event Card */}
                    <div style={{
                      backgroundColor: 'var(--bg-secondary)',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      padding: '12px 14px',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                    }}>
                      {/* Top row: States transition + Date */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {item.estado_anterior ? (
                            <>
                              <span style={{
                                padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                                backgroundColor: colorAnterior.bg, color: colorAnterior.text, border: `1px solid ${colorAnterior.border}`
                              }}>
                                {item.estado_anterior}
                              </span>
                              <ArrowRight size={13} style={{ color: 'var(--text-secondary)' }} />
                            </>
                          ) : null}

                          <span style={{
                            padding: '3px 10px', borderRadius: '4px', fontSize: '12px', fontWeight: 700,
                            backgroundColor: colorNuevo.bg, color: colorNuevo.text, border: `1px solid ${colorNuevo.border}`
                          }}>
                            {item.estado_nuevo}
                          </span>

                          <span style={{
                            fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px',
                            padding: '2px 6px', borderRadius: '4px',
                            backgroundColor: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)'
                          }}>
                            {item.origen}
                          </span>
                        </div>

                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>
                          {formatFecha(item.fecha_cambio)}
                        </span>
                      </div>

                      {/* Motivo / Observación */}
                      {item.motivo && (
                        <div style={{
                          marginTop: '8px', padding: '8px 10px', borderRadius: '6px',
                          backgroundColor: 'rgba(255,255,255,0.03)', borderLeft: `3px solid ${colorNuevo.text}`,
                          fontSize: '12px', color: 'var(--text-primary)', fontStyle: 'italic'
                        }}>
                          "{item.motivo}"
                        </div>
                      )}

                      {/* Footer: User responsible */}
                      <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                        <User size={12} />
                        <span>
                          {item.usuario_nombre
                            ? `${item.usuario_nombre}${item.usuario_email ? ` (${item.usuario_email})` : ''}`
                            : 'Sistema / Automático'}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
          <button onClick={onClose} className="btn-secondary" style={{ padding: '6px 16px' }}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreditHistorialModal;
