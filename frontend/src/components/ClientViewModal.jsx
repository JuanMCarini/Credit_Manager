import React, { useState, useEffect } from 'react';
import { X, AlertCircle, Clock, User, ArrowRight, Info } from 'lucide-react';
import axiosClient from '../api/axiosClient';

const getEstadoClienteColor = (estado) => {
  switch (estado?.toUpperCase()) {
    case 'ACTIVO':
      return { bg: 'rgba(16, 185, 129, 0.15)', text: '#10b981', border: 'rgba(16, 185, 129, 0.3)' };
    case 'MOROSO':
      return { bg: 'rgba(245, 158, 11, 0.15)', text: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' };
    case 'INCOBRABLE':
      return { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444', border: 'rgba(239, 68, 68, 0.3)' };
    case 'INACTIVO':
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

const ClientViewModal = ({ client, onClose }) => {
  const [activeTab, setActiveTab] = useState('datos'); // 'datos' | 'historial'
  const [riesgo, setRiesgo] = useState(null);
  const [loadingRiesgo, setLoadingRiesgo] = useState(false);

  const [historial, setHistorial] = useState([]);
  const [loadingHistorial, setLoadingHistorial] = useState(false);
  const [errorHistorial, setErrorHistorial] = useState(null);

  useEffect(() => {
    if (client?.CUIL) {
      setLoadingRiesgo(true);
      axiosClient.get(`/api/v1/clientes/${client.CUIL}/riesgo`)
        .then(res => setRiesgo(res.data.nivel_riesgo))
        .catch(err => console.error("Error fetching riesgo:", err))
        .finally(() => setLoadingRiesgo(false));
    }
  }, [client]);

  useEffect(() => {
    if (activeTab === 'historial' && client?.CUIL) {
      setLoadingHistorial(true);
      setErrorHistorial(null);
      axiosClient.get(`/api/v1/clientes/${client.CUIL}/historial-estados`)
        .then(res => setHistorial(res.data || []))
        .catch(err => setErrorHistorial(err.response?.data?.detail || err.message || 'Error al obtener historial'))
        .finally(() => setLoadingHistorial(false));
    }
  }, [activeTab, client]);

  if (!client) return null;

  const excludeKeys = ['Apellido y Nombre'];
  const entries = Object.entries(client).filter(([key]) => !excludeKeys.includes(key));
  
  if (riesgo) {
    entries.push(["Nivel de Riesgo UIF", riesgo]);
  } else if (loadingRiesgo) {
    entries.push(["Nivel de Riesgo UIF", "Calculando..."]);
  }

  const formatValue = (key, value) => {
    if (value === null || value === '') return '-';
    if (key === 'Remuneración' && !isNaN(value)) {
      return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value);
    }
    return value;
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1000, animation: 'fadeIn 0.3s ease' }}>
      <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()} style={{ width: '680px', maxWidth: '90%', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div className="modal-header" style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0, color: 'var(--text-color)' }}>
              {client.Nombre ? `${client.Nombre} ${client.Apellido || ''}` : 'Datos del Cliente'}
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>CUIL: {client.CUIL}</span>
          </div>
          <button className="btn-secondary" onClick={onClose} style={{ padding: '4px 8px' }}>
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '8px', padding: '12px 24px 0 24px', borderBottom: '1px solid var(--border-color)' }}>
          <button
            onClick={() => setActiveTab('datos')}
            style={{
              padding: '8px 16px', background: 'none', border: 'none',
              borderBottom: activeTab === 'datos' ? '2px solid var(--primary-color, #6366f1)' : '2px solid transparent',
              color: activeTab === 'datos' ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: 600, fontSize: '13px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            <Info size={15} />
            Datos Generales
          </button>
          <button
            onClick={() => setActiveTab('historial')}
            style={{
              padding: '8px 16px', background: 'none', border: 'none',
              borderBottom: activeTab === 'historial' ? '2px solid var(--primary-color, #6366f1)' : '2px solid transparent',
              color: activeTab === 'historial' ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: 600, fontSize: '13px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            <Clock size={15} />
            Historial de Estados
          </button>
        </div>
        
        {/* Body */}
        <div className="modal-body" style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'datos' ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              {entries.map(([key, value]) => (
                <div key={key} style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-color)', opacity: 0.7, fontWeight: 'bold', marginBottom: '4px' }}>
                    {key}
                  </span>
                  <span style={{ 
                    fontSize: '14px', 
                    color: key === 'Nivel de Riesgo UIF' && typeof value === 'string' && (value.toUpperCase() === 'ALTO' || value.toUpperCase() === 'DENEGADO') ? '#f43f5e' :
                           key === 'Nivel de Riesgo UIF' && typeof value === 'string' && value.toUpperCase() === 'MEDIO' ? '#f59e0b' : 
                           key === 'Nivel de Riesgo UIF' && typeof value === 'string' && value.toUpperCase() === 'BAJO' ? '#10b981' : 'var(--text-color)', 
                    background: 'rgba(255,255,255,0.05)', 
                    padding: '8px', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border-color)',
                    fontWeight: key === 'Nivel de Riesgo UIF' ? 'bold' : 'normal',
                    display: 'flex', alignItems: 'center', gap: '8px'
                  }}>
                    {key === 'Nivel de Riesgo UIF' && value !== 'Calculando...' && <AlertCircle size={16} />}
                    {formatValue(key, value)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div>
              {loadingHistorial && (
                <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-secondary)' }}>
                  Cargando historial de cambios de estado...
                </div>
              )}

              {errorHistorial && (
                <div style={{ padding: '10px 14px', borderRadius: '6px', backgroundColor: 'rgba(239,68,68,0.1)', color: 'var(--error)' }}>
                  {errorHistorial}
                </div>
              )}

              {!loadingHistorial && !errorHistorial && historial.length === 0 && (
                <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--text-secondary)' }}>
                  No hay registros de historial de estado para este cliente.
                </div>
              )}

              {!loadingHistorial && !errorHistorial && historial.length > 0 && (
                <div style={{ position: 'relative', paddingLeft: '20px' }}>
                  <div style={{
                    position: 'absolute', top: '14px', bottom: '14px', left: '7px',
                    width: '2px', backgroundColor: 'var(--border-color)'
                  }} />

                  {historial.map((item, idx) => {
                    const colorNuevo = getEstadoClienteColor(item.estado_nuevo);
                    const colorAnterior = item.estado_anterior ? getEstadoClienteColor(item.estado_anterior) : null;
                    const isFirst = idx === 0;

                    return (
                      <div key={item.id} style={{ position: 'relative', marginBottom: '18px' }}>
                        <div style={{
                          position: 'absolute', left: '-20px', top: '4px',
                          width: '14px', height: '14px', borderRadius: '50%',
                          backgroundColor: isFirst ? colorNuevo.text : 'var(--bg-secondary)',
                          border: `2px solid ${colorNuevo.text}`,
                          zIndex: 2
                        }} />

                        <div style={{
                          backgroundColor: 'var(--bg-secondary)',
                          borderRadius: '8px',
                          border: '1px solid var(--border-color)',
                          padding: '10px 12px'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              {item.estado_anterior && (
                                <>
                                  <span style={{
                                    padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                                    backgroundColor: colorAnterior.bg, color: colorAnterior.text, border: `1px solid ${colorAnterior.border}`
                                  }}>
                                    {item.estado_anterior}
                                  </span>
                                  <ArrowRight size={12} style={{ color: 'var(--text-secondary)' }} />
                                </>
                              )}

                              <span style={{
                                padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700,
                                backgroundColor: colorNuevo.bg, color: colorNuevo.text, border: `1px solid ${colorNuevo.border}`
                              }}>
                                {item.estado_nuevo}
                              </span>

                              <span style={{
                                fontSize: '10px', textTransform: 'uppercase',
                                padding: '1px 5px', borderRadius: '3px',
                                backgroundColor: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)'
                              }}>
                                {item.origen}
                              </span>
                            </div>

                            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                              {formatFecha(item.fecha_cambio)}
                            </span>
                          </div>

                          {item.motivo && (
                            <div style={{
                              marginTop: '6px', padding: '6px 8px', borderRadius: '4px',
                              backgroundColor: 'rgba(255,255,255,0.03)', borderLeft: `3px solid ${colorNuevo.text}`,
                              fontSize: '11px', color: 'var(--text-primary)', fontStyle: 'italic'
                            }}>
                              "{item.motivo}"
                            </div>
                          )}

                          <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: '5px', fontSize: '10px', color: 'var(--text-secondary)' }}>
                            <User size={11} />
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
          )}
        </div>
        
        {/* Footer */}
        <div className="modal-footer" style={{ padding: '16px 24px', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-secondary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClientViewModal;
