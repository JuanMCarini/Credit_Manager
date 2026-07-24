import { useState, useEffect, useMemo } from 'react';
import axiosClient from '../api/axiosClient';
import { CheckCircle, Edit, Trash2, XCircle, Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import useAppStore from '../store/useAppStore';
import CarteraPreviewModal from '../components/CarteraPreviewModal';
import ExcelDateFilter from '../components/ExcelDateFilter';
import ExportExcelButton from '../components/ExportExcelButton';
import * as XLSX from 'xlsx';

const PortfolioOperationsPage = () => {
  const navigate = useNavigate();
  const { setEditingCompra } = useAppStore();
  const [carteras, setCarteras] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterFecha, setFilterFecha] = useState([]);
  
  // States for Edit Modal
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingCartera, setEditingCartera] = useState(null);
  const [isReadOnly, setIsReadOnly] = useState(false);
  
  // Loading state for legajos download
  const [loadingLegajos, setLoadingLegajos] = useState({});

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
    try {
      await axiosClient.patch(`/api/v1/carteras/${id}`, { estado: nuevoEstado });
      fetchCarteras();
    } catch (error) {
      alert("Error al cambiar estado: " + error.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("¿Seguro que desea eliminar esta cartera permanentemente?")) return;
    try {
      await axiosClient.delete(`/api/v1/carteras/${id}`);
      fetchCarteras();
    } catch (error) {
      alert("Error al eliminar cartera: " + error.message);
    }
  };

  const handleEditClick = (c, readOnly = false) => {
    if (c.tipo_operacion === 'COMPRA') {
      if (!readOnly) {
        setEditingCompra(c);
        navigate('/nueva-operacion-cartera');
        return;
      }
    }
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
          fecha_venta: cartera.fecha_compra || new Date().toISOString().split('T')[0],
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

      const formatDates = (arr, dateFields) => {
        return arr.map(item => {
          const newItem = { ...item };
          for (const field of dateFields) {
            if (newItem[field]) {
              let dateStr = newItem[field];
              if (dateStr.length === 7) dateStr += "-01";
              
              const d = new Date(dateStr + "T00:00:00");
              if (!isNaN(d)) {
                newItem[field] = d;
              }
            }
          }
          return newItem;
        });
      };

      const formattedCreditos = formatDates(creditos || [], ['fecha_emision']);
      const formattedCuotas = formatDates(cuotas || [], ['fecha_vencimiento', 'fecha_vencimiento_pago']);
      const formattedResumen = formatDates(resumen || [], ['mes', 'mes_pago', 'fecha_vencimiento']);

      const wb = XLSX.utils.book_new();
      
      const sheetOptions = { cellDates: true, dateNF: 'dd/mm/yyyy' };
      
      const wsCreditos = XLSX.utils.json_to_sheet(formattedCreditos, sheetOptions);
      XLSX.utils.book_append_sheet(wb, wsCreditos, "Créditos");
      
      const wsCuotas = XLSX.utils.json_to_sheet(formattedCuotas, sheetOptions);
      XLSX.utils.book_append_sheet(wb, wsCuotas, "Cuotas");
      
      const wsResumen = XLSX.utils.json_to_sheet(formattedResumen, sheetOptions);
      XLSX.utils.book_append_sheet(wb, wsResumen, "Vencimientos");
      
      XLSX.writeFile(wb, `Operacion_${cartera.id}_${cartera.nombre}.xlsx`);
    } catch (error) {
      alert("Error al descargar Excel: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleDownloadCsvs = async (cartera) => {
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
    }
  };

  const handleDownloadLegajos = async (cartera) => {
    setLoadingLegajos(prev => ({ ...prev, [cartera.id]: true }));
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
      setLoadingLegajos(prev => ({ ...prev, [cartera.id]: false }));
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
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="btn-secondary" style={{ padding: '4px', fontSize: '14px' }} onClick={() => handleDownloadExcel(c)} title="Descargar Excel de la Operación">
                        📊
                      </button>
                      <button className="btn-secondary" style={{ padding: '4px', fontSize: '14px' }} onClick={() => handleDownloadLegajos(c)} title="Descargar Legajos (PDF)" disabled={loadingLegajos[c.id]}>
                        {loadingLegajos[c.id] ? '⏳' : '📑'}
                      </button>
                      {c.tipo_operacion === 'VENTA' && (
                        <button className="btn-secondary" style={{ padding: '4px', fontSize: '14px' }} onClick={() => handleDownloadCsvs(c)} title="Descargar CSVs Generados">
                          📁
                        </button>
                      )}
                      {c.estado === 'PENDIENTE' && (
                        <>
                          <button className="btn-secondary" style={{ padding: '4px', fontSize: '14px' }} onClick={() => handleChangeEstado(c.id, c.tipo_operacion === 'VENTA' ? 'VENDIDA' : 'COMPRADA')} title="Confirmar">
                            ✅
                          </button>
                          <button className="btn-secondary" style={{ padding: '4px', fontSize: '14px' }} onClick={() => handleEditClick(c, true)} title="Ver Detalles">
                            👁️
                          </button>
                          <button className="btn-secondary" style={{ padding: '4px', fontSize: '14px' }} onClick={() => handleEditClick(c)} title="Editar">
                            ✏️
                          </button>
                          <button className="btn-secondary" style={{ padding: '4px', fontSize: '14px', color: 'var(--danger-color)' }} onClick={() => handleDelete(c.id)} title="Eliminar">
                            🗑️
                          </button>
                        </>
                      )}
                      {(c.estado === 'VENDIDA' || c.estado === 'COMPRADA') && (
                        <>
                          <button className="btn-secondary" style={{ padding: '4px', fontSize: '14px' }} onClick={() => handleEditClick(c, true)} title="Ver Detalles">
                            👁️
                          </button>
                          <button className="btn-secondary" style={{ padding: '4px', fontSize: '14px', color: 'var(--danger-color)' }} onClick={() => alert('No se puede anular una cartera ya confirmada directamente.')} title="Anular (No Permitido)">
                            ❌
                          </button>
                        </>
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
    </section>
  );
};

export default PortfolioOperationsPage;
