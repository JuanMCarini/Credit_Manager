import React, { useState } from 'react';
import useAppStore from '../store/useAppStore';
import axiosClient from '../api/axiosClient';

const AuxiliaryTablesPage = () => {
  const { provincias, empleadores, socios, tasasYComisiones, relaciones, fetchAuxiliares } = useAppStore();
  
  const [activeTable, setActiveTable] = useState('provincias');
  const [isCreating, setIsCreating] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [editFormData, setEditFormData] = useState({});
  const [feedback, setFeedback] = useState(null);

  const relationMaps = {
    socio_comercial_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    socio_originador_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    socio_intermediario_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    socio_id: { options: socios, valueKey: 'id', labelKey: 'razon_social' },
    provincia_id: { options: provincias, valueKey: 'id', labelKey: 'nombre' },
    id_provincia: { options: provincias, valueKey: 'id', labelKey: 'nombre' }
  };

  const percentFields = [
    'colocacion_originador', 'colocacion_intermediario', 
    'cobranza_originador', 'cobranza_intermediario', 
    'colocacion_propia', 'tna_c_iva', 'tna_s_iva', 'alicuota_iva'
  ];
  
  const tablesMap = {
    provincias: { name: 'Provincias', data: provincias, endpoint: 'provincias', schema: ['id', 'nombre'] },
    empleadores: { name: 'Empleadores', data: empleadores, endpoint: 'empleadores', schema: ['id', 'cuit', 'razon_social', 'socio_comercial_id'] },
    socios: { name: 'Socios Comerciales', data: socios, endpoint: 'socios', schema: ['id', 'razon_social', 'cuit', 'domicilio_legal', 'contacto_nombre', 'mail', 'telefono', 'dia_corte'] },
    tasasYComisiones: { name: 'Tasas y Comisiones', data: tasasYComisiones, endpoint: 'tasas_y_comisiones', schema: ['id', 'fecha', 'estado', 'socio_originador_id', 'socio_intermediario_id', 'colocacion_originador', 'colocacion_intermediario', 'cobranza_originador', 'cobranza_intermediario', 'colocacion_propia', 'plazo', 'tna_c_iva'] },
    relaciones: { name: 'Relaciones Mapeadas', data: relaciones, endpoint: 'relaciones', schema: ['id', 'socio_id', 'tabla', 'id_local', 'id_foraneo'] }
  };

  const currentTableConfig = tablesMap[activeTable];
  const tableData = currentTableConfig.data || [];
  const columns = tableData.length > 0 ? Object.keys(tableData[0]) : (currentTableConfig.schema || []);

  const handleDelete = async (id) => {
    if (!window.confirm("¿Estás seguro de que deseas eliminar este registro?")) return;
    
    setFeedback(null);
    try {
      await axiosClient.delete(`/api/v1/auxiliares/${currentTableConfig.endpoint}/${id}`);
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
        } else if (c === 'fecha') {
          emptyForm[c] = new Date().toISOString().split('T')[0]; // Default today
        } else {
          emptyForm[c] = '';
        }
      });
      setEditFormData(emptyForm);
    }
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

      if (isCreating) {
        await axiosClient.post(`/api/v1/auxiliares/${currentTableConfig.endpoint}`, cleanedData);
        setFeedback({ type: 'success', message: 'Registro creado exitosamente.' });
      } else {
        await axiosClient.put(`/api/v1/auxiliares/${currentTableConfig.endpoint}/${editingRecord.id}`, cleanedData);
        setFeedback({ type: 'success', message: 'Registro actualizado exitosamente.' });
      }
      await fetchAuxiliares();
      closeEditModal();
    } catch (error) {
      setFeedback({ type: 'error', message: error.response?.data?.detail || "Error al guardar el registro." });
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Tablas Auxiliares</h2>
        <p>Visor de tablas maestras cacheadas desde el Core Engine. Permite editar y eliminar registros siempre que no existan dependencias activas.</p>
      </header>
      
      {feedback && (
        <div className={`alert ${feedback.type === 'error' ? 'alert-error' : 'alert-success'}`} style={{ marginBottom: '20px' }}>
          {feedback.message}
        </div>
      )}

      <div className="content-grid" style={{ display: 'block' }}>
        <div className="glass-panel" style={{ padding: '20px', marginBottom: '20px' }}>
          <label style={{ fontWeight: 'bold', marginRight: '10px' }}>Seleccionar Tabla:</label>
          <select 
            value={activeTable} 
            onChange={(e) => { setActiveTable(e.target.value); setFeedback(null); }}
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', minWidth: '250px' }}
          >
            {Object.keys(tablesMap).map(key => (
              <option key={key} value={key}>{tablesMap[key].name}</option>
            ))}
          </select>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0 }}>Registros ({tableData.length})</h3>
            <button 
              className="btn-primary" 
              onClick={() => openEditModal(null)}
              style={{ padding: '8px 16px', borderRadius: '4px', border: 'none', background: 'var(--primary-color)', color: 'white', cursor: 'pointer' }}
            >
              + Agregar Registro
            </button>
          </div>
          
          {tableData.length === 0 ? (
            <p style={{ opacity: 0.7 }}>No hay registros en esta tabla.</p>
          ) : (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    {columns.map(col => <th key={col}>{col.toUpperCase().replace(/_/g, ' ')}</th>)}
                    <th style={{ width: '120px', textAlign: 'center' }}>ACCIONES</th>
                  </tr>
                </thead>
                <tbody>
                  {tableData.map((row, idx) => (
                    <tr key={row.id || idx}>
                      {columns.map(col => {
                        let displayValue = String(row[col] ?? '');
                        if (percentFields.includes(col) && row[col] !== null) {
                          displayValue = `${(row[col] * 100).toFixed(2)}%`;
                        }
                        return <td key={col}>{displayValue}</td>;
                      })}
                      <td style={{ textAlign: 'center' }}>
                        <button 
                          className="btn-icon" 
                          onClick={() => openEditModal(row)}
                          title="Editar"
                          style={{ marginRight: '8px', cursor: 'pointer', background: 'none', border: 'none', color: 'var(--primary-color)' }}
                        >
                          ✏️
                        </button>
                        <button 
                          className="btn-icon" 
                          onClick={() => handleDelete(row.id)}
                          title="Eliminar"
                          style={{ cursor: 'pointer', background: 'none', border: 'none', color: 'var(--danger-color)' }}
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {(editingRecord || isCreating) && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
          backdropFilter: 'blur(5px)'
        }}>
          <div className="glass-panel" style={{
            width: '100%', maxWidth: '500px', maxHeight: '90vh', overflowY: 'auto',
            position: 'relative', padding: '24px'
          }}>
            <button onClick={closeEditModal} style={{
              position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none',
              color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px'
            }}>✕</button>
            <h3 style={{ marginBottom: '20px', color: 'var(--primary-color)' }}>
              {isCreating ? 'Agregar Nuevo Registro' : `Editar ${currentTableConfig.name}`}
            </h3>
            
            <form onSubmit={handleEditSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              {columns.map(col => {
                if (col === 'id' && !isCreating) return null; // Prevent editing ID on update
                if (col === 'id' && isCreating) return null; // Prevent typing ID on create (auto-increment)
                
                const relation = relationMaps[col];
                
                const inputStyle = { padding: '10px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-color)', color: 'var(--text-primary)', width: '100%' };
                let inputElement;

                if (currentTableConfig.endpoint === 'relaciones' && col === 'tabla') {
                  const tableOptions = [
                    'codigos_postales', 'empleadores', 'provincias', 
                    'socios_comerciales', 'tasas_y_comisiones'
                  ];
                  inputElement = (
                    <select
                      value={editFormData[col] ?? ''}
                      onChange={(e) => {
                        handleEditChange(col, e.target.value);
                        handleEditChange('id_local', ''); // Reset id_local when tabla changes
                      }}
                      style={inputStyle}
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
                  }
                  
                  if (!selectedTabla) {
                    inputElement = (
                      <select style={inputStyle} disabled>
                        <option value="">Seleccione Tabla primero...</option>
                      </select>
                    );
                  } else if (localOptions && localOptions.length > 0) {
                    inputElement = (
                      <select
                        value={editFormData[col] ?? ''}
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        style={inputStyle}
                      >
                        <option value="">Seleccione Registro Local...</option>
                        {localOptions.map(opt => (
                          <option key={opt.id} value={opt.id}>
                            {opt.id} - {localLabel === 'id' ? `Plazo: ${opt.plazo} TNA: ${(opt.tna_c_iva*100).toFixed(2)}%` : opt[localLabel]}
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
                        style={inputStyle}
                      />
                    );
                  }
                } else if (relation) {
                  inputElement = (
                    <select 
                      value={editFormData[col] ?? ''} 
                      onChange={(e) => handleEditChange(col, e.target.value)}
                      style={inputStyle}
                    >
                      <option value="">Seleccione...</option>
                      {relation.options.map(opt => (
                        <option key={opt[relation.valueKey]} value={opt[relation.valueKey]}>
                          {opt[relation.labelKey]}
                        </option>
                      ))}
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
                      style={inputStyle}
                    >
                      <option value="">Seleccione...</option>
                      {estadoOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                  );
                } else if (col === 'fecha') {
                  inputElement = (
                    <input 
                      type="date" 
                      value={editFormData[col] ?? ''} 
                      onChange={(e) => handleEditChange(col, e.target.value)}
                      style={inputStyle}
                    />
                  );
                } else if (col === 'plazo') {
                  inputElement = (
                    <input 
                      type="number" 
                      step="1"
                      value={editFormData[col] ?? ''} 
                      onChange={(e) => handleEditChange(col, e.target.value)}
                      style={inputStyle}
                    />
                  );
                } else if (percentFields.includes(col)) {
                  inputElement = (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <input 
                        type="number" 
                        step="any"
                        value={editFormData[col] ?? ''} 
                        onChange={(e) => handleEditChange(col, e.target.value)}
                        style={inputStyle}
                      />
                      <span style={{ fontWeight: 'bold' }}>%</span>
                    </div>
                  );
                } else {
                  inputElement = (
                    <input 
                      type="text" 
                      value={editFormData[col] ?? ''} 
                      onChange={(e) => handleEditChange(col, e.target.value)}
                      style={inputStyle}
                    />
                  );
                }

                let labelText = col.toUpperCase().replace(/_/g, ' ');
                if (col === 'socio_id') labelText = 'SOCIO COMERCIAL';

                return (
                  <div key={col} style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                    <label style={{ fontSize: '0.9em', fontWeight: 'bold' }}>{labelText}</label>
                    {inputElement}
                  </div>
                );
              })}
              <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button type="button" onClick={closeEditModal} className="btn-secondary" style={{ padding: '10px 20px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--text-primary)', cursor: 'pointer' }}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" style={{ padding: '10px 20px', borderRadius: '4px', border: 'none', background: 'var(--primary-color)', color: 'white', cursor: 'pointer' }}>
                  {isCreating ? 'Crear' : 'Guardar Cambios'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
};

export default AuxiliaryTablesPage;
