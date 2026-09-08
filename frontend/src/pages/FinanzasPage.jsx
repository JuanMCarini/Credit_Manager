import { useState, useCallback, useMemo } from 'react';
import axiosClient from '../api/axiosClient';
import { Calendar, DollarSign, Briefcase, Users, Download } from 'lucide-react';
import ExportExcelButton from '../components/ExportExcelButton';

const FinanzasPage = () => {
  const [mes, setMes] = useState(
    new Date().toISOString().substring(0, 7)
  );
  
  const [colocaciones, setColocaciones] = useState([]);
  const [cobranzas, setCobranzas] = useState([]);
  const [inversores, setInversores] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingInversores, setLoadingInversores] = useState(false);
  const [error, setError] = useState('');
  const [errorInversores, setErrorInversores] = useState('');
  const [activeTab, setActiveTab] = useState('colocacion');

  const handleFetchComisiones = useCallback(async () => {
    if (!mes) return;
    setLoading(true);
    setError('');
    try {
      const [resColocacion, resCobranza] = await Promise.all([
        axiosClient.get('/api/finanzas/comisiones/colocacion', { params: { mes } }),
        axiosClient.get('/api/finanzas/comisiones/cobranza', { params: { mes } })
      ]);
      setColocaciones(resColocacion.data);
      setCobranzas(resCobranza.data);
    } catch (err) {
      console.error(err);
      setError('Error al calcular las comisiones para el período seleccionado.');
    } finally {
      setLoading(false);
    }
  }, [mes]);

  const handleFetchInversores = useCallback(async () => {
    if (!mes) return;
    setLoadingInversores(true);
    setErrorInversores('');
    try {
      const res = await axiosClient.get('/api/finanzas/comisiones/inversores', { params: { mes } });
      setInversores(res.data);
    } catch (err) {
      console.error(err);
      setErrorInversores(err.response?.data?.detail || 'Error al calcular las comisiones de inversores.');
    } finally {
      setLoadingInversores(false);
    }
  }, [mes]);

  const totalColocacionGeneral = useMemo(() => {
    return colocaciones.reduce((acc, c) => acc + (c.total_comisiones || 0), 0);
  }, [colocaciones]);

  const totalCobranzaGeneral = useMemo(() => {
    return cobranzas.reduce((acc, c) => acc + (c.total_comisiones || 0), 0);
  }, [cobranzas]);

  const totalesInversores = useMemo(() => {
    return inversores.reduce((acc, r) => ({
      capital: acc.capital + (r.Capital || 0),
      comision: acc.comision + (r['Comisión'] || 0),
    }), { capital: 0, comision: 0 });
  }, [inversores]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

  const formatPct = (value) => `${((value || 0) * 100).toFixed(2)}%`;

  const totalesColocacion = useMemo(() => {
    return colocaciones.reduce((acc, c) => ({
      capital: acc.capital + (c.total_capital || 0),
      originador: acc.originador + (c.total_colocacion_originador || 0),
      intermediario: acc.intermediario + (c.total_colocacion_intermediario || 0)
    }), { capital: 0, originador: 0, intermediario: 0 });
  }, [colocaciones]);

  const totalesCobranza = useMemo(() => {
    return cobranzas.reduce((acc, c) => ({
      monto: acc.monto + (c.total_monto_cobrado || 0),
      originador: acc.originador + (c.total_cobranza_originador || 0),
      intermediario: acc.intermediario + (c.total_cobranza_intermediario || 0)
    }), { monto: 0, originador: 0, intermediario: 0 });
  }, [cobranzas]);

  const tabs = [
    { key: 'colocacion', label: 'Colocación', icon: <DollarSign size={16} /> },
    { key: 'cobranza',   label: 'Cobranza',   icon: <Briefcase size={16} /> },
    { key: 'inversores', label: 'Inversores', icon: <Users size={16} /> },
  ];

  return (
    <div className="page-container" style={{ padding: '24px', margin: '0 auto' }}>
      <header className="page-header" style={{ marginBottom: '32px' }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '28px', fontWeight: 'bold' }}>
          <Briefcase size={32} color="var(--primary-color)" />
          Finanzas - Liquidación de Comisiones
        </h1>
        <p className="page-description" style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px' }}>
          Calcule y visualice las comisiones de colocación, cobranza e inversores separadas por período.
        </p>
      </header>

      {/* Controls */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: '1', minWidth: '200px' }}>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Calendar size={16} />
              Mes de Liquidación
            </label>
            <input 
              type="month" 
              className="form-control" 
              value={mes} 
              onChange={(e) => setMes(e.target.value)} 
              max={new Date().toISOString().substring(0, 7)}
            />
          </div>
          {activeTab !== 'inversores' ? (
            <button 
              className="btn btn-primary" 
              onClick={handleFetchComisiones} 
              disabled={loading || !mes}
              style={{ height: '42px', padding: '0 24px', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              {loading ? <span className="spinner" /> : <DollarSign size={18} />}
              {loading ? 'Calculando...' : 'Calcular Comisiones'}
            </button>
          ) : (
            <button 
              className="btn btn-primary" 
              onClick={handleFetchInversores} 
              disabled={loadingInversores || !mes}
              style={{ height: '42px', padding: '0 24px', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              {loadingInversores ? <span className="spinner" /> : <Users size={18} />}
              {loadingInversores ? 'Calculando...' : 'Calcular Com. Inversores'}
            </button>
          )}
        </div>
        {error && <div className="alert alert-error" style={{ marginTop: '16px' }}>{error}</div>}
        {errorInversores && activeTab === 'inversores' && (
          <div className="alert alert-error" style={{ marginTop: '16px' }}>{errorInversores}</div>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0', borderBottom: '1px solid var(--border-color)', marginBottom: '24px' }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '12px 24px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.key ? '3px solid var(--primary-color)' : '3px solid transparent',
              color: activeTab === tab.key ? 'var(--primary-color)' : 'var(--text-muted)',
              fontWeight: activeTab === tab.key ? '600' : '400',
              cursor: 'pointer',
              fontSize: '15px',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '7px',
            }}
          >
            {tab.icon}{tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Colocación ── */}
      {activeTab === 'colocacion' && (
        <div>
          <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '24px', maxWidth: '400px' }}>
            <div className="stat-icon" style={{ background: 'rgba(var(--primary-rgb), 0.1)', color: 'var(--primary-color)', padding: '16px', borderRadius: '50%' }}>
              <DollarSign size={32} />
            </div>
            <div className="stat-content">
              <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Total Colocación</p>
              <h3 className="stat-value" style={{ fontSize: '28px', fontWeight: 'bold', margin: 0 }}>
                {formatCurrency(totalColocacionGeneral)}
              </h3>
            </div>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: '600' }}>Detalle de Colocación</h3>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ textAlign: 'center' }}>ID Socio</th>
                    <th>Razón Social</th>
                    <th style={{ textAlign: 'center' }}>Plazo</th>
                    <th style={{ textAlign: 'right' }}>Saldo de Capital</th>
                    <th style={{ textAlign: 'right' }}>Comisión (Originador)</th>
                    <th style={{ textAlign: 'right' }}>Comisión (Intermediario)</th>
                    <th style={{ textAlign: 'right' }}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {colocaciones.length === 0 ? (
                    <tr><td colSpan="7" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>No hay datos para mostrar</td></tr>
                  ) : (
                    colocaciones.map((c, i) => (
                      <tr key={i}>
                        <td style={{ textAlign: 'center' }}>{c.socio_id}</td>
                        <td>{c.razon_social}</td>
                        <td style={{ textAlign: 'center' }}>{c.plazo}</td>
                        <td style={{ textAlign: 'right' }}>{formatCurrency(c.total_capital)}</td>
                        <td style={{ textAlign: 'right' }}>{formatCurrency(c.total_colocacion_originador)}</td>
                        <td style={{ textAlign: 'right' }}>{formatCurrency(c.total_colocacion_intermediario)}</td>
                        <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{formatCurrency(c.total_comisiones)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
                {colocaciones.length > 0 && (
                  <tfoot>
                    <tr style={{ background: 'var(--surface-color)', fontWeight: 'bold' }}>
                      <td colSpan="3" style={{ textAlign: 'right' }}>TOTALES:</td>
                      <td style={{ textAlign: 'right', color: 'var(--primary-color)' }}>{formatCurrency(totalesColocacion.capital)}</td>
                      <td style={{ textAlign: 'right', color: 'var(--primary-color)' }}>{formatCurrency(totalesColocacion.originador)}</td>
                      <td style={{ textAlign: 'right', color: 'var(--primary-color)' }}>{formatCurrency(totalesColocacion.intermediario)}</td>
                      <td style={{ textAlign: 'right', color: 'var(--primary-color)', fontSize: '1.1em' }}>{formatCurrency(totalColocacionGeneral)}</td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Cobranza ── */}
      {activeTab === 'cobranza' && (
        <div>
          <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '24px', maxWidth: '400px' }}>
            <div className="stat-icon" style={{ background: 'rgba(var(--secondary-rgb), 0.1)', color: 'var(--secondary-color)', padding: '16px', borderRadius: '50%' }}>
              <Briefcase size={32} />
            </div>
            <div className="stat-content">
              <p className="stat-label" style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Total Cobranza</p>
              <h3 className="stat-value" style={{ fontSize: '28px', fontWeight: 'bold', margin: 0 }}>
                {formatCurrency(totalCobranzaGeneral)}
              </h3>
            </div>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: '600' }}>Detalle de Cobranza</h3>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ textAlign: 'center' }}>ID Socio</th>
                    <th>Razón Social</th>
                    <th style={{ textAlign: 'center' }}>Fecha Cobranza</th>
                    <th style={{ textAlign: 'center' }}>ID Proceso</th>
                    <th style={{ textAlign: 'right' }}>Monto Cobrado Total</th>
                    <th style={{ textAlign: 'right' }}>Comisión (Originador)</th>
                    <th style={{ textAlign: 'right' }}>Comisión (Intermediario)</th>
                    <th style={{ textAlign: 'right' }}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {cobranzas.length === 0 ? (
                    <tr><td colSpan="8" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>No hay datos para mostrar</td></tr>
                  ) : (
                    cobranzas.map((c, i) => (
                      <tr key={i}>
                        <td style={{ textAlign: 'center' }}>{c.socio_id}</td>
                        <td>{c.razon_social}</td>
                        <td style={{ textAlign: 'center' }}>{c.fecha}</td>
                        <td style={{ textAlign: 'center' }}>{c.proceso_id || 'N/A'}</td>
                        <td style={{ textAlign: 'right' }}>{formatCurrency(c.total_monto_cobrado)}</td>
                        <td style={{ textAlign: 'right' }}>{formatCurrency(c.total_cobranza_originador)}</td>
                        <td style={{ textAlign: 'right' }}>{formatCurrency(c.total_cobranza_intermediario)}</td>
                        <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{formatCurrency(c.total_comisiones)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
                {cobranzas.length > 0 && (
                  <tfoot>
                    <tr style={{ background: 'var(--surface-color)', fontWeight: 'bold' }}>
                      <td colSpan="4" style={{ textAlign: 'right' }}>TOTALES:</td>
                      <td style={{ textAlign: 'right', color: 'var(--primary-color)' }}>{formatCurrency(totalesCobranza.monto)}</td>
                      <td style={{ textAlign: 'right', color: 'var(--primary-color)' }}>{formatCurrency(totalesCobranza.originador)}</td>
                      <td style={{ textAlign: 'right', color: 'var(--primary-color)' }}>{formatCurrency(totalesCobranza.intermediario)}</td>
                      <td style={{ textAlign: 'right', color: 'var(--primary-color)', fontSize: '1.1em' }}>{formatCurrency(totalCobranzaGeneral)}</td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Inversores ── */}
      {activeTab === 'inversores' && (
        <div>
          {/* Summary cards */}
          <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' }}>
            <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px', flex: '1', minWidth: '220px' }}>
              <div style={{ background: 'rgba(var(--primary-rgb), 0.1)', color: 'var(--primary-color)', padding: '16px', borderRadius: '50%' }}>
                <DollarSign size={28} />
              </div>
              <div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Capital Suscripto</p>
                <h3 style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>{formatCurrency(totalesInversores.capital)}</h3>
              </div>
            </div>
            <div className="stat-card" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '20px', flex: '1', minWidth: '220px' }}>
              <div style={{ background: 'rgba(var(--success-rgb, 34,197,94), 0.1)', color: 'var(--success-color)', padding: '16px', borderRadius: '50%' }}>
                <Users size={28} />
              </div>
              <div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px', fontWeight: '500' }}>Total Comisión Inversores</p>
                <h3 style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>{formatCurrency(totalesInversores.comision)}</h3>
              </div>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '600', margin: 0 }}>Detalle de Comisiones — Inversores</h3>
              {inversores.length > 0 && (
                <ExportExcelButton
                  data={inversores}
                  filename={`Comisiones_Inversores_${mes}`}
                />
              )}
            </div>

            {inversores.length === 0 && !loadingInversores ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                <Users size={40} style={{ marginBottom: '12px', opacity: 0.4 }} />
                <p>Presioná <strong>"Calcular Com. Inversores"</strong> para ver el detalle del mes seleccionado.</p>
                <p style={{ fontSize: '13px', marginTop: '8px' }}>Solo se incluyen movimientos de tipo Suscripción y Renovación Suscripción de series con comisión asignada.</p>
              </div>
            ) : (
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Socio Comercial</th>
                      <th>Serie</th>
                      <th style={{ textAlign: 'right' }}>Capital</th>
                      <th style={{ textAlign: 'right' }}>TNA</th>
                      <th style={{ textAlign: 'center' }}>Plazo (días)</th>
                      <th style={{ textAlign: 'right' }}>% Comisión</th>
                      <th style={{ textAlign: 'right', fontWeight: 'bold' }}>Comisión</th>
                    </tr>
                  </thead>
                  <tbody>
                    {inversores.map((r, i) => (
                      <tr key={i}>
                        <td><strong>{r.Socio}</strong></td>
                        <td>{r.Serie}</td>
                        <td style={{ textAlign: 'right' }}>{formatCurrency(r.Capital)}</td>
                        <td style={{ textAlign: 'right' }}>{formatPct(r.TNA)}</td>
                        <td style={{ textAlign: 'center' }}>{r.Plazo}</td>
                        <td style={{ textAlign: 'right' }}>{formatPct(r['% Comisión'])}</td>
                        <td style={{ textAlign: 'right', fontWeight: 'bold', color: 'var(--success-color)' }}>
                          {formatCurrency(r['Comisión'])}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  {inversores.length > 0 && (
                    <tfoot>
                      <tr style={{ background: 'var(--surface-color)', fontWeight: 'bold' }}>
                        <td colSpan="2" style={{ textAlign: 'right' }}>TOTALES ({inversores.length} filas):</td>
                        <td style={{ textAlign: 'right', color: 'var(--primary-color)' }}>{formatCurrency(totalesInversores.capital)}</td>
                        <td colSpan="3"></td>
                        <td style={{ textAlign: 'right', color: 'var(--success-color)', fontSize: '1.1em' }}>{formatCurrency(totalesInversores.comision)}</td>
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default FinanzasPage;

