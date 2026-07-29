import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import axiosClient from '../api/axiosClient';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Search, User, Briefcase, MapPin, Phone, Mail, FileText, CreditCard } from 'lucide-react';

const formatCurrency = (value) => {
  if (value === null || value === undefined) return "$ 0";
  return new Intl.NumberFormat('es-AR', { 
    style: 'currency', 
    currency: 'ARS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const CHART_COLORS = ['#6366f1', '#14b8a6', '#f59e0b', '#ec4899', '#8b5cf6', '#10b981', '#f43f5e', '#3b82f6'];

const DashboardClientesPage = () => {
  const [searchParams] = useSearchParams();
  const initialCuil = searchParams.get('cuil');

  // State for search and clients list
  const [allClients, setAllClients] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const searchRef = useRef(null);

  // State for selected client data
  const [selectedCuil, setSelectedCuil] = useState(initialCuil || null);
  const [clientData, setClientData] = useState(null);
  const [ccData, setCcData] = useState([]);
  const [loadingClient, setLoadingClient] = useState(false);
  const [clientError, setClientError] = useState(null);

  // Dashboard UI state
  const [activeTab, setActiveTab] = useState('genericos');
  const [selectedCreditos, setSelectedCreditos] = useState([]);

  // 1. Fetch all clients on mount for the search bar
  useEffect(() => {
    const fetchAllClients = async () => {
      setIsSearching(true);
      try {
        const res = await axiosClient.get('/api/v1/clientes');
        setAllClients(res.data);
      } catch (err) {
        console.error("Error cargando lista de clientes:", err);
      } finally {
        setIsSearching(false);
      }
    };
    fetchAllClients();
  }, []);

  // 2. Fetch specific client data when selected
  useEffect(() => {
    if (!selectedCuil || allClients.length === 0) return;

    const fetchClientDashboardData = async () => {
      setLoadingClient(true);
      setClientError(null);
      try {
        const ccRes = await axiosClient.get(`/api/v1/clientes/${selectedCuil}/cuenta_corriente`);
        const foundClient = allClients.find(c => c.CUIL === selectedCuil);
        setClientData(foundClient);
        setCcData(ccRes.data);
        setSelectedCreditos([]); // Reset credit filters on new client
      } catch (err) {
        console.error("Error cargando datos del cliente:", err);
        setClientError("Ocurrió un error al cargar la información del cliente seleccionado.");
      } finally {
        setLoadingClient(false);
      }
    };
    fetchClientDashboardData();
  }, [selectedCuil, allClients]);

  // Handle outside click for search dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Filter clients based on search term
  const filteredSearchClients = useMemo(() => {
    if (!searchTerm) return [];
    const term = searchTerm.toLowerCase();
    return allClients.filter(c => {
      const fullName = (c["Apellido y Nombre"] || "").toLowerCase();
      const matchName = fullName.includes(term) || (c.Nombre || "").toLowerCase().includes(term) || (c.Apellido || "").toLowerCase().includes(term);
      const matchCuil = (c.CUIL || "").includes(term);
      const matchDni = (c.Documento || "").includes(term);
      return matchName || matchCuil || matchDni;
    }).slice(0, 10); // Limit to 10 results
  }, [searchTerm, allClients]);

  const handleSelectClient = (cuil) => {
    setSelectedCuil(cuil);
    setSearchTerm('');
    setShowDropdown(false);
    setActiveTab('genericos');
  };

  // --- TAB 2: KPIs CRÉDITOS CALCULATIONS ---
  const uniqueCreditos = useMemo(() => {
    const map = new Map();
    ccData.forEach(quota => {
      if (quota.credito_id && !map.has(quota.credito_id)) {
        map.set(quota.credito_id, {
          tipo: quota.tipo_credito || 'Desconocido',
          estado: quota.estado_credito || 'Desconocido'
        });
      }
    });
    return Array.from(map.entries()).map(([id, info]) => ({ id, tipo: info.tipo, estado: info.estado }));
  }, [ccData]);

  const filteredCcData = useMemo(() => {
    if (selectedCreditos.length === 0) return ccData;
    const selectedIds = selectedCreditos.map(Number);
    return ccData.filter(quota => selectedIds.includes(quota.credito_id));
  }, [ccData, selectedCreditos]);

  const kpisCreditos = useMemo(() => {
    let montoTotal = 0;
    let saldoPendiente = 0;
    let cuotasCanceladas = 0;
    let cuotasEnMora = 0;
    let cuotasPendientes = 0;

    let capitalAdeudado = 0;
    let interesAdeudado = 0;
    let ivaAdeudado = 0;

    const creditosFirstCuota = {};

    let maxDiasMora = 0;
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    filteredCcData.forEach(quota => {
      const estado = (quota.estado || '').toUpperCase();

      if (estado !== 'NO COMPRADA') {
        if (!creditosFirstCuota[quota.credito_id] || (quota.nro_cuota && quota.nro_cuota < creditosFirstCuota[quota.credito_id].nro)) {
          creditosFirstCuota[quota.credito_id] = { nro: quota.nro_cuota || 1, val: parseFloat(quota.total_esperado || 0) };
        }
      }

      montoTotal += parseFloat(quota.total_esperado || quota.capital || 0);
      saldoPendiente += parseFloat(quota.saldo_pendiente || 0);

      if (estado === 'CANCELADA') cuotasCanceladas++;
      else if (estado === 'MOROSA') cuotasEnMora++;
      else if (estado === 'PENDIENTE') cuotasPendientes++;

      if (estado !== 'NO COMPRADA' && estado !== 'CANCELADA') {
        let netCapital = parseFloat(quota.capital || 0);
        let netInteres = parseFloat(quota.interes || 0);
        let netIva = parseFloat(quota.iva || 0);
        
        if (quota.detalle_cobranzas && quota.detalle_cobranzas.length > 0) {
          quota.detalle_cobranzas.forEach(cob => {
            netCapital -= parseFloat(cob.capital || 0);
            netInteres -= parseFloat(cob.interes || 0);
            netIva -= parseFloat(cob.iva || 0);
          });
        }
        
        capitalAdeudado += Math.max(0, netCapital);
        interesAdeudado += Math.max(0, netInteres);
        ivaAdeudado += Math.max(0, netIva);

        if (quota.vencimiento && quota.vencimiento !== '-') {
          const parts = quota.vencimiento.split('/');
          if (parts.length === 3) {
            const vencDate = new Date(parts[2], parts[1] - 1, parts[0]);
            const diffTime = today.getTime() - vencDate.getTime();
            const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
            if (diffDays > maxDiasMora) {
              maxDiasMora = diffDays;
            }
          }
        }
      }
    });

    const valorCuotaTotal = Object.values(creditosFirstCuota).reduce((acc, curr) => acc + curr.val, 0);

    return { 
      totalOps: selectedCreditos.length === 0 ? uniqueCreditos.length : selectedCreditos.length,
      montoTotal, 
      saldoPendiente,
      cuotasCanceladas,
      cuotasEnMora,
      cuotasPendientes,
      totalCuotas: filteredCcData.length,
      capitalAdeudado,
      interesAdeudado,
      ivaAdeudado,
      valorCuotaTotal,
      maxDiasMora
    };
  }, [filteredCcData, selectedCreditos, uniqueCreditos]);

  const chartDataEstadoCuotas = useMemo(() => {
    return [
      { name: 'Canceladas', value: kpisCreditos.cuotasCanceladas, fill: '#10b981' },
      { name: 'Pendientes', value: kpisCreditos.cuotasPendientes, fill: '#f59e0b' },
      { name: 'Morosas', value: kpisCreditos.cuotasEnMora, fill: '#ef4444' }
    ].filter(item => item.value > 0);
  }, [kpisCreditos]);

  return (
    <div className="page-container" style={{ animation: 'fadeIn 0.5s ease', display: 'flex', flexDirection: 'column' }}>
      
      {/* HEADER & SEARCH */}
      <header className="page-header" style={{ marginBottom: '30px', display: 'flex', flexWrap: 'wrap', gap: '20px', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Ficha del Cliente</h1>
          <p className="page-subtitle">Busca un cliente para ver su información detallada y estado crediticio</p>
        </div>

        <div className="search-container" ref={searchRef} style={{ position: 'relative', minWidth: '300px', flex: 1, maxWidth: '500px' }}>
          <div style={{ position: 'relative' }}>
            <Search style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} size={18} />
            <input 
              type="text" 
              placeholder="Buscar por DNI, CUIL, Nombre..." 
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setShowDropdown(true);
              }}
              onFocus={() => setShowDropdown(true)}
              style={{
                width: '100%',
                padding: '12px 12px 12px 40px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-panel)',
                color: 'var(--text-primary)',
                fontSize: '1rem',
                outline: 'none',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
              }}
            />
            {isSearching && <div className="loading-spinner" style={{ position: 'absolute', right: '12px', top: '25%', width: '16px', height: '16px' }}></div>}
          </div>

          {/* Search Dropdown */}
          {showDropdown && searchTerm.length > 1 && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, marginTop: '8px',
              background: 'var(--surface-color)', border: '1px solid var(--border-color)',
              borderRadius: '8px', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', zIndex: 50,
              maxHeight: '300px', overflowY: 'auto'
            }}>
              {filteredSearchClients.length === 0 ? (
                <div style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>No se encontraron resultados</div>
              ) : (
                filteredSearchClients.map(c => (
                  <div 
                    key={c.CUIL}
                    onClick={() => handleSelectClient(c.CUIL)}
                    style={{
                      padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)',
                      display: 'flex', flexDirection: 'column', gap: '4px'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <div style={{ fontWeight: '600' }}>{c.Apellido}, {c.Nombre}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>CUIL: {c.CUIL} | DNI: {c.Documento}</div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </header>

      {/* CONTENT AREA */}
      {!selectedCuil ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', padding: '40px' }}>
          <Search size={64} style={{ opacity: 0.2, marginBottom: '20px' }} />
          <h2>Ningún cliente seleccionado</h2>
          <p>Utiliza el buscador de arriba para encontrar y analizar a un cliente.</p>
        </div>
      ) : loadingClient ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '100px 0' }}>
          <div className="loading-spinner"></div>
          <span style={{ marginLeft: '10px' }}>Cargando ficha del cliente...</span>
        </div>
      ) : clientError ? (
        <div className="alert error">{clientError}</div>
      ) : clientData ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Client Header Card */}
          <div className="glass-panel" style={{ padding: '24px', borderRadius: '12px', display: 'flex', flexWrap: 'wrap', gap: '24px', alignItems: 'center', borderLeft: `6px solid ${clientData.Estado === 'ACTIVO' ? '#10b981' : '#ef4444'}` }}>
            <div style={{ width: '80px', height: '80px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <User size={40} color="var(--text-secondary)" />
            </div>
            <div style={{ flex: 1 }}>
              <h2 style={{ fontSize: '2rem', margin: '0 0 8px 0' }}>{clientData.Apellido}, {clientData.Nombre}</h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', color: 'var(--text-secondary)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><FileText size={16} /> CUIL: {clientData.CUIL}</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><CreditCard size={16} /> DNI: {clientData.Documento}</span>
              </div>
            </div>
            <div>
              <span style={{ 
                padding: '8px 16px', borderRadius: '20px', fontWeight: 'bold', letterSpacing: '1px',
                background: clientData.Estado === 'ACTIVO' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                color: clientData.Estado === 'ACTIVO' ? '#10b981' : '#ef4444'
              }}>
                {clientData.Estado}
              </span>
            </div>
          </div>

          {/* Tabs Menu */}
          <div style={{ display: 'flex', gap: '15px', marginTop: '10px' }}>
            <button 
              onClick={() => setActiveTab('genericos')}
              style={{ 
                padding: '10px 20px', borderRadius: '8px', border: 'none', cursor: 'pointer', fontWeight: '600', transition: 'all 0.2s',
                background: activeTab === 'genericos' ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)',
                color: activeTab === 'genericos' ? 'white' : 'var(--text-secondary)'
              }}
            >
              Datos del Cliente
            </button>
            <button 
              onClick={() => setActiveTab('creditos')}
              style={{ 
                padding: '10px 20px', borderRadius: '8px', border: 'none', cursor: 'pointer', fontWeight: '600', transition: 'all 0.2s',
                background: activeTab === 'creditos' ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)',
                color: activeTab === 'creditos' ? 'white' : 'var(--text-secondary)'
              }}
            >
              Créditos y Estado
            </button>
          </div>

          {/* TAB 1: DATOS GENERICOS */}
          {activeTab === 'genericos' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', animation: 'fadeIn 0.3s' }}>
              
              <div className="glass-panel" style={{ padding: '24px', borderRadius: '12px' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--accent-primary)', marginBottom: '20px' }}>
                  <User size={20} /> Información Personal
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-secondary)' }}>F. Nacimiento:</span> <span>{clientData["Fecha Nacimiento"] || '-'}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-secondary)' }}>Estado Civil:</span> <span>{clientData["Estado Civil"] || '-'}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-secondary)' }}>Género:</span> <span>{clientData.Sexo || '-'}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-secondary)' }}>Nacionalidad:</span> <span>{clientData.Nacionalidad || '-'}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-secondary)' }}>PEP:</span> <span>{clientData.PEP || 'No'}</span></div>
                </div>
              </div>

              <div className="glass-panel" style={{ padding: '24px', borderRadius: '12px' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#8b5cf6', marginBottom: '20px' }}>
                  <MapPin size={20} /> Contacto y Domicilio
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                    <Mail size={16} style={{ color: 'var(--text-secondary)', marginTop: '2px' }} />
                    <span style={{ wordBreak: 'break-all' }}>{clientData.Mail !== '-' ? clientData.Mail : 'Sin email registrado'}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                    <Phone size={16} style={{ color: 'var(--text-secondary)', marginTop: '2px' }} />
                    <span>{clientData["Teléfono"] || '-'}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                    <MapPin size={16} style={{ color: 'var(--text-secondary)', marginTop: '2px', flexShrink: 0 }} />
                    <div>
                      <div>{clientData.Calle !== '-' ? clientData.Calle : 'Sin calle'} {clientData["Calle Nro"] !== '-' ? clientData["Calle Nro"] : ''} {clientData.Piso !== '-' ? `Piso ${clientData.Piso}` : ''} {clientData.Depto !== '-' ? `Dpto ${clientData.Depto}` : ''}</div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{clientData.Localidad !== '-' ? clientData.Localidad : 'Localidad Desconocida'}, {clientData.Provincia !== '-' ? clientData.Provincia : 'Provincia Desconocida'} ({clientData["Código Postal"] !== '-' ? clientData["Código Postal"] : 'CP'})</div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="glass-panel" style={{ padding: '24px', borderRadius: '12px' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#f59e0b', marginBottom: '20px' }}>
                  <Briefcase size={20} /> Datos Laborales
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-secondary)' }}>Empleador:</span> <span style={{ textAlign: 'right' }}>{clientData.Empleador || '-'}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-secondary)' }}>Cargo:</span> <span style={{ textAlign: 'right' }}>{clientData.Cargo || '-'}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--text-secondary)' }}>Fecha Ingreso:</span> <span>{clientData["Fecha de Ingreso"] || '-'}</span></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                    <span style={{ color: 'var(--text-secondary)', fontWeight: 'bold' }}>Remuneración:</span> 
                    <span style={{ fontWeight: 'bold', color: '#10b981' }}>{formatCurrency(clientData["Remuneración"])}</span>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* TAB 2: CREDITOS Y KPIs */}
          {activeTab === 'creditos' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', animation: 'fadeIn 0.3s' }}>
              
              {/* Filtro de Créditos */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px' }}>
                <label style={{ color: 'var(--text-secondary)', fontWeight: '500', display: 'block', marginBottom: '10px' }}>
                  Filtrar por Crédito (Múltiple):
                </label>
                {uniqueCreditos.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)' }}>El cliente no posee créditos registrados.</p>
                ) : (
                  <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
                    <select 
                      multiple
                      value={selectedCreditos}
                      onChange={(e) => {
                        const options = Array.from(e.target.options);
                        const selected = options.filter(o => o.selected).map(o => o.value);
                        setSelectedCreditos(selected);
                      }}
                      style={{ 
                        background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', 
                        padding: '10px', borderRadius: '8px', minHeight: '120px', flex: 1, minWidth: '200px' 
                      }}
                    >
                      {uniqueCreditos.map(cred => (
                        <option key={cred.id} value={cred.id}>Operación #{cred.id} - {cred.tipo} ({cred.estado})</option>
                      ))}
                    </select>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', justifyContent: 'center' }}>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '200px' }}>
                        Mantén presionado Ctrl (o Cmd) para seleccionar múltiples operaciones. Si no seleccionas ninguna, se mostrará el total de todas las operaciones.
                      </div>
                      <button 
                        onClick={() => setSelectedCreditos([])} 
                        className="btn-secondary" 
                        disabled={selectedCreditos.length === 0}
                      >
                        Ver todos
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* KPIs de Créditos Principales */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
                <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px', borderTop: '4px solid #3b82f6', textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px' }}>Operaciones Analizadas</div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{kpisCreditos.totalOps} <span style={{fontSize: '1rem', color: 'var(--text-muted)'}}>/ {uniqueCreditos.length}</span></div>
                </div>
                <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px', borderTop: '4px solid #14b8a6', textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px' }}>Total Esperado (Cap+Int)</div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{formatCurrency(kpisCreditos.montoTotal)}</div>
                </div>
                <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px', borderTop: '4px solid #ef4444', textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px' }}>Saldo Pendiente Total</div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold', color: kpisCreditos.saldoPendiente > 0 ? '#ef4444' : 'inherit' }}>
                    {formatCurrency(kpisCreditos.saldoPendiente)}
                  </div>
                </div>
                <div className="glass-panel" style={{ padding: '20px', borderRadius: '12px', borderTop: `4px solid ${kpisCreditos.maxDiasMora > 0 ? '#ef4444' : '#10b981'}`, textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '10px' }}>Días en Mora (Máx)</div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold', color: kpisCreditos.maxDiasMora > 0 ? '#ef4444' : '#10b981' }}>
                    {kpisCreditos.maxDiasMora}
                  </div>
                </div>
              </div>

              {/* KPIs de Créditos Desglose */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '20px' }}>
                <div className="glass-panel" style={{ padding: '15px', borderRadius: '12px', borderLeft: '3px solid #10b981' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>Capital Adeudado</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 'bold', marginTop: '5px' }}>{formatCurrency(kpisCreditos.capitalAdeudado)}</div>
                </div>
                <div className="glass-panel" style={{ padding: '15px', borderRadius: '12px', borderLeft: '3px solid #f59e0b' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>Interés Adeudado</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 'bold', marginTop: '5px' }}>{formatCurrency(kpisCreditos.interesAdeudado)}</div>
                </div>
                <div className="glass-panel" style={{ padding: '15px', borderRadius: '12px', borderLeft: '3px solid #8b5cf6' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>IVA Adeudado</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 'bold', marginTop: '5px' }}>{formatCurrency(kpisCreditos.ivaAdeudado)}</div>
                </div>
                <div className="glass-panel" style={{ padding: '15px', borderRadius: '12px', borderLeft: '3px solid #ec4899' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase' }}>Valor de Cuota (Suma)</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 'bold', marginTop: '5px', color: '#ec4899' }}>{formatCurrency(kpisCreditos.valorCuotaTotal)}</div>
                </div>
              </div>

              {/* Gráficos */}
              {kpisCreditos.totalCuotas > 0 && (
                <div className="glass-panel" style={{ padding: '24px', borderRadius: '12px' }}>
                  <h3 style={{ marginBottom: '20px', color: 'var(--text-secondary)' }}>Estado de Cuotas</h3>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '30px' }}>
                    
                    <div style={{ flex: '1 1 300px', height: '250px' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie 
                            data={chartDataEstadoCuotas} 
                            cx="50%" cy="50%" innerRadius={60} outerRadius={90} 
                            paddingAngle={5} dataKey="value"
                            label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                          >
                            {chartDataEstadoCuotas.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.fill} />
                            ))}
                          </Pie>
                          <Tooltip contentStyle={{ backgroundColor: 'var(--bg-panel)', borderColor: 'var(--border-color)', borderRadius: '8px' }} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>

                    <div style={{ flex: '1 1 300px', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '15px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#10b981' }}></span> Canceladas
                        </span>
                        <span style={{ fontWeight: 'bold' }}>{kpisCreditos.cuotasCanceladas} cuotas</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '10px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#f59e0b' }}></span> Pendientes
                        </span>
                        <span style={{ fontWeight: 'bold' }}>{kpisCreditos.cuotasPendientes} cuotas</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#ef4444' }}></span> En Mora
                        </span>
                        <span style={{ fontWeight: 'bold' }}>{kpisCreditos.cuotasEnMora} cuotas</span>
                      </div>
                    </div>

                  </div>
                </div>
              )}

            </div>
          )}

        </div>
      ) : null}
    </div>
  );
};

export default DashboardClientesPage;
