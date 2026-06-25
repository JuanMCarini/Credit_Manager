import { useState } from 'react';
import axiosClient from '../api/axiosClient';
import ExportExcelButton from '../components/ExportExcelButton';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const SimulationPage = () => {
  const [loading, setLoading] = useState(false);
  const [cuotas, setCuotas] = useState([]);
  const [form, setForm] = useState({
    capital: 100000,
    plazo: 12,
    tna: 105,
    fecha: new Date().toISOString().split('T')[0],
    vto: 28,
    gracia: 2,
    iva: 0.21
  });

  const handleSimulation = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const params = {
        credito_id: 0,
        capital: form.capital,
        tna_c_iva: parseFloat(form.tna) / 100,
        plazo: form.plazo,
        fecha_emision: form.fecha,
        dia_vencimiento: form.vto,
        gracia: form.gracia,
        tasa_iva: form.iva,
        dia_corte: 28
      };
      
      const res = await axiosClient.get('/api/v1/creditos/simular-cuotas', { params });
      setCuotas(res.data);
    } catch (error) {
      alert("Ocurrió un error al simular: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const totals = cuotas.reduce((acc, c) => ({
    capital: acc.capital + c.capital,
    interes: acc.interes + c.interes,
    iva: acc.iva + c.iva,
    total: acc.total + c.capital + c.interes + c.iva
  }), { capital: 0, interes: 0, iva: 0, total: 0 });

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Simulador de Amortización (Sistema Francés)</h2>
        <p>Calcule cronogramas de pagos utilizando el motor financiero de Credit Manager.</p>
      </header>

      <div className="content-grid">
        <div className="form-container glass-panel">
          <form onSubmit={handleSimulation}>
            <div className="form-group">
              <label>Capital a financiar ($)</label>
              <input type="number" step="0.01" value={form.capital} onChange={(e) => setForm({...form, capital: e.target.value})} required />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Plazo (Cuotas)</label>
                <input type="number" value={form.plazo} onChange={(e) => setForm({...form, plazo: e.target.value})} required />
              </div>
              <div className="form-group">
                <label>TNA c/IVA (%)</label>
                <input type="number" step="0.01" value={form.tna} onChange={(e) => setForm({...form, tna: e.target.value})} required />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Fecha Emisión</label>
                <input type="date" value={form.fecha} onChange={(e) => setForm({...form, fecha: e.target.value})} required />
              </div>
              <div className="form-group">
                <label>Día Vencimiento</label>
                <input type="number" value={form.vto} onChange={(e) => setForm({...form, vto: e.target.value})} required />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Meses Gracia</label>
                <input type="number" value={form.gracia} onChange={(e) => setForm({...form, gracia: e.target.value})} required />
              </div>
              <div className="form-group">
                <label>Alícuota IVA</label>
                <input type="number" step="0.01" value={form.iva} onChange={(e) => setForm({...form, iva: e.target.value})} required />
              </div>
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Calculando..." : "Generar Cronograma"}
            </button>
          </form>
        </div>

        <div className="results-container glass-panel">
          <div className="results-header">
            <h3>Cronograma Resultante</h3>
            {cuotas.length > 0 && (
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <ExportExcelButton data={cuotas} filteredData={cuotas} filename="simulacion_export" />
                <div className="summary-pills" style={{ display: 'flex' }}>
                  <div className="pill">Cuotas: {cuotas.length}</div>
                  <div className="pill">Total a Pagar: {formatCurrency(totals.total)}</div>
                </div>
              </div>
            )}
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nro</th>
                  <th>Vencimiento</th>
                  <th>Capital</th>
                  <th>Interés</th>
                  <th>IVA</th>
                  <th>Total Cuota</th>
                </tr>
              </thead>
              <tbody>
                {cuotas.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="text-center empty-state">Ingrese los datos y simule para ver resultados.</td>
                  </tr>
                ) : (
                  cuotas.map((c, i) => (
                    <tr key={i}>
                      <td>{c.nro_cuota}</td>
                      <td>{c.fecha_vencimiento}</td>
                      <td>{formatCurrency(c.capital)}</td>
                      <td>{formatCurrency(c.interes)}</td>
                      <td>{formatCurrency(c.iva)}</td>
                      <td style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>{formatCurrency(c.capital + c.interes + c.iva)}</td>
                    </tr>
                  ))
                )}
              </tbody>
              {cuotas.length > 0 && (
                <tfoot style={{ background: 'rgba(255, 255, 255, 0.05)', fontWeight: 'bold' }}>
                  <tr>
                    <td colSpan="2" style={{ textAlign: 'right' }}>TOTALES:</td>
                    <td>{formatCurrency(totals.capital)}</td>
                    <td>{formatCurrency(totals.interes)}</td>
                    <td>{formatCurrency(totals.iva)}</td>
                    <td style={{ color: 'var(--accent-primary)' }}>{formatCurrency(totals.total)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>
      </div>
    </section>
  );
};

export default SimulationPage;
