import React, { useState, useEffect, useMemo } from 'react';
import axiosClient from '../api/axiosClient';

const calcularNuevaFecha = (fechaDDMMYYYY, deltaMeses, diaVto) => {
  if (!fechaDDMMYYYY || !deltaMeses) return fechaDDMMYYYY || '-';
  const parts = fechaDDMMYYYY.split('/');
  if (parts.length !== 3) return fechaDDMMYYYY;
  const day = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1;
  const year = parseInt(parts[2], 10);

  const targetFirst = new Date(year, month + deltaMeses, 1);
  const targetYear = targetFirst.getFullYear();
  const targetMonth = targetFirst.getMonth();
  const lastDayOfTargetMonth = new Date(targetYear, targetMonth + 1, 0).getDate();

  const desiredDay = diaVto || day;
  const finalDay = Math.min(desiredDay, lastDayOfTargetMonth);

  const dd = String(finalDay).padStart(2, '0');
  const mm = String(targetMonth + 1).padStart(2, '0');
  return `${dd}/${mm}/${targetYear}`;
};

const CreditShiftVencimientosModal = ({ credito, onClose, onSuccess }) => {
  const creditoId = credito?.id;
  const diaVencimiento = credito?.diaVto || 28;

  const [sentido, setSentido] = useState(1); // 1 = adelante, -1 = atrás
  const [cantidadMeses, setCantidadMeses] = useState(1);
  const [motivo, setMotivo] = useState('');
  const [cuotas, setCuotas] = useState([]);
  const [loadingCuotas, setLoadingCuotas] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    if (!creditoId) return;
    let active = true;
    setLoadingCuotas(true);
    axiosClient
      .get(`/api/v1/creditos/${creditoId}/cuotas`)
      .then((res) => {
        if (active) setCuotas(res.data || []);
      })
      .catch((err) => {
        if (active) {
          setFeedback({
            type: 'error',
            message: err.response?.data?.detail || err.message || 'Error al cargar cuotas',
          });
        }
      })
      .finally(() => {
        if (active) setLoadingCuotas(false);
      });
    return () => {
      active = false;
    };
  }, [creditoId]);

  const deltaMeses = useMemo(() => {
    const num = parseInt(cantidadMeses, 10);
    if (isNaN(num) || num <= 0) return 0;
    return sentido * num;
  }, [sentido, cantidadMeses]);

  const cuotasElegibles = useMemo(() => {
    return cuotas.filter((c) => !['CANCELADA', 'NO COMPRADA'].includes(c.estado));
  }, [cuotas]);

  const cuotasCanceladasCount = useMemo(() => {
    return cuotas.filter((c) => c.estado === 'CANCELADA').length;
  }, [cuotas]);

  const handleQuickSelect = (val) => {
    setSentido(val > 0 ? 1 : -1);
    setCantidadMeses(Math.abs(val));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (deltaMeses === 0) {
      setFeedback({ type: 'error', message: 'La cantidad de meses debe ser mayor a 0.' });
      return;
    }
    if (cuotasElegibles.length === 0) {
      setFeedback({ type: 'error', message: 'No hay cuotas no canceladas para desplazar.' });
      return;
    }

    setSaving(true);
    setFeedback(null);

    try {
      await axiosClient.patch(`/api/v1/creditos/${creditoId}/correr-vencimientos`, {
        meses: deltaMeses,
        motivo: motivo.trim() || null,
      });
      onSuccess();
      onClose();
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.detail || err.message || 'Error al correr vencimientos',
      });
      setSaving(false);
    }
  };

  const QUICK_VALUES = [-3, -2, -1, 1, 2, 3, 6];

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0,0,0,0.55)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        backdropFilter: 'blur(5px)',
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '580px',
          position: 'relative',
          padding: '24px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '15px',
            right: '15px',
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: '20px',
          }}
        >
          ✕
        </button>

        <h2 style={{ marginBottom: '6px', fontFamily: 'var(--font-heading)' }}>
          Correr Vencimientos (Crédito #{creditoId})
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '18px' }}>
          Desplaza las fechas de vencimiento de las cuotas <strong>no canceladas</strong> hacia atrás o hacia adelante.
        </p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '14px' }}>
            <div className="form-group">
              <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500, fontSize: '13px' }}>
                Sentido del desplazamiento
              </label>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  type="button"
                  onClick={() => setSentido(-1)}
                  style={{
                    flex: 1,
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: sentido === -1 ? 'var(--accent-primary)' : 'var(--border-color)',
                    backgroundColor: sentido === -1 ? 'rgba(59, 130, 246, 0.2)' : 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontWeight: sentido === -1 ? 600 : 400,
                    cursor: 'pointer',
                    fontSize: '13px',
                  }}
                >
                  ⏪ Hacia atrás (-)
                </button>
                <button
                  type="button"
                  onClick={() => setSentido(1)}
                  style={{
                    flex: 1,
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: sentido === 1 ? 'var(--accent-primary)' : 'var(--border-color)',
                    backgroundColor: sentido === 1 ? 'rgba(59, 130, 246, 0.2)' : 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontWeight: sentido === 1 ? 600 : 400,
                    cursor: 'pointer',
                    fontSize: '13px',
                  }}
                >
                  Hacia adelante (+) ⏩
                </button>
              </div>
            </div>

            <div className="form-group">
              <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500, fontSize: '13px' }}>
                Cantidad de meses
              </label>
              <input
                type="number"
                min="1"
                max="120"
                value={cantidadMeses}
                onChange={(e) => setCantidadMeses(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', marginRight: '4px' }}>
              Selección rápida:
            </span>
            {QUICK_VALUES.map((val) => {
              const isSelected = deltaMeses === val;
              return (
                <button
                  key={val}
                  type="button"
                  onClick={() => handleQuickSelect(val)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '12px',
                    borderRadius: '4px',
                    border: '1px solid',
                    borderColor: isSelected ? 'var(--accent-primary)' : 'var(--border-color)',
                    backgroundColor: isSelected ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)',
                    color: isSelected ? '#fff' : 'var(--text-primary)',
                    cursor: 'pointer',
                    fontWeight: isSelected ? 600 : 400,
                  }}
                >
                  {val > 0 ? `+${val}` : val} {Math.abs(val) === 1 ? 'mes' : 'meses'}
                </button>
              );
            })}
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '8px',
              fontSize: '12px',
              color: 'var(--text-secondary)',
            }}
          >
            <span>
              Cuotas a modificar: <strong style={{ color: 'var(--text-primary)' }}>{cuotasElegibles.length}</strong>
              {cuotasCanceladasCount > 0 && ` (${cuotasCanceladasCount} canceladas sin cambios)`}
            </span>
            {deltaMeses !== 0 && (
              <span style={{ color: 'var(--accent-secondary)', fontWeight: 600 }}>
                Desplazamiento: {deltaMeses > 0 ? `+${deltaMeses}` : deltaMeses}{' '}
                {Math.abs(deltaMeses) === 1 ? 'mes' : 'meses'}
              </span>
            )}
          </div>

          <div
            style={{
              background: 'rgba(0,0,0,0.25)',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              overflowY: 'auto',
              maxHeight: '220px',
              marginBottom: '16px',
            }}
          >
            {loadingCuotas ? (
              <div style={{ padding: '20px', textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary)' }}>
                Cargando cuotas del crédito...
              </div>
            ) : cuotasElegibles.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary)' }}>
                Este crédito no tiene cuotas pendientes o en mora para modificar.
              </div>
            ) : (
              <table className="data-table compact" style={{ width: '100%', fontSize: '12px' }}>
                <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-panel)', zIndex: 2 }}>
                  <tr>
                    <th style={{ padding: '8px 10px', textAlign: 'center' }}>Cuota #</th>
                    <th style={{ padding: '8px 10px', textAlign: 'left' }}>Estado Actual</th>
                    <th style={{ padding: '8px 10px', textAlign: 'center' }}>Vto. Actual</th>
                    <th style={{ padding: '8px 10px', textAlign: 'center' }}>Nuevo Vto.</th>
                  </tr>
                </thead>
                <tbody>
                  {cuotasElegibles.map((c) => {
                    const nuevoVto = calcularNuevaFecha(
                      c.vencimiento,
                      deltaMeses,
                      c.nro_cuota === 99 ? null : diaVencimiento
                    );
                    return (
                      <tr key={c.nro_cuota}>
                        <td style={{ padding: '6px 10px', textAlign: 'center' }}>{c.nro_cuota}</td>
                        <td style={{ padding: '6px 10px', textAlign: 'left' }}>{c.estado}</td>
                        <td style={{ padding: '6px 10px', textAlign: 'center', opacity: 0.8 }}>{c.vencimiento}</td>
                        <td
                          style={{
                            padding: '6px 10px',
                            textAlign: 'center',
                            fontWeight: 600,
                            color: deltaMeses !== 0 ? 'var(--accent-secondary)' : 'var(--text-primary)',
                          }}
                        >
                          {nuevoVto}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500, fontSize: '13px' }}>
              Motivo / Observación (Opcional)
            </label>
            <input
              type="text"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Ej: Prórroga acordada / Corrección de fecha de primer vencimiento..."
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                fontSize: '13px',
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto' }}>
            <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--error)' }}>{feedback?.message || ''}</div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="button" onClick={onClose} className="btn-secondary" disabled={saving}>
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={saving || loadingCuotas || cuotasElegibles.length === 0 || deltaMeses === 0}
              >
                {saving ? 'Aplicando...' : 'Confirmar Corrimiento'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreditShiftVencimientosModal;

