import { useState, useRef, useEffect } from 'react';
import * as XLSX from 'xlsx';
import { Download } from 'lucide-react';

const ExportExcelButton = ({ data, filteredData, filename = 'exportacion', fetchData }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleExport = async (type) => {
    setIsExporting(true);
    try {
      let dataToExport = type === 'completa' ? data : filteredData;
      
      if (fetchData) {
        dataToExport = await fetchData(type);
      }
      
      if (!dataToExport || dataToExport.length === 0) {
        alert("No hay datos para exportar.");
        return;
      }

      // Preprocesar datos para que Excel identifique correctamente fechas y números
      const processedData = dataToExport.map(row => {
        const newRow = {};
        for (const [key, value] of Object.entries(row)) {
          if (typeof value === 'string') {
            const strVal = value.trim();
            // Evitar procesar celdas vacías o con guiones
            if (strVal === '-' || strVal === '') {
              newRow[key] = value;
              continue;
            }
            
            // Regex para fechas YYYY-MM-DD o YYYY-MM-DD HH:mm:ss o ISO
            const dateRegex = /^\d{4}-\d{2}-\d{2}(T|\s)\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$|^\d{4}-\d{2}-\d{2}$/;
            // Regex para números (enteros o decimales)
            const numRegex = /^-?\d+(\.\d+)?$/;

            if (dateRegex.test(strVal)) {
              if (strVal.length === 10) {
                // "YYYY-MM-DD" exactly - parse manually to avoid timezone shifting
                const [year, month, day] = strVal.split('-');
                const parsedDate = new Date(Number(year), Number(month) - 1, Number(day));
                
                // Compensar el bug de SheetJS (xlsx) con las zonas horarias históricas.
                // Excel usa la época 1899-12-30. Como el offset UTC en Argentina en 1899 era distinto al de hoy,
                // la resta de milisegundos genera un desfase de fracciones de día (ej: 23:59:12 del día anterior).
                const epoch = new Date(1899, 11, 30);
                const offsetDiff = epoch.getTimezoneOffset() - parsedDate.getTimezoneOffset();
                parsedDate.setMinutes(parsedDate.getMinutes() + offsetDiff);
                
                newRow[key] = parsedDate;
              } else {
                const parsedDate = new Date(strVal);
                if (!isNaN(parsedDate.getTime())) {
                  newRow[key] = parsedDate;
                } else {
                  newRow[key] = value;
                }
              }
            } else if (numRegex.test(strVal)) {
              // Evitar quitar ceros a la izquierda (ej: '0123') y evitar pérdida de precisión en números muy largos
              if (strVal.length > 1 && strVal.startsWith('0') && !strVal.startsWith('0.')) {
                newRow[key] = value;
              } else if (strVal.length > 15) {
                newRow[key] = value;
              } else {
                newRow[key] = Number(strVal);
              }
            } else {
              newRow[key] = value;
            }
          } else {
            newRow[key] = value;
          }
        }
        return newRow;
      });

      const worksheet = XLSX.utils.json_to_sheet(processedData, { cellDates: true });
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "Datos");
      
      // Generar archivo Excel
      XLSX.writeFile(workbook, `${filename}.xlsx`);
    } catch (error) {
      console.error("Error al exportar:", error);
      alert("Error al exportar los datos.");
    } finally {
      setIsExporting(false);
      setIsOpen(false);
    }
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block', marginLeft: '8px' }} ref={dropdownRef}>
      <button 
        className="btn-secondary" 
        onClick={() => !isExporting && setIsOpen(!isOpen)}
        disabled={isExporting}
        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', height: '100%' }}
      >
        <Download size={16} />
        {isExporting ? 'Exportando...' : 'Exportar a Excel'}
      </button>

      {isOpen && (
        <div 
          style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: '4px',
            background: 'var(--surface-color)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            zIndex: 100,
            minWidth: '160px',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <button 
            onClick={() => handleExport('completa')}
            style={{
              padding: '8px 16px',
              textAlign: 'left',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-color)',
              cursor: 'pointer',
              borderBottom: '1px solid var(--border-color)'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            Descargar Completa
          </button>
          <button 
            onClick={() => handleExport('filtrada')}
            style={{
              padding: '8px 16px',
              textAlign: 'left',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-color)',
              cursor: 'pointer'
            }}
            onMouseOver={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            Descargar Filtrada
          </button>
        </div>
      )}
    </div>
  );
};

export default ExportExcelButton;
