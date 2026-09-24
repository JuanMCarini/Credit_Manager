import React, { useState } from 'react';
import useAppStore from '../store/useAppStore';
import axiosClient from '../api/axiosClient';
import ExportExcelButton from '../components/ExportExcelButton';

const AuxiliaryTablesPage = () => {
  const { nacionalidades, provincias, empleadores, socios, operadores, tasasYComisiones, relaciones, comercializadores, bancos, cuentas, conceptos, clasificaciones, comisionesDeuda, factoresRiesgo, multiplicadoresRiesgo, reglasPerfilesTransaccionales, fetchAuxiliares } = useAppStore();

  const [activeTable, setActiveTable] = useState('socios');
  const [isCreating, setIsCreating] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [editFormData, setEditFormData] = useState({});
  const [feedback, setFeedback] = useState(null);
  const [columnFilters, setColumnFilters] = useState({});
  const [sortConfig, setSortConfig] = useState({ key: 'id', direction: 'desc' });

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  // Advance Adjustment State
  const [adjustingAdvance, setAdjustingAdvance] = useState(null);
  const [advanceAmount, setAdvanceAmount] = useState('');
  const [advanceDate, setAdvanceDate] = useState('');

  // Bulk Edit Factores State
  const [showBulkEditFactores, setShowBulkEditFactores] = useState(false);
  const [bulkFactoresData, setBulkFactoresData] = useState([]);
  const [bulkFactoresSaving, setBulkFactoresSaving] = useState(false);

  const relationMaps = {
    socio_comercial_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    socio_originador_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    socio_intermediario_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    gasto_1_socio_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    gasto_2_socio_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    socio_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    provincia_id: { options: provincias, valueKey: 'id', labelKey: 'nombre' },
    id_provincia: { options: provincias, valueKey: 'id', labelKey: 'nombre' },
    banco_id: { options: bancos, valueKey: 'id', labelKey: 'nombre_banco' },
    concepto_id: { options: conceptos, valueKey: 'id', labelKey: 'name' },
    clasificacion_id: { options: clasificaciones, valueKey: 'id', labelKey: 'name' },
    id_socio_comercial: { options: socios, valueKey: 'id', labelKey: 'razon_social' }
  };

  const percentFields = [
    'colocacion_originador', 'colocacion_intermediario',
    'cobranza_originador', 'cobranza_intermediario',
    'colocacion_propia', 'tna_c_iva', 'tna_s_iva', 'alicuota_iva',
    'gasto_1_porcentaje', 'gasto_2_porcentaje', 'porcentaje_sellado', 'porcentaje', 'cupo'
  ];

  const tablesMap = {
    nacionalidades: { name: 'Nacionalidades', data: nacionalidades, endpoint: 'nacionalidades', schema: ['id', 'nombre', 'lista_gafi'] },
    provincias: { name: 'Provincias', data: provincias, endpoint: 'provincias', schema: ['id', 'nombre'] },
    operadores: { name: 'Operadores de Cheques', data: operadores, endpoint: 'operadores', basePath: '/api/cheques', idField: 'cuit', schema: ['cuit', 'razon_social', 'calificacion', 'telefono', 'email'] },
    empleadores: { name: 'Empleadores', data: empleadores, endpoint: 'empleadores', schema: ['id', 'cuit', 'razon_social', 'es_pasivo', 'domicilio_calle', 'domicilio_nro', 'domicilio_piso', 'domicilio_depto', 'id_provincia', 'id_codigo_postal', 'localidad', 'telefono', 'socio_comercial_id'] },
    socios: { name: 'Socios Comerciales', data: socios, endpoint: 'socios', schema: ['id', 'razon_social', 'cuit', 'domicilio_legal', 'contacto_nombre', 'mail', 'telefono', 'dia_corte', 'cbu', 'nro_cuenta_bancaria', 'nombre_banco', 'anticipo_vigente', 'codigo_descuento'] },
    tasasYComisiones: { name: 'Tasas y Comisiones', data: tasasYComisiones, endpoint: 'tasas_y_comisiones', schema: ['id', 'fecha', 'estado', 'socio_originador_id', 'socio_intermediario_id', 'colocacion_originador', 'colocacion_intermediario', 'cobranza_originador', 'cobranza_intermediario', 'colocacion_propia', 'gasto_1_porcentaje', 'gasto_1_socio_id', 'gasto_2_porcentaje', 'gasto_2_socio_id', 'porcentaje_sellado', 'plazo', 'tna_c_iva'] },
    relaciones: { name: 'Relaciones Mapeadas', data: relaciones, endpoint: 'relaciones', schema: ['id', 'socio_id', 'tabla', 'id_local', 'id_foraneo'] },
    comercializadores: { name: 'Comercializadores', data: comercializadores, endpoint: 'comercializadores', schema: ['id', 'nombre'] },
    bancos: { name: 'Bancos', data: bancos, endpoint: 'bancos', basePath: '/api/finanzas', schema: ['id', 'nombre_banco', 'parser_type'] },
    cuentas: { name: 'Cuentas Bancarias', data: cuentas, endpoint: 'cuentas', basePath: '/api/finanzas', schema: ['id', 'nombre', 'banco_id', 'nro', 'cbu', 'alias', 'tipo_cuenta', 'moneda'] },
    conceptos: { name: 'Conceptos', data: conceptos, endpoint: 'conceptos', basePath: '/api/finanzas', schema: ['id', 'name', 'clasificacion_id', 'tipo_movimiento', 'descripcion'] },
    clasificaciones: { name: 'Clasificaciones de Conceptos', data: clasificaciones, endpoint: 'clasificaciones', basePath: '/api/finanzas', schema: ['id', 'name', 'descripcion'] },
    comisionesDeuda: { name: 'Comisiones Deuda', data: comisionesDeuda, endpoint: 'comisiones_deuda', schema: ['id', 'fecha', 'id_socio_comercial', 'porcentaje'] },
    factoresRiesgo: { name: 'Factores de Riesgo', data: factoresRiesgo, endpoint: 'factores_riesgo', schema: ['id', 'codigo', 'detalle', 'peso'] },
    multiplicadoresRiesgo: { name: 'Multiplicadores de Riesgo', data: multiplicadoresRiesgo, endpoint: 'multiplicadores_riesgo', schema: ['id', 'id_riesgo', 'codigo', 'detalle', 'multiplicador', 'variable'] },
    reglasPerfilesTransaccionales: { name: 'Perfiles Transaccionales', data: reglasPerfilesTransaccionales, endpoint: 'reglas_perfiles_transaccionales', schema: ['id', 'id_socio_comercial', 'cupo', 'sueldo_tipo', 'asignacion_familiar', 'horas_extras', 'vacaciones', 'otros', 'descuentos_voluntarios'] }
  };

  const currentTableConfig = tablesMap[activeTable];
  const columns = currentTableConfig.schema || [];
  const tableData = currentTableConfig.data || [];

  const handleDelete = async (id) => {
    if (!window.confirm("¿Estás seguro de que deseas eliminar este registro?")) return;

    setFeedback(null);
    try {
      const basePath = currentTableConfig.basePath || '/api/v1/auxiliares';
      await axiosClient.delete(`${basePath}/${currentTableConfig.endpoint}/${id}`);
      setFeedback({ type: 'success', message: 'Registro eliminado exitosamente.' });
      await fetchAuxiliares();
    } catch (error) {
      setFeedback({ type: 'error', message: error.response?.data?.detail || "Error al eliminar el registro." });
    }
  };

  const openEditModal = (record = null) => {
    if (record) {
      setIsCreating(false);
      setEditingRecord(record);

      const editData = { ...record };
      percentFields.forEach(f => {
        if (editData[f] !== null && editData[f] !== undefined) {
          editData[f] = parseFloat((editData[f] * 100).toFixed(4));
        }
      });
      setEditFormData(editData);
    } else {
      setIsCreating(true);
      setEditingRecord(null);
      const emptyForm = {};
      columns.forEach(c => {
        if (c === 'estado' && currentTableConfig.endpoint === 'tasas_y_comisiones') {
          emptyForm[c] = 'ACTIVA';
        } else if (c === 'estado') {
          emptyForm[c] = 'ACTIVO';
        } else if (c === 'es_pasivo' || c === 'asignacion_familiar') {
          emptyForm[c] = false;
        } else if (['horas_extras', 'vacaciones', 'otros', 'descuentos_voluntarios'].includes(c)) {
          emptyForm[c] = true;
        } else if (c === 'fecha') {
          emptyForm[c] = new Date().toISOString().substring(0, 10);
        } else if (c === 'moneda') {
          emptyForm[c] = 'Pesos Argentinos $';
        } else if (c === 'anticipo_vigente') {
          emptyForm[c] = 0;
        } else {
          emptyForm[c] = '';
        }
      });
      setEditFormData(emptyForm);
    }
  };

  const openDuplicateModal = (record) => {
    setIsCreating(true);
    setEditingRecord(null);

    const duplicateData = { ...record };
    delete duplicateData.id; // Remove ID to create a new record
    if (currentTableConfig.schema.includes('fecha')) {
      duplicateData.fecha = new Date().toISOString().split('T')[0]; // Set date to today
    }

    percentFields.forEach(f => {
      if (duplicateData[f] !== null && duplicateData[f] !== undefined) {
        duplicateData[f] = parseFloat((duplicateData[f] * 100).toFixed(4));
      }
    });
    setEditFormData(duplicateData);
  };


  const closeEditModal = () => {
    setIsCreating(false);
    setEditingRecord(null);
    setEditFormData({});
    setFeedback(null);
  };

  const handleEditChange = (key, value) => {
    setEditFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setFeedback(null);
    try {
      // Clean up empty string values to null for integers
      const cleanedData = { ...editFormData };
      for (const key in cleanedData) {
        if (cleanedData[key] === '') {
          cleanedData[key] = null;
        } else if (relationMaps[key]) {
          cleanedData[key] = parseInt(cleanedData[key], 10);
        } else if (percentFields.includes(key) && cleanedData[key] !== null) {
          cleanedData[key] = parseFloat(cleanedData[key]) / 100.0;
        }
      }

      // Remove read-only or computed fields before sending to the backend
      if (currentTableConfig.endpoint === 'socios') {
        delete cleanedData.anticipo_vigente;
      }

      if (isCreating) {
        const basePath = currentTableConfig.basePath || '/api/v1/auxiliares';
        await axiosClient.post(`${basePath}/${currentTableConfig.endpoint}`, cleanedData);
        setFeedback({ type: 'success', message: 'Registro creado exitosamente.' });
      } else {
        const basePath = currentTableConfig.basePath || '/api/v1/auxiliares';
        const idField = currentTableConfig.idField || 'id';
        await axiosClient.put(`${basePath}/${currentTableConfig.endpoint}/${editingRecord[idField]}`, cleanedData);
        setFeedback({ type: 'success', message: 'Registro actualizado exitosamente.' });
      }
      await fetchAuxiliares();
      closeEditModal();
    } catch (error) {
      setFeedback({ type: 'error', message: error.response?.data?.detail || "Error al guardar el registro." });
    }
  };

  const handleAdvanceSubmit = async (e) => {
    e.preventDefault();
    if (!advanceAmount || !advanceDate) return;
    try {
      await axiosClient.post(`/api/v1/auxiliares/socios/${adjustingAdvance.id}/anticipos`, {
        monto: parseFloat(advanceAmount),
        fecha: advanceDate
      });
      setFeedback({ type: 'success', message: 'Anticipo registrado exitosamente.' });
      setAdjustingAdvance(null);
      await fetchAuxiliares();
    } catch (err) {
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Error al registrar anticipo.' });
    }
  };

  const openBulkEditFactores = () => {
    // Inicializar data con porcentajes
    const data = factoresRiesgo.map(f => ({
      ...f,
      peso_pct: f.peso !== null ? parseFloat((f.peso * 100).toFixed(2)) : 0
    }));
    setBulkFactoresData(data);
    setShowBulkEditFactores(true);
  };

  const handleBulkFactoresChange = (id, newValue) => {
    const parsed = parseFloat(newValue) || 0;
    setBulkFactoresData(prev => prev.map(f => f.id === id ? { ...f, peso_pct: parsed } : f));
  };

  const handleBulkFactoresSubmit = async (e) => {
    e.preventDefault();
    setBulkFactoresSaving(true);
    setFeedback(null);
    try {
      const promises = bulkFactoresData.map(f => {
        const original = factoresRiesgo.find(orig => orig.id === f.id);
        const nuevoPeso = parseFloat((f.peso_pct / 100).toFixed(4));
        if (original && original.peso !== nuevoPeso) {
          return axiosClient.put(`/api/v1/auxiliares/factores_riesgo/${f.id}`, {
            ...original,
            peso: nuevoPeso
          });
        }
        return null;
      }).filter(p => p !== null);

      if (promises.length > 0) {
        await Promise.all(promises);
        setFeedback({ type: 'success', message: 'Pesos actualizados exitosamente.' });
        await fetchAuxiliares();
      }
      setShowBulkEditFactores(false);
    } catch (error) {
      setFeedback({ type: 'error', message: "Error al actualizar los pesos." });
    } finally {
      setBulkFactoresSaving(false);
    }
  };

  const bulkFactoresTotal = bulkFactoresData.reduce((acc, f) => acc + f.peso_pct, 0);
  const isBulkFactoresValid = Math.abs(bulkFactoresTotal - 100) < 0.01;

  const formatCellValue = (col, value) => {
    if (value === null || value === undefined) return '-';
    if (['socio_comercial_id', 'socio_originador_id', 'socio_intermediario_id', 'gasto_1_socio_id', 'gasto_2_socio_id', 'id_socio_comercial'].includes(col)) {
      const socio = socios.find(s => s.id === value);
      return socio ? socio.razon_social : value;
    }
    if (col === 'id_riesgo') {
      const factor = factoresRiesgo.find(f => f.id === value);
      return factor ? factor.detalle : value;
    }
    if (col === 'id_provincia' || col === 'provincia_id') {
      const prov = provincias.find(p => p.id === value);
      return prov ? prov.nombre : value;
    }
    if (col === 'banco_id') {
      const banco = bancos.find(b => b.id === value);
      return banco ? banco.nombre_banco : value;
    }
    if (col === 'concepto_id') {
      const concepto = conceptos.find(c => c.id === value);
      return concepto ? concepto.name : value;
    }
    if (col === 'clasificacion_id') {
      const clasificacion = clasificaciones.find(c => c.id === value);
      return clasificacion ? clasificacion.name : value;
    }
    if (col === 'sueldo_tipo' && value) {
      return String(value).toUpperCase();
    }
    if (['es_pasivo', 'codigo_descuento', 'asignacion_familiar', 'horas_extras', 'vacaciones', 'otros', 'descuentos_voluntarios'].includes(col)) {
      return value ? 'Sí' : 'No';
    }
    if (percentFields.includes(col)) {
      return `${(value * 100).toFixed(2)}%`;
    }
    if (['capital', 'interes', 'iva', 'total', 'anticipo_vigente'].includes(col.toLowerCase())) {
      return `$ ${parseFloat(value).toLocaleString('es-AR', { minimumFractionDigits: 2 })}`;
    }
    return String(value);
  };

  const filteredData = tableData.filter(row => {
    return columns.every(col => {
      const filterValue = columnFilters[col];
      if (!filterValue) return true;
      const val = formatCellValue(col, row[col]);

      if (col === 'clasificacion_id' && filterValue === 'Sin Clasificar') {
        return val === '-';
      }

      if (col === 'estado') {
        return String(val).toUpperCase() === String(filterValue).toUpperCase();
      }

      return String(val).toLowerCase().includes(filterValue.toLowerCase());
    });
  });

  const sortedData = [...filteredData].sort((a, b) => {
    let valA = a[sortConfig.key];
    let valB = b[sortConfig.key];
    if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Tablas Auxiliares</h2>
        <p>Visor de tablas maestras cacheadas desde el Core Engine. Permite editar y eliminar registros siempre que no existan dependencias activas.</p>
      </header>

      {!editingRecord && !isCreating && feedback && (
        <div style={{
          marginBottom: '20px', padding: '16px', borderRadius: '8px', fontSize: '15px', fontWeight: 500,
          backgroundColor: feedback.type === 'error' ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
          color: feedback.type === 'error' ? 'var(--danger-color)' : 'var(--success-color)'
        }}>
          {feedback.message}
        </div>
      )}

      <div className="content-grid" style={{ display: 'block' }}>
        <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px', display: 'flex', gap: '16px', alignItems: 'center' }}>
          <label style={{ fontWeight: '600', color: 'var(--text-secondary)' }}>Seleccionar Tabla:</label>
          <select
            value={activeTable}
            onChange={(e) => { setActiveTable(e.target.value); setFeedback(null); setColumnFilters({}); }}
            className="input-field"
            style={{ minWidth: '250px' }}
          >
            {Object.keys(tablesMap).map(key => (
              <option key={key} value={key}>{tablesMap[key].name}</option>
            ))}
          </select>
        </div>

        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <h3 style={{ margin: 0, fontFamily: 'var(--font-heading)' }}>Registros de {currentTableConfig.name}</h3>
            <div style={{ display: 'flex', gap: '10px' }}>
              {activeTable === 'factoresRiesgo' && (
                <button className="btn-secondary" onClick={openBulkEditFactores} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  ⚖️ Ajustar Pesos (100%)
                </button>
              )}
              <ExportExcelButton data={filteredData} filename={`${currentTableConfig.name}_export`} />
              <button className="btn-primary" onClick={() => openEditModal()} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                + Nuevo {currentTableConfig.name.split(' ')[0]}
              </button>
            </div>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  {columns.map(col => {
                    let headerText = col.toUpperCase().replace(/_/g, ' ');
                    if (col === 'socio_comercial_id') headerText = 'SOCIO ORIGINADOR ASOCIADO';
                    else if (col === 'socio_originador_id') headerText = 'SOCIO ORIGINADOR';
                    else if (col === 'socio_intermediario_id') headerText = 'SOCIO INTERMEDIARIO';
                    else if (col === 'gasto_1_socio_id') headerText = 'GASTO 1 SOCIO';
                    else if (col === 'gasto_2_socio_id') headerText = 'GASTO 2 SOCIO';
                    else if (col === 'id_provincia' || col === 'provincia_id') headerText = 'PROVINCIA';
                    else if (col === 'es_pasivo') headerText = 'ES PASIVO';
                    else if (col === 'id_socio_comercial') headerText = 'SOCIO COMERCIAL';
                    return (
                      <th key={col} onClick={() => handleSort(col)} style={{ cursor: 'pointer', verticalAlign: 'top' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center' }}>
                          {headerText}
                          <span style={{ fontSize: '10px', opacity: sortConfig.key === col ? 1 : 0.3 }}>
                            {sortConfig.key === col ? (sortConfig.direction === 'asc' ? '⬆️' : '⬇️') : '↕️'}
                          </span>
                        </div>
                        <div onClick={e => e.stopPropagation()}>
                          {activeTable === 'tasasYComisiones' && col === 'estado' ? (
                            <select
                              value={columnFilters[col] || ''}
                              onChange={(e) => setColumnFilters(prev => ({ ...prev, [col]: e.target.value }))}
                              style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', boxSizing: 'border-box' }}
                            >
                              <option value="">Todos</option>
                              <option value="ACTIVA">ACTIVA</option>
                              <option value="INACTIVA">INACTIVA</option>
                            </select>
                          ) : activeTable === 'tasasYComisiones' && ['socio_originador_id', 'socio_intermediario_id', 'gasto_1_socio_id', 'gasto_2_socio_id'].includes(col) ? (
                            <select
                              value={columnFilters[col] || ''}
                              onChange={(e) => setColumnFilters(prev => ({ ...prev, [col]: e.target.value }))}
                              style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', boxSizing: 'border-box' }}
                            >
                              <option value="">Todos</option>
                              {socios.map(s => <option key={s.id} value={s.razon_social}>{s.razon_social}</option>)}
                            </select>
                          ) : activeTable === 'tasasYComisiones' && col === 'fecha' ? (
                            <input
                              type="date"
                              value={columnFilters[col] || ''}
                              onChange={(e) => setColumnFilters(prev => ({ ...prev, [col]: e.target.value }))}
                              style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', boxSizing: 'border-box' }}
                            />
                          ) : activeTable === 'conceptos' && col === 'clasificacion_id' ? (
                            <select
                              value={columnFilters[col] || ''}
                              onChange={(e) => setColumnFilters(prev => ({ ...prev, [col]: e.target.value }))}
                              style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', boxSizing: 'border-box' }}
                            >
                              <option value="">Todas</option>
                              <option value="Sin Clasificar">Sin Clasificar</option>
                              {clasificaciones.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
                            </select>
                          ) : (
                            <input
                              type="text"
                              placeholder="Filtrar..."
                              value={columnFilters[col] || ''}
                              onChange={(e) => setColumnFilters(prev => ({ ...prev, [col]: e.target.value }))}
                              style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', boxSizing: 'border-box' }}
                            />
                          )}
                        </div>
                      </th>
                    );
                  })}
                  <th style={{ textAlign: 'center', verticalAlign: 'top' }}>ACCIONES</th>
                </tr>
              </thead>
              <tbody>
                {sortedData.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length + 1} className="text-center empty-state">
                      No hay registros que coincidan con la búsqueda.
                    </td>
                  </tr>
                ) : (
                  sortedData.map((row) => (
                    <tr key={row.id}>
                      {columns.map(col => (
                        <td key={col}>{formatCellValue(col, row[col])}</td>
                      ))}
                      <td>
                        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
                          {activeTable === 'factoresRiesgo' && (
                            <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '14px' }} onClick={() => { setActiveTable('multiplicadoresRiesgo'); setColumnFilters({ id_riesgo: row.detalle }); }} title="Ver Multiplicadores">
                              📊
                            </button>
                          )}
                          {activeTable === 'socios' && (
                            <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--success-color)' }} onClick={() => { setAdjustingAdvance(row); setAdvanceAmount(''); setAdvanceDate(''); }} title="Ajustar Anticipo">
                              💲
                            </button>
                          )}
                          {activeTable === 'tasasYComisiones' && (
                            <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '14px', color: '#3b82f6' }} onClick={() => openDuplicateModal(row)} title="Duplicar">
                              📑
                            </button>
                          )}
                          <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '14px' }} onClick={() => openEditModal(row)} title="Editar">
                            ✏️
                          </button>
                          <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} onClick={() => handleDelete(row[currentTableConfig.idField || 'id'])} title="Eliminar">
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {(editingRecord || isCreating) && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
          backdropFilter: 'blur(4px)'
        }}>
          <div className="glass-panel" style={{
            width: '100%', maxWidth: '550px', maxHeight: '90vh', overflowY: 'auto',
            position: 'relative', padding: '32px'
          }}>
            <button onClick={closeEditModal} className="btn-secondary" style={{
              position: 'absolute', top: '16px', right: '16px', padding: '4px 12px'
            }}>X</button>
            <h3 style={{ marginBottom: '24px', fontFamily: 'var(--font-heading)' }}>
              {isCreating ? 'Agregar Nuevo Registro' : `Editar ${currentTableConfig.name}`}
            </h3>

            {(editingRecord || isCreating) && feedback && (
              <div style={{
                marginBottom: '20px', padding: '16px', borderRadius: '8px', fontSize: '15px', fontWeight: 500,
                backgroundColor: feedback.type === 'error' ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)',
                color: feedback.type === 'error' ? 'var(--danger-color)' : 'var(--success-color)'
              }}>
                {feedback.message}
              </div>
            )}

            <form onSubmit={handleEditSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
                {currentTableConfig.schema.map(col => {
                  if (col === 'id' && currentTableConfig.endpoint !== 'operadores') return null;
                  if (col === 'anticipo_vigente') return null;

                  const relation = relationMaps[col];
                  let inputElement;

                  if (currentTableConfig.endpoint === 'relaciones' && col === 'tabla') {
                    const tableOptions = [
                      'codigos_postales', 'empleadores', 'provincias',
                      'socios_comerciales', 'tasas_y_comisiones', 'comercializadores'
                    ];
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => {
                          handleEditChange(col, e.target.value);
                          handleEditChange('id_local', ''); // Reset id_local when tabla changes
                        }}
                        className="input-field" required
                      >
                        <option value="">Seleccione Tabla...</option>
                        {tableOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    );
                  } else if (currentTableConfig.endpoint === 'relaciones' && col === 'id_local') {
                    const selectedTabla = editFormData['tabla'];
                    let localOptions = [];
                    let localLabel = '';
                    if (selectedTabla === 'provincias') {
                      localOptions = provincias;
                      localLabel = 'nombre';
                    } else if (selectedTabla === 'empleadores') {
                      localOptions = empleadores;
                      localLabel = 'razon_social';
                    } else if (selectedTabla === 'tasas_y_comisiones') {
                      localOptions = tasasYComisiones;
                      localLabel = 'id'; // Placeholder
                    } else if (selectedTabla === 'socios_comerciales') {
                      localOptions = socios;
                      localLabel = 'razon_social';
                    } else if (selectedTabla === 'comercializadores') {
                      localOptions = comercializadores;
                      localLabel = 'nombre';
                    }

                    if (!selectedTabla) {
                      inputElement = (
                        <select className="input-field" disabled>
                          <option value="">Seleccione Tabla primero...</option>
                        </select>
                      );
                    } else if (localOptions && localOptions.length > 0) {
                      inputElement = (
                        <select
                          value={editFormData[col] ?? ''}
                          onChange={(e) => handleEditChange(col, e.target.value)}
                          className="input-field" required
                        >
                          <option value="">Seleccione Registro Local...</option>
                          {localOptions.map(opt => (
                            <option key={opt.id} value={opt.id}>
                              {opt.id} - {localLabel === 'id' ? `Plazo: ${opt.plazo} TNA: ${(opt.tna_c_iva * 100).toFixed(2)}%` : opt[localLabel]}
                            </option>
                          ))}
                        </select>
                      );
                    } else {
                      inputElement = (
                        <input
                          type="number"
                          step="1"
                          placeholder="Ingrese el ID local numérico"
                          value={editFormData[col] ?? ''}
                          onChange={(e) => handleEditChange(col, e.target.value)}
                          className="input-field" required
                        />
                      );
                    }
                  } else if (relation) {
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field"
                      >
                        <option value="">Seleccione...</option>
                        {relation.options.map(opt => (
                          <option key={opt[relation.valueKey]} value={opt[relation.valueKey]}>
                            {opt[relation.labelKey]}
                          </option>
                        ))}
                      </select>
                    );
                  } else if (col === 'calificacion') {
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field" required
                      >
                        <option value="">Seleccione...</option>
                        {['EXCELENTE', 'BUENO', 'REGULAR', 'MALO', 'RECHAZADO'].map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    );
                  } else if (col === 'estado') {
                    const estadoOptions = currentTableConfig.endpoint === 'tasas_y_comisiones'
                      ? ['ACTIVA', 'INACTIVA', 'SEMI ACTIVA']
                      : ['ACTIVO', 'INACTIVO'];
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field" required
                      >
                        <option value="">Seleccione...</option>
                        {estadoOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    );
                  } else if (col === 'tipo_cuenta') {
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field" required
                      >
                        <option value="">Seleccione...</option>
                        {['Cuenta Corriente', 'Caja de Ahorros', 'Plazo Fijo', 'Fondo Común de Inversión'].map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    );
                  } else if (col === 'moneda') {
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field" required
                      >
                        <option value="">Seleccione...</option>
                        {['Pesos Argentinos $', 'Dólares Estadounidenses USD', 'Euros EUR'].map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    );
                  } else if (col === 'tipo_movimiento') {
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field" required
                      >
                        <option value="">Seleccione...</option>
                        {["Ingreso", "Egreso", "Suscripción FCI", "Rescate FCI", "Ingresos a plazo fijo", "Egresos de plazo fijo"].map(opt => <option key={opt} value={opt}>{opt}</option>)}
                      </select>
                    );
                  } else if (col === 'lista_gafi') {
                    inputElement = (
                      <select
                        value={editFormData[col] ?? 'Lista Blanca'}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field" required
                      >
                        <option value="Lista Blanca">Lista Blanca</option>
                        <option value="Lista Gris">Lista Gris</option>
                        <option value="Lista Negra">Lista Negra</option>
                      </select>
                    );
                  } else if (col === 'parser_type') {
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field"
                      >
                        <option value="none">Sin importación automática</option>
                        <option value="bica">Banco Ficticio</option>
                        <option value="santander">Banco Santander</option>
                        <option value="pampa">Banco Pampa</option>
                      </select>
                    );
                  } else if (col === 'fecha') {
                    inputElement = (
                      <input
                        type="date"
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field" required
                      />
                    );
                  } else if (col === 'plazo') {
                    inputElement = (
                      <input
                        type="number"
                        step="1"
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field" required
                      />
                    );
                  } else if (percentFields.includes(col)) {
                    inputElement = (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <input
                          type="number"
                          step="any"
                          value={editFormData[col] ?? ''}
                          onChange={(e) => handleEditChange(col, e.target.value)}
                          className="input-field" required
                        />
                        <span style={{ fontWeight: '600', color: 'var(--text-secondary)' }}>%</span>
                      </div>
                    );
                  } else if (col === 'sueldo_tipo') {
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field" required
                      >
                        <option value="">Seleccione...</option>
                        <option value="bruto">BRUTO</option>
                        <option value="neto">NETO</option>
                      </select>
                    );
                  } else if (['es_pasivo', 'codigo_descuento', 'asignacion_familiar', 'horas_extras', 'vacaciones', 'otros', 'descuentos_voluntarios'].includes(col)) {
                    inputElement = (
                      <label style={{ display: 'flex', alignItems: 'center', gap: '12px', fontWeight: 500, cursor: 'pointer', height: '100%' }}>
                        <div className="toggle-switch">
                          <input
                            type="checkbox"
                            checked={editFormData[col] ?? false}
                            onChange={(e) => handleEditChange(col, e.target.checked)}
                          />
                          <span className="slider"></span>
                        </div>
                        {col === 'es_pasivo' ? (editFormData[col] ? 'Sí (Jubilado/Pensionado)' : 'No') : (editFormData[col] ? 'SÍ' : 'NO')}
                      </label>
                    );
                  } else {
                    inputElement = (
                      <input
                        type="text"
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        className="input-field"
                      />
                    );
                  }

                  let labelText = col.toUpperCase().replace(/_/g, ' ');
                  if (col === 'socio_id') labelText = 'SOCIO COMERCIAL';
                  if (col === 'socio_comercial_id') labelText = 'SOCIO ORIGINADOR ASOCIADO';
                  if (col === 'id_socio_comercial') labelText = 'SOCIO COMERCIAL';
                  if (col === 'es_pasivo') labelText = 'ES PASIVO';

                  const formGroup = (
                    <div key={col} className="form-group">
                      <label>{labelText}</label>
                      {inputElement}
                    </div>
                  );

                  if (col === 'asignacion_familiar') {
                    return (
                      <React.Fragment key={`group-${col}`}>
                        <div style={{ gridColumn: '1 / -1', marginTop: '16px', marginBottom: '4px', fontSize: '13px', color: 'var(--text-secondary)', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '6px' }}>
                          <strong>Descuentos sobre el sueldo:</strong> (Si es SÍ, el concepto se resta del sueldo elegido)
                        </div>
                        {formGroup}
                      </React.Fragment>
                    );
                  } else if (col === 'descuentos_voluntarios') {
                    return (
                      <React.Fragment key={`group-${col}`}>
                        <div style={{ gridColumn: '1 / -1', marginTop: '16px', marginBottom: '4px', fontSize: '13px', color: 'var(--text-secondary)', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '6px' }}>
                          <strong>Descuentos Voluntarios:</strong> (Si es SÍ, se descuentan antes de calcular el cupo. Si es NO, se descuentan del cupo final)
                        </div>
                        {formGroup}
                      </React.Fragment>
                    );
                  }

                  return formGroup;
                })}
              </div>
              <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '12px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '20px' }}>
                <button type="button" onClick={closeEditModal} className="btn-secondary">
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  {isCreating ? 'Crear Registro' : 'Guardar Cambios'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de Ajuste de Anticipo */}
      {adjustingAdvance && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ width: '400px' }}>
            <h3 style={{ marginTop: 0, color: 'var(--text-color)' }}>Registrar Anticipo</h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Socio: {adjustingAdvance.razon_social}
            </p>
            <form onSubmit={handleAdvanceSubmit}>
              <div className="form-group">
                <label>Monto del Anticipo</label>
                <input 
                  type="number" 
                  step="0.01"
                  value={advanceAmount} 
                  onChange={(e) => setAdvanceAmount(e.target.value)} 
                  required 
                />
              </div>
              <div className="form-group">
                <label>Fecha</label>
                <input 
                  type="date" 
                  value={advanceDate} 
                  onChange={(e) => setAdvanceDate(e.target.value)} 
                  required 
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button type="button" className="btn-secondary" onClick={() => setAdjustingAdvance(null)}>Cancelar</button>
                <button type="submit" className="btn-primary">Guardar Anticipo</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Bulk Edit Factores */}
      {showBulkEditFactores && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ 
            width: '500px', maxWidth: '90%', 
            maxHeight: '90vh', display: 'flex', flexDirection: 'column' 
          }}>
            <h3 style={{ marginTop: 0, color: 'var(--text-color)', flexShrink: 0 }}>Ajustar Pesos de Riesgo</h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '20px', flexShrink: 0 }}>
              Ajuste los porcentajes de cada factor. <strong>La suma total debe ser exactamente 100%.</strong>
            </p>
            <form onSubmit={handleBulkFactoresSubmit} style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
              <div style={{ flex: 1, overflowY: 'auto', paddingRight: '10px', minHeight: '150px' }}>
                {bulkFactoresData.map(f => (
                  <div key={f.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ flex: 1, fontSize: '0.9rem' }}>
                      <div style={{ fontWeight: 'bold' }}>{f.detalle}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Código: {f.codigo}</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input 
                        type="number" 
                        step="0.1" 
                        min="0" 
                        max="100" 
                        value={f.peso_pct} 
                        onChange={(e) => handleBulkFactoresChange(f.id, e.target.value)}
                        className="input-field"
                        style={{ width: '80px', padding: '8px', textAlign: 'right', margin: 0 }}
                        disabled={f.codigo === 'cortes'}
                      />
                      <span style={{ color: 'var(--text-secondary)', fontWeight: 'bold' }}>%</span>
                    </div>
                  </div>
                ))}
              </div>
              
              <div style={{ flexShrink: 0 }}>
                <div style={{ 
                  marginTop: '16px', padding: '16px', borderRadius: '8px', 
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  background: isBulkFactoresValid ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                  border: `1px solid ${isBulkFactoresValid ? '#10b981' : '#ef4444'}`
                }}>
                  <span style={{ fontWeight: 'bold' }}>Total Resultante:</span>
                  <span style={{ 
                    fontWeight: 'bold', fontSize: '1.2rem',
                    color: isBulkFactoresValid ? '#10b981' : '#ef4444' 
                  }}>
                    {bulkFactoresTotal.toFixed(2)}%
                  </span>
                </div>
                
                {!isBulkFactoresValid && (
                  <div style={{ color: '#ef4444', fontSize: '0.85rem', marginTop: '8px', textAlign: 'center' }}>
                    El total debe ser 100%. Por favor, ajuste los valores.
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                  <button type="button" className="btn-secondary" onClick={() => setShowBulkEditFactores(false)}>Cancelar</button>
                  <button type="submit" className="btn-primary" disabled={!isBulkFactoresValid || bulkFactoresSaving}>
                    {bulkFactoresSaving ? "Guardando..." : "Guardar Pesos"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
};

export default AuxiliaryTablesPage;
