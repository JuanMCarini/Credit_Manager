import { useState, useEffect, useMemo } from 'react';
import axiosClient from '../api/axiosClient';
import { CheckCircle, Edit, Trash2, XCircle, Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import useAppStore from '../store/useAppStore';
import CarteraPreviewModal from '../components/CarteraPreviewModal';
import CarteraContratoModal from '../components/CarteraContratoModal';
import ExcelDateFilter from '../components/ExcelDateFilter';
import ExportExcelButton from '../components/ExportExcelButton';
import * as XLSX from 'xlsx';
import { getLocalDateISO } from '../utils/dates';
import { CARTERAS_EXPORT_COLUMNS, formatExcelValue } from '../utils/carteraExcelColumns';

const PortfolioOperationsPage = () => {
  const navigate = useNavigate();
  const { setEditingCompra } = useAppStore();
  const [carteras, setCarteras] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterFecha, setFilterFecha] = useState([]);
  
  // State for Contratos Firmados Modal
  const [viewContratoCartera, setViewContratoCartera] = useState(null);

  // States for Edit Modal
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingCartera, setEditingCartera] = useState(null);
  const [isReadOnly, setIsReadOnly] = useState(false);
  
  // Loading state for actions
  const [loadingActions, setLoadingActions] = useState({});

  const fetchCarteras = async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get('/api/v1/carteras');
      setCarteras(res.data);
    } catch (error) {
      alert("Error cargando carteras: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const AVAILABLE_FECHAS = useMemo(() => [...new Set(carteras.map(c => c.fecha_compra).filter(Boolean))], [carteras]);

  const filteredCarteras = useMemo(() => {
    let result = [...carteras];
    if (filterFecha && filterFecha.length > 0) result = result.filter(c => filterFecha.includes(c.fecha_compra));
    return result;
  }, [carteras, filterFecha]);

  useEffect(() => {
    fetchCarteras();
  }, []);

  const handleChangeEstado = async (id, nuevoEstado) => {
    if (!window.confirm(`¿Seguro que desea cambiar el estado a ${nuevoEstado}?`)) return;
    setLoadingActions(prev => ({ ...prev, [`estado-${id}`]: true }));
    try {
      await axiosClient.patch(`/api/v1/carteras/${id}`, { estado: nuevoEstado });
      fetchCarteras();
    } catch (error) {
      alert("Error al cambiar estado: " + error.message);
    } finally {
      setLoadingActions(prev => ({ ...prev, [`estado-${id}`]: false }));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("¿Seguro que desea eliminar esta cartera permanentemente?")) return;
    setLoadingActions(prev => ({ ...prev, [`delete-${id}`]: true }));
    try {
      await axiosClient.delete(`/api/v1/carteras/${id}`);
      fetchCarteras();
    } catch (error) {
      alert("Error al eliminar cartera: " + error.message);
    } finally {
      setLoadingActions(prev => ({ ...prev, [`delete-${id}`]: false }));
    }
  };

  const handleEditClick = (c, readOnly = false) => {
    setIsReadOnly(readOnly);
    setEditingCartera(c);
    setShowEditModal(true);
  };

  const handleEditClose = () => {
    setShowEditModal(false);
    setEditingCartera(null);
  };

  const handleEditSuccess = () => {
    setShowEditModal(false);
    setEditingCartera(null);
    fetchCarteras();
  };

  const handleDownloadExcel = async (cartera) => {
    setLoadingActions(prev => ({ ...prev, [`excel-${cartera.id}`]: true }));
    try {
      let res;
      if (cartera.tipo_operacion === 'COMPRA') {
        res = await axiosClient.get(`/api/v1/carteras/compra/${cartera.id}/preview`);
      } else {
        res = await axiosClient.post('/api/v1/carteras/venta/preview', {
          cartera_id: cartera.id,
          usar_cuotas_guardadas: true,
          creditos_excluidos: [],
          nombre_cartera: cartera.nombre || 'Export',
          fecha_venta: cartera.fecha_compra || getLocalDateISO(),
          tna_descuento: cartera.tna_descuento || 0,
          cuit_comprador: '',
          razon_social_comprador: cartera.socio || '',
          mora: false, 
          recurso: cartera.recurso || false, 
          iva: cartera.iva || false, 
          cuotas_completas: false
        });
      }

      const { creditos, cuotas, resumen } = res.data;
      const isCompra = cartera.tipo_operacion === 'COMPRA';



      // 1. Mapeo de Créditos con encabezados amigables
      const mappedCreditos = (creditos || []).map(c => {
        if (isCompra) {
          return {
            'ID Externo': c.id_externo ?? '',
            'Cliente': c.cliente_nombre ?? '',
            'Fecha de Emisión': formatExcelValue(c.fecha_emision),
            'Capital Vendido': c.capital_vendido ?? 0,
            'Plazo': c.plazo ?? 0,
            'Cuotas Adquiridas': c.cuotas_compradas ?? 0,
            'Valor Actual': c.valor_actual ?? 0
          };
        }
        return {
          'ID Crédito': c.id ?? '',
          'Cliente': c.cliente ?? '',
          'Fecha de Emisión': formatExcelValue(c.fecha_emision),
          'Estado': c.estado ?? '',
          'Monto Otorgado': c.monto_otorgado ?? 0,
          'Total Cuotas': c.total_cuotas ?? 0,
          'Cuotas a Ceder': c.cuotas_a_ceder ?? 0,
          'Valor Actual': c.valor_actual ?? 0
        };
      });

      // 2. Mapeo de Cuotas con encabezados amigables
      const mappedCuotas = (cuotas || []).map(q => {
        if (isCompra) {
          return {
            'ID Crédito Externo': q.credito_id_externo ?? '',
            'Nro. Cuota': q.nro_cuota ?? '',
            'Fecha Vencimiento': formatExcelValue(q.fecha_vencimiento),
            'Fecha Vto. Pago': formatExcelValue(q.fecha_vencimiento_pago),
            'Capital': q.capital ?? 0,
            'Interés': q.interes ?? 0,
            'IVA': q.iva ?? 0,
            'Total Cuota': q.total ?? 0,
            'Valor Actual': q.valor_actual ?? 0,
            'Comprada': (q.comprada === true || q.comprada === 'Sí' || q.comprada === 'SI') ? 'Sí' : 'No'
          };
        }
        return {
          'ID Cuota': q.id ?? '',
          'ID Crédito': q.credito_id ?? '',
          'Nro. Cuota': q.nro_cuota ?? '',
          'Fecha Vencimiento': formatExcelValue(q.fecha_vencimiento),
          'Capital': q.capital ?? 0,
          'Interés': q.interes ?? 0,
          'IVA': q.iva ?? 0,
          'Total Cuota': q.total_cuota ?? 0,
          'Valor Actual': q.valor_actual ?? 0,
          'Incluida en Operación': (q.incluida === true || q.incluida === 'Sí' || q.incluida === 'SI') ? 'Sí' : 'No'
        };
      });

      // 3. Mapeo de Resumen/Vencimientos con encabezados amigables
      const mappedResumen = (resumen || []).map(r => {
        if (isCompra) {
          return {
            'Mes Vencimiento': formatExcelValue(r.mes),
            'Cantidad de Cuotas': r.cantidad_cuotas ?? 0,
            'Capital Total': r.capital_total ?? 0,
            'Interés Total': r.interes_total ?? 0,
            'IVA Total': r.iva_total ?? 0,
            'Monto Total': r.monto_total ?? 0,
            'Valor Actual': r.valor_actual ?? 0
          };
        }
        return {
          'Mes Vencimiento': formatExcelValue(r.fecha_vencimiento),
          'Cantidad de Cuotas': r.cantidad ?? 0,
          'Capital Total': r.capital ?? 0,
          'Interés Total': r.interes ?? 0,
          'IVA Total': r.iva ?? 0,
          'Monto Total': r.total_cuota ?? 0,
          'Valor Actual': r.valor_actual ?? 0
        };
      });

      const autoFitCols = (data) => {
        if (!data || data.length === 0) return [];
        const keys = Object.keys(data[0]);
        return keys.map(k => {
          let maxLen = k.length;
          for (let i = 0; i < Math.min(data.length, 500); i++) {
            const val = data[i][k];
            if (val !== undefined && val !== null) {
              const len = (val && typeof val === 'object' && val.v !== undefined) 
                ? (val.z === 'mm/yyyy' ? 7 : 10) 
                : String(val).length;
              if (len > maxLen) maxLen = len;
            }
          }
          return { wch: Math.min(Math.max(maxLen + 4, 12), 48) };
        });
      };

      const wb = XLSX.utils.book_new();
      
      const wsCreditos = XLSX.utils.json_to_sheet(mappedCreditos);
      wsCreditos['!cols'] = autoFitCols(mappedCreditos);
      XLSX.utils.book_append_sheet(wb, wsCreditos, "Créditos");
      
      const wsCuotas = XLSX.utils.json_to_sheet(mappedCuotas);
      wsCuotas['!cols'] = autoFitCols(mappedCuotas);
      XLSX.utils.book_append_sheet(wb, wsCuotas, "Cuotas");
      
      const wsResumen = XLSX.utils.json_to_sheet(mappedResumen);
      wsResumen['!cols'] = autoFitCols(mappedResumen);
      XLSX.utils.book_append_sheet(wb, wsResumen, "Vencimientos");
      
      XLSX.writeFile(wb, `Operacion_${cartera.id}_${cartera.nombre}.xlsx`);
    } catch (error) {
      alert("Error al descargar Excel: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoadingActions(prev => ({ ...prev, [`excel-${cartera.id}`]: false }));
    }
  };

  const handleDownloadCsvs = async (cartera) => {
    setLoadingActions(prev => ({ ...prev, [`csvs-${cartera.id}`]: true }));
    try {
      const response = await axiosClient.get(`/api/v1/carteras/${cartera.id}/export`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Venta_${cartera.id}_${cartera.nombre}.zip`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (error) {
      if (error.response && error.response.data instanceof Blob) {
        // Parse error blob
        const text = await error.response.data.text();
        try {
          const json = JSON.parse(text);
          alert("Error al descargar CSVs: " + (json.detail || "Error desconocido"));
        } catch {
          alert("Error al descargar CSVs.");
        }
      } else {
        alert("Error al descargar CSVs: " + (error.message || 'Error desconocido'));
      }
    } finally {
      setLoadingActions(prev => ({ ...prev, [`csvs-${cartera.id}`]: false }));
    }
  };

  const handleDownloadLegajos = async (cartera) => {
    setLoadingActions(prev => ({ ...prev, [`legajos-${cartera.id}`]: true }));
    try {
      const response = await axiosClient.get(`/api/v1/carteras/${cartera.id}/legajos/export`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Legajos_${cartera.id}_${cartera.nombre}.zip`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (error) {
      if (error.response && error.response.data instanceof Blob) {
        // Parse error blob
        const text = await error.response.data.text();
        try {
          const json = JSON.parse(text);
          alert("Error al descargar Legajos: " + (json.detail || "Error desconocido"));
        } catch {
          alert("Error al descargar Legajos.");
        }
      } else {
        alert("Error al descargar Legajos: " + (error.message || 'Error desconocido'));
      }
    } finally {
      setLoadingActions(prev => ({ ...prev, [`legajos-${cartera.id}`]: false }));
    }
  };

  const handleDownloadContrato = async (cartera, formato = 'pdf') => {
    setLoadingActions(prev => ({ ...prev, [`contrato-${formato}-${cartera.id}`]: true }));
    try {
      const response = await axiosClient.post(`/api/v1/papeleria/generar_por_cartera/${cartera.id}?formato=${formato}`, null, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Contrato_Cartera_${cartera.id}.${formato}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (error) {
      if (error.response && error.response.data instanceof Blob) {
        const text = await error.response.data.text();
        try {
          const json = JSON.parse(text);
          alert("Error al descargar contrato: " + (json.detail || "Error desconocido"));
        } catch {
          alert("Error al descargar contrato.");
        }
      } else {
        alert("Error al descargar contrato: " + (error.message || 'Error desconocido'));
      }
    } finally {
      setLoadingActions(prev => ({ ...prev, [`contrato-${formato}-${cartera.id}`]: false }));
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Operaciones de Cartera</h2>
          <p>Administración y registro de compras, ventas y recompras de cartera de créditos.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px', marginBottom: '8px' }}>
          <button className="btn-secondary" onClick={fetchCarteras} disabled={loading} style={{ height: 'fit-content', width: 'fit-content', paddingLeft: '24px', paddingRight: '24px' }}>
            {loading ? 'Actualizando...' : 'Actualizar Datos'}
          </button>
          <ExportExcelButton 
            data={carteras} 
            filteredData={filteredCarteras} 
            filename="operaciones_cartera_export" 
            columns={CARTERAS_EXPORT_COLUMNS}
          />
        </div>
      </header>
      
      <div className="glass-panel" style={{ overflowX: 'auto', maxHeight: 'calc(100vh - 180px)', overflowY: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Tipo Operación</th>
              <th>Estado</th>
              <th>Socio Comercial</th>
              <th>
                Fecha <br/>
                <ExcelDateFilter 
                  availableDates={AVAILABLE_FECHAS}
                  selectedDates={filterFecha}
                  onChange={setFilterFecha}
                />
              </th>
              <th>TNA</th>
              <th>Recurso</th>
              <th>IVA</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {filteredCarteras.length === 0 ? (
              <tr><td colSpan="10" className="text-center empty-state">{loading ? "Cargando..." : "No hay operaciones de cartera."}</td></tr>
            ) : (
              filteredCarteras.map(c => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>{c.nombre}</td>
                  <td>{c.tipo_operacion}</td>
                  <td>
                    <span className={`status-badge status-${(c.estado || '').toLowerCase()}`}>
                      {c.estado}
                    </span>
                  </td>
                  <td>{c.socio || '-'}</td>
                  <td>{c.fecha_compra}</td>
                  <td>{(c.tna_descuento * 100).toFixed(2)}%</td>
                  <td>{c.recurso ? 'Sí' : 'No'}</td>
                  <td>{c.iva ? 'Sí' : 'No'}</td>
                  <td style={{ textAlign: 'center', verticalAlign: 'middle', width: '135px' }}>
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(4, 28px)',
                      gap: '4px',
                      justifyContent: 'center',
                      alignItems: 'center'
                    }}>
                      {/* 1. Excel */}
                      <button 
                        className="btn-secondary" 
                        style={{ width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px' }} 
                        onClick={() => handleDownloadExcel(c)} 
                        title="Descargar Excel de la Operación" 
                        disabled={loadingActions[`excel-${c.id}`]}
                      >
                        {loadingActions[`excel-${c.id}`] ? '⏳' : '📊'}
                      </button>

                      {/* 2. Legajos */}
                      <button 
                        className="btn-secondary" 
                        style={{ width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px' }} 
                        onClick={() => handleDownloadLegajos(c)} 
                        title="Descargar Legajos (PDF)" 
                        disabled={loadingActions[`legajos-${c.id}`]}
                      >
                        {loadingActions[`legajos-${c.id}`] ? '⏳' : '📑'}
                      </button>

                      {/* 3. CSVs (solo si VENTA) */}
                      {c.tipo_operacion === 'VENTA' && (
                        <button 
                          className="btn-secondary" 
                          style={{ width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px' }} 
                          onClick={() => handleDownloadCsvs(c)} 
                          title="Descargar CSVs Generados" 
                          disabled={loadingActions[`csvs-${c.id}`]}
                        >
                          {loadingActions[`csvs-${c.id}`] ? '⏳' : '📁'}
                        </button>
                      )}

                      {/* 4. Modelo Contrato PDF (solo si NO tiene contrato firmado) */}
                      {!c.tiene_contrato_firmado && (
                        <button 
                          className="btn-secondary" 
                          style={{ width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px' }} 
                          onClick={() => handleDownloadContrato(c, 'pdf')} 
                          title="Descargar Modelo Contrato (PDF)" 
                          disabled={loadingActions[`contrato-pdf-${c.id}`]}
                        >
                          {loadingActions[`contrato-pdf-${c.id}`] ? '⏳' : '📜'}
                        </button>
                      )}

                      {/* 5. Modelo Contrato DOCX (solo si NO tiene contrato firmado) */}
                      {!c.tiene_contrato_firmado && (
                        <button 
                          className="btn-secondary" 
                          style={{ width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px' }} 
                          onClick={() => handleDownloadContrato(c, 'docx')} 
                          title="Descargar Modelo Contrato (DOCX)" 
                          disabled={loadingActions[`contrato-docx-${c.id}`]}
                        >
                          {loadingActions[`contrato-docx-${c.id}`] ? '⏳' : '📝'}
                        </button>
                      )}

                      {/* 6. Contratos Firmados */}
                      <button 
                        className="btn-secondary" 
                        style={{ 
                          width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px',
                          borderColor: c.tiene_contrato_firmado ? '#10b981' : undefined,
                          color: c.tiene_contrato_firmado ? '#10b981' : undefined
                        }} 
                        onClick={() => setViewContratoCartera(c)} 
                        title={c.tiene_contrato_firmado ? `Ver / Gestionar Contrato Firmado (${c.cant_documentos || 1})` : "Adjuntar Contrato Firmado"}
                      >
                        ✍️
                      </button>

                      {/* 7. Ver Detalles */}
                      <button 
                        className="btn-secondary" 
                        style={{ width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px' }} 
                        onClick={() => handleEditClick(c, true)} 
                        title="Ver Detalles"
                      >
                        👁️
                      </button>

                      {/* 8. Editar (solo PENDIENTE) */}
                      {c.estado === 'PENDIENTE' && (
                        <button 
                          className="btn-secondary" 
                          style={{ width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px' }} 
                          onClick={() => handleEditClick(c)} 
                          title="Editar"
                        >
                          ✏️
                        </button>
                      )}

                      {/* 9. Eliminar (solo PENDIENTE) */}
                      {c.estado === 'PENDIENTE' && (
                        <button 
                          className="btn-secondary" 
                          style={{ width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px', color: 'var(--danger-color)' }} 
                          onClick={() => handleDelete(c.id)} 
                          title="Eliminar" 
                          disabled={loadingActions[`delete-${c.id}`]}
                        >
                          {loadingActions[`delete-${c.id}`] ? '⏳' : '🗑️'}
                        </button>
                      )}

                      {/* 10. Confirmar (solo PENDIENTE) */}
                      {c.estado === 'PENDIENTE' && (
                        <button 
                          className="btn-secondary" 
                          style={{ width: '28px', height: '28px', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: '6px', color: '#10b981' }} 
                          onClick={() => handleChangeEstado(c.id, c.tipo_operacion === 'VENTA' ? 'VENDIDA' : 'COMPRADA')} 
                          title="Confirmar"
                          disabled={loadingActions[`estado-${c.id}`]}
                        >
                          {loadingActions[`estado-${c.id}`] ? '⏳' : '✅'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showEditModal && editingCartera && (
        <CarteraPreviewModal 
          cartera={editingCartera}
          onClose={handleEditClose}
          onSuccess={handleEditSuccess}
          isReadOnly={isReadOnly}
        />
      )}

      {viewContratoCartera && (
        <CarteraContratoModal 
          cartera={viewContratoCartera}
          onClose={() => setViewContratoCartera(null)}
          onSuccess={() => {
            fetchCarteras();
          }}
        />
      )}
    </section>
  );
};

export default PortfolioOperationsPage;
