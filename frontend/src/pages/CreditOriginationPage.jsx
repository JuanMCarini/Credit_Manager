import { useState } from 'react';
import axiosClient from '../api/axiosClient';
import useAppStore from '../store/useAppStore';
import ClientForm from '../components/ClientForm';
import ClientCCModal from '../components/ClientCCModal';
import TransfersForm from '../components/TransfersForm';
import CurrencyInput from '../components/CurrencyInput';

const formatCurrency = (value) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value);
};

const CreditOriginationPage = () => {
  const { empleadores, socios, tasasYComisiones } = useAppStore();
  
  const [step, setStep] = useState(1); // 1: Search, 2: ClientForm, 3: CreditForm
  const [searchCuil, setSearchCuil] = useState('');
  const [cliente, setCliente] = useState(null);
  const [isClientNew, setIsClientNew] = useState(false);
  
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [loadingClient, setLoadingClient] = useState(false);
  const [clientFeedback, setClientFeedback] = useState(null);
  const [loadingSimulation, setLoadingSimulation] = useState(false);
  const [simulation, setSimulation] = useState(null);
  const [transfers, setTransfers] = useState([]);
  const [loadingCredit, setLoadingCredit] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  
  const [bcraData, setBcraData] = useState(null);
  const [loadingBcra, setLoadingBcra] = useState(false);

  const [ccModalData, setCcModalData] = useState(null);
  
  const [computedCapitalBruto, setComputedCapitalBruto] = useState(0);

  const [creditoForm, setCreditoForm] = useState({
    capital_neto: '',
    tasa_id: '',
    tipo: 'SISTEMA FRANCES',
    socio_id: '',
    fecha_emision: new Date().toISOString().split('T')[0],
    id_externo: ''
  });

  const fetchBcraData = async (cuil) => {
    setLoadingBcra(true);
    setBcraData(null);
    try {
      const res = await axiosClient.get(`/api/v1/clientes/${cuil}/bcra`);
      setBcraData(res.data);
    } catch (error) {
      console.error("Error fetching BCRA data", error);
      setBcraData({ Estado: "Error de Conexión", Error: error.message });
    } finally {
      setLoadingBcra(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchCuil) return;
    setLoadingSearch(true);
    setClientFeedback(null);
    try {
      const res = await axiosClient.get(`/api/v1/clientes/${searchCuil}`);
      setCliente(res.data);
      setIsClientNew(false);
      setStep(2);
    } catch (error) {
      if (error.response?.status === 404) {
        // Asumimos que puede ser DNI o CUIL
        const isDNI = searchCuil.length <= 8;
        setCliente({ cuil: isDNI ? '' : searchCuil, documento: isDNI ? searchCuil : '' });
        setIsClientNew(true);
        setStep(2);
      } else {
        alert("Error al buscar cliente.");
      }
    } finally {
      setLoadingSearch(false);
    }
  };

  const handleClientSubmit = async (formData) => {
    setLoadingClient(true);
    setClientFeedback(null);
    try {
      // Clean up empty strings to null for foreign keys and optional fields
      const cleanData = { ...formData };
      ['id_provincia', 'empleador_id'].forEach(key => {
        if (cleanData[key] === '') cleanData[key] = null;
        else if (cleanData[key] !== null) cleanData[key] = parseInt(cleanData[key]);
      });
      if (cleanData.remuneracion === '') cleanData.remuneracion = 0;

      if (isClientNew) {
        await axiosClient.post('/api/v1/clientes', cleanData);
      } else {
        await axiosClient.put(`/api/v1/clientes/${cliente.cuil}`, cleanData);
      }
      setCliente(cleanData); 
      
      // Auto-select Socio Originador if Empleador has one
      let defaultSocioId = '';
      if (cleanData.empleador_id) {
        const emp = empleadores.find(e => e.id === cleanData.empleador_id);
        if (emp && emp.socio_comercial_id) {
          defaultSocioId = String(emp.socio_comercial_id);
        }
      }
      
      setCreditoForm(prev => ({
        ...prev,
        socio_id: defaultSocioId,
        tasa_id: '' // reset selected tasa
      }));
      
      fetchBcraData(cleanData.cuil || cleanData.documento);
      setStep(3);
    } catch (error) {
      setClientFeedback({ type: 'error', message: error.response?.data?.detail || "Error al guardar el cliente." });
    } finally {
      setLoadingClient(false);
    }
  };

  const handleSimulateCredit = async (e) => {
    e.preventDefault();
    const selectedTasa = tasasYComisiones.find(t => t.id === parseInt(creditoForm.tasa_id));
    if (!selectedTasa) {
      alert("Debe seleccionar una tasa.");
      return;
    }
    setLoadingSimulation(true);
    try {
      const g1 = parseFloat(selectedTasa.gasto_1_porcentaje || 0);
      const g2 = parseFloat(selectedTasa.gasto_2_porcentaje || 0);
      const capitalNeto = parseFloat(creditoForm.capital_neto);
      
      if (1 - g1 - g2 <= 0) {
        throw new Error("Los gastos superan o igualan el 100% del capital. Ajuste la tasa seleccionada.");
      }
      
      const capitalBruto = capitalNeto / (1 - g1 - g2);
      setComputedCapitalBruto(capitalBruto);

      const params = new URLSearchParams({
        credito_id: 0,
        capital: capitalBruto,
        tna_c_iva: selectedTasa.tna_c_iva,
        plazo: selectedTasa.plazo,
        fecha_emision: creditoForm.fecha_emision
      });
      const res = await axiosClient.get(`/api/v1/creditos/simular-cuotas?${params.toString()}`);
      setSimulation(res.data);
      
      const newTransfers = [];
      newTransfers.push({
        cbu: cliente.cbu || '',
        cuit: cliente.cuil,
        razon_social: `${cliente.nombre} ${cliente.apellido}`,
        monto: capitalNeto
      });

      if (g1 > 0 && selectedTasa.gasto_1_socio_id) {
        const socio1 = socios.find(s => s.id === selectedTasa.gasto_1_socio_id);
        if (socio1) {
          newTransfers.push({
            cbu: socio1.cbu || '',
            cuit: socio1.cuit,
            razon_social: socio1.razon_social,
            monto: capitalBruto * g1
          });
        }
      }

      if (g2 > 0 && selectedTasa.gasto_2_socio_id) {
        const socio2 = socios.find(s => s.id === selectedTasa.gasto_2_socio_id);
        if (socio2) {
          newTransfers.push({
            cbu: socio2.cbu || '',
            cuit: socio2.cuit,
            razon_social: socio2.razon_social,
            monto: capitalBruto * g2
          });
        }
      }
      
      setTransfers(newTransfers);
      setStep(4);
    } catch (error) {
      alert("Error al simular crédito: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoadingSimulation(false);
    }
  };

  const handlePreviewLegajo = async () => {
    const selectedTasa = tasasYComisiones.find(t => t.id == creditoForm.tasa_id);
    if (!selectedTasa) return;

    setLoadingPreview(true);
    try {
      const payload = {
        cliente_cuil: cliente.cuil,
        capital: computedCapitalBruto,
        tna_c_iva: parseFloat(selectedTasa.tna_c_iva),
        plazo: selectedTasa.plazo,
        tipo_credito: creditoForm.tipo,
        socio_originador_id: creditoForm.socio_id ? parseInt(creditoForm.socio_id) : null,
        comision_id: selectedTasa.comision_id || null,
        fecha_emision: creditoForm.fecha_emision,
        id_externo: creditoForm.id_externo || null,
        transferencias: transfers
      };

      const res = await axiosClient.post('/api/v1/creditos/originacion/preview_legajo', payload, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Preview_Legajo_${cliente.cuil}.pdf`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      alert("Error al generar previsualización.");
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleConfirmCredit = async () => {
    const selectedTasa = tasasYComisiones.find(t => t.id === parseInt(creditoForm.tasa_id));
    if (!selectedTasa) return;

    const currentTotal = transfers.reduce((sum, t) => sum + parseFloat(t.monto || 0), 0);
    
    if (Math.abs(computedCapitalBruto - currentTotal) > 0.05) {
      alert("La suma de las transferencias debe ser igual al capital bruto a otorgar.");
      return;
    }

    setLoadingCredit(true);
    try {
      const payload = {
        cliente_cuil: cliente.cuil,
        capital: computedCapitalBruto,
        tna_c_iva: parseFloat(selectedTasa.tna_c_iva),
        plazo: selectedTasa.plazo,
        tipo_credito: creditoForm.tipo,
        socio_originador_id: creditoForm.socio_id ? parseInt(creditoForm.socio_id) : null,
        comision_id: selectedTasa.comision_id || null,
        fecha_emision: creditoForm.fecha_emision,
        id_externo: creditoForm.id_externo || null,
        transferencias: transfers
      };

      const res = await axiosClient.post('/api/v1/creditos/originacion', payload);
      alert(`Crédito originado con éxito.`);
      
      setCcModalData({ cuil: cliente.cuil, clientName: `${cliente.nombre} ${cliente.apellido}`, creditoId: res.data.credito_id });

      setStep(1);
      setCliente(null);
      setSearchCuil('');
      setCreditoForm({ capital_neto: '', tasa_id: '', tipo: 'SISTEMA FRANCES', socio_id: '', fecha_emision: new Date().toISOString().split('T')[0], id_externo: '' });
      setComputedCapitalBruto(0);
      setSimulation(null);
      setTransfers([]);
    } catch (error) {
      alert("Error al originar crédito: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoadingCredit(false);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Originación de Crédito</h2>
        <p>Busque un cliente, confirme o actualice sus datos y proceda a dar de alta un nuevo crédito.</p>
      </header>

      <div className="content-grid" style={{ gridTemplateColumns: '1fr' }}>
        
        {step === 1 && (
          <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '12px', fontFamily: 'var(--font-heading)', fontSize: '16px' }}>Paso 1: Buscar Cliente</h3>
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
              <div className="form-group" style={{ flexGrow: 1, maxWidth: '300px', marginBottom: 0 }}>
                <label>CUIL o Documento</label>
                <input type="text" value={searchCuil} onChange={(e) => setSearchCuil(e.target.value)} placeholder="Ingrese DNI o CUIL" required />
              </div>
              <button type="submit" className="btn-primary" disabled={loadingSearch} style={{ height: '42px', width: 'auto' }}>
                {loadingSearch ? "Buscando..." : "🔍 Buscar"}
              </button>
            </form>
          </div>
        )}

        {step === 2 && (
          <div className="glass-panel fade-in" style={{ padding: '20px', marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '16px', margin: 0 }}>
                Paso 2: {isClientNew ? "Alta de Nuevo Cliente" : `Actualización Obligatoria: ${cliente?.nombre} ${cliente?.apellido}`}
              </h3>
              <button className="btn-secondary" onClick={() => setStep(1)}>Volver a la búsqueda</button>
            </div>
            {isClientNew && (
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.05)', borderLeft: '4px solid var(--accent-secondary)', marginBottom: '20px', fontSize: '14px' }}>
                No se encontró ningún cliente con ese documento/CUIL. Por favor, complete sus datos para darlo de alta y continuar.
              </div>
            )}
            {!isClientNew && (
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.05)', borderLeft: '4px solid var(--accent-secondary)', marginBottom: '20px', fontSize: '14px' }}>
                Verifique y actualice los datos del cliente si es necesario. Debe guardar los cambios para proceder al paso 3.
              </div>
            )}
            <ClientForm 
              initialData={cliente} 
              onSubmit={handleClientSubmit} 
              loading={loadingClient} 
              feedback={clientFeedback}
              buttonText={isClientNew ? "Crear Cliente y Continuar" : "Actualizar Datos y Continuar"}
            />
          </div>
        )}

        {step === 3 && cliente && (
          <div className="form-container glass-panel fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '16px', margin: 0 }}>
                Paso 3: Condiciones del Crédito para {cliente.nombre} {cliente.apellido}
              </h3>
              <button className="btn-secondary" onClick={() => setStep(2)}>Volver a los datos</button>
            </div>
            
            {/* BCRA Block */}
            <div style={{ marginBottom: '24px', padding: '16px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <h4 style={{ margin: '0 0 12px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                🏦 Situación BCRA (Central de Deudores)
              </h4>
              {loadingBcra ? (
                <div style={{ fontSize: '14px', color: 'var(--text-color)' }}>Consultando situación crediticia... ⏳</div>
              ) : bcraData ? (
                <div>
                  <div style={{ display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                    <span style={{ 
                      padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold',
                      background: bcraData.Estado === 'Sin Deudas' || bcraData.Estado === 'Sin Deudas / Vacio' ? 'rgba(0, 200, 83, 0.2)' : 'rgba(255, 61, 0, 0.2)',
                      color: bcraData.Estado === 'Sin Deudas' || bcraData.Estado === 'Sin Deudas / Vacio' ? '#00e676' : '#ff5252' 
                    }}>
                      {bcraData.Estado}
                    </span>
                    {bcraData.Datos_API?.results?.denominacion && (
                      <span style={{ fontSize: '13px', alignSelf: 'center' }}>
                        Titular: <strong>{bcraData.Datos_API.results.denominacion}</strong>
                      </span>
                    )}
                  </div>
                  
                  {bcraData.Datos_API?.results?.periodos && bcraData.Datos_API.results.periodos.length > 0 && (
                    <div className="table-responsive" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                      <table className="data-table" style={{ fontSize: '12px' }}>
                        <thead>
                          <tr>
                            <th>Período</th>
                            <th>Entidad</th>
                            <th>Situación</th>
                            <th>Monto</th>
                            <th>Días Atraso</th>
                          </tr>
                        </thead>
                        <tbody>
                          {bcraData.Datos_API.results.periodos.flatMap(p => 
                            p.entidades.map((ent, idx) => (
                              <tr key={`${p.periodo}-${idx}`}>
                                <td>{p.periodo}</td>
                                <td>{ent.entidad}</td>
                                <td>
                                  <span style={{
                                    padding: '2px 6px', borderRadius: '4px',
                                    background: ent.situacion === 1 ? 'rgba(0, 200, 83, 0.2)' : 'rgba(255, 61, 0, 0.2)',
                                    color: ent.situacion === 1 ? '#00e676' : '#ff5252'
                                  }}>
                                    {ent.situacion}
                                  </span>
                                </td>
                                <td>{formatCurrency(ent.monto * 1000)}</td>
                                <td>{ent.diasAtrasoPago}</td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ fontSize: '14px', color: 'var(--text-color)' }}>No se pudo obtener información del BCRA.</div>
              )}
            </div>

            <form onSubmit={handleSimulateCredit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Capital Neto (Mano) *</label>
                  <CurrencyInput 
                    value={creditoForm.capital_neto} 
                    onChange={(val) => setCreditoForm({...creditoForm, capital_neto: val})} 
                    required={true} 
                  />
                </div>
                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                  <label>Condiciones (Plazo y TNA) *</label>
                  <select value={creditoForm.tasa_id} onChange={(e) => setCreditoForm({...creditoForm, tasa_id: e.target.value})} required>
                    <option value="">Seleccione una opción...</option>
                    {tasasYComisiones
                      .filter(t => !creditoForm.socio_id || t.socio_originador_id == creditoForm.socio_id)
                      .map(t => (
                        <option key={t.id} value={t.id}>{t.plazo} meses - TNA: {(t.tna_c_iva * 100).toFixed(2)}%</option>
                      ))}
                  </select>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Tipo de Crédito *</label>
                  <select value={creditoForm.tipo} onChange={(e) => setCreditoForm({...creditoForm, tipo: e.target.value})} required>
                    <option value="SISTEMA FRANCES">Sistema Francés</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Socio Originador</label>
                  <select value={creditoForm.socio_id} onChange={(e) => setCreditoForm({...creditoForm, socio_id: e.target.value})}>
                    <option value="">(Ninguno / Directo)</option>
                    {socios.map(s => <option key={s.id} value={s.id}>{s.razon_social}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Fecha de Emisión</label>
                  <input type="date" value={creditoForm.fecha_emision} onChange={(e) => setCreditoForm({...creditoForm, fecha_emision: e.target.value})} required />
                </div>
                <div className="form-group">
                  <label>ID Externo</label>
                  <input type="text" value={creditoForm.id_externo} onChange={(e) => setCreditoForm({...creditoForm, id_externo: e.target.value})} placeholder="Opcional" />
                </div>
              </div>
              <div className="form-actions" style={{ marginTop: '24px' }}>
                <button type="submit" className="btn-primary" disabled={loadingSimulation} style={{ width: '100%', fontSize: '16px', padding: '14px' }}>
                  {loadingSimulation ? "Simulando..." : "Simular Crédito"}
                </button>
              </div>
            </form>
          </div>
        )}

        {step === 4 && simulation && (
          <div className="form-container glass-panel fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '16px', margin: 0 }}>
                Paso 4: Simulación y Transferencias
              </h3>
              <button className="btn-secondary" onClick={() => setStep(3)}>Volver a condiciones</button>
            </div>
            
            <div className="table-responsive" style={{ marginBottom: '24px', maxHeight: '300px', overflowY: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Cuota</th>
                    <th>Vencimiento</th>
                    <th>Capital</th>
                    <th>Interés</th>
                    <th>IVA</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {simulation.map((c, idx) => {
                    const totalCuota = parseFloat(c.capital) + parseFloat(c.interes) + parseFloat(c.iva);
                    return (
                      <tr key={idx}>
                        <td>{c.nro_cuota}</td>
                        <td>{c.fecha_vencimiento}</td>
                        <td>{formatCurrency(c.capital)}</td>
                        <td>{formatCurrency(c.interes)}</td>
                        <td>{formatCurrency(c.iva)}</td>
                        <td><strong>{formatCurrency(totalCuota)}</strong></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <TransfersForm 
              transfers={transfers}
              onChange={setTransfers}
              totalRequired={computedCapitalBruto}
            />

            <div className="form-actions" style={{ marginTop: '32px', display: 'flex', gap: '15px' }}>
              <button 
                type="button" 
                className="btn-secondary" 
                onClick={handlePreviewLegajo}
                disabled={loadingPreview || loadingCredit || Math.abs(computedCapitalBruto - transfers.reduce((sum, t) => sum + parseFloat(t.monto || 0), 0)) > 0.05} 
                style={{ flex: 1, fontSize: '16px', padding: '14px', backgroundColor: 'var(--border-color)', color: 'var(--text-color)' }}
              >
                {loadingPreview ? "Generando..." : "Descargar Legajo (Borrador)"}
              </button>
              <button 
                type="button" 
                className="btn-primary" 
                onClick={handleConfirmCredit}
                disabled={loadingCredit || loadingPreview || Math.abs(computedCapitalBruto - transfers.reduce((sum, t) => sum + parseFloat(t.monto || 0), 0)) > 0.05} 
                style={{ flex: 1, fontSize: '16px', padding: '14px' }}
              >
                {loadingCredit ? "Procesando Originación..." : "Confirmar y Originar"}
              </button>
            </div>
          </div>
        )}
      </div>

      {ccModalData && (
        <ClientCCModal 
          cuil={ccModalData.cuil} 
          clientName={ccModalData.clientName} 
          initialFilterCredito={ccModalData.creditoId}
          onClose={() => setCcModalData(null)} 
        />
      )}
    </section>
  );
};

export default CreditOriginationPage;
