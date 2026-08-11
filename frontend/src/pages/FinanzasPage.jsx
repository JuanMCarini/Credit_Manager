import { useState, useCallback, useMemo } from 'react';
import axiosClient from '../api/axiosClient';
import { Calendar, DollarSign, Briefcase, Download, Filter, Landmark } from 'lucide-react';

const FinanzasPage = () => {
  const [mes, setMes] = useState(
    new Date().toISOString().substring(0, 7)
  );
  
  const [colocaciones, setColocaciones] = useState([]);
  const [cobranzas, setCobranzas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
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

  const totalColocacionGeneral = useMemo(() => {
    return colocaciones.reduce((acc, c) => acc + (c.total_comisiones || 0), 0);
  }, [colocaciones]);

  const totalCobranzaGeneral = useMemo(() => {
    return cobranzas.reduce((acc, c) => acc + (c.total_comisiones || 0), 0);
  }, [cobranzas]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2
    }).format(value || 0);
  };

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

  return (
    <div className="page-container" style={{ padding: '24px', margin: '0 auto' }}>
      <header className="page-header" style={{ marginBottom: '32px' }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '28px', fontWeight: 'bold' }}>
          <Briefcase size={32} color="var(--primary-color)" />
          Finanzas - Liquidación de Comisiones
        </h1>
        <p className="page-description" style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px' }}>
          Calcule y visualice las comisiones de colocación y cobranza separadas por detalle de plazo y fecha.
        </p>
      </header>

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
          <button 
            className="btn btn-primary" 
            onClick={handleFetchComisiones} 
            disabled={loading || !mes}
            style={{ height: '42px', padding: '0 24px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            {loading ? <span className="spinner" /> : <DollarSign size={18} />}
            {loading ? 'Calculando...' : 'Calcular Comisiones'}
          </button>
        </div>
        {error && <div className="alert alert-error" style={{ marginTop: '16px' }}>{error}</div>}
      </div>

      <div style={{ display: 'flex', gap: '16px', borderBottom: '1px solid var(--border-color)', marginBottom: '24px' }}>
        <button
          onClick={() => setActiveTab('colocacion')}
          style={{
            padding: '12px 24px',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'colocacion' ? '3px solid var(--primary-color)' : '3px solid transparent',
            color: activeTab === 'colocacion' ? 'var(--primary-color)' : 'var(--text-muted)',
            fontWeight: activeTab === 'colocacion' ? '600' : '400',
            cursor: 'pointer',
            fontSize: '16px',
            transition: 'all 0.2s'
          }}
        >
          Colocación
        </button>
        <button
          onClick={() => setActiveTab('cobranza')}
          style={{
            padding: '12px 24px',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'cobranza' ? '3px solid var(--primary-color)' : '3px solid transparent',
            color: activeTab === 'cobranza' ? 'var(--primary-color)' : 'var(--text-muted)',
            fontWeight: activeTab === 'cobranza' ? '600' : '400',
            cursor: 'pointer',
            fontSize: '16px',
            transition: 'all 0.2s'
          }}
        >
          Cobranza
        </button>
      </div>

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
                    <tr>
                      <td colSpan="7" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                        No hay datos para mostrar
                      </td>
                    </tr>
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
                    <tr>
                      <td colSpan="8" style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                        No hay datos para mostrar
                      </td>
                    </tr>
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
    </div>
  );
};

export default FinanzasPage;

