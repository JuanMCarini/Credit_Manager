import { useState, useRef, useEffect } from 'react';
import * as XLSX from 'xlsx';
import { Download } from 'lucide-react';
import { formatExcelValue } from '../utils/carteraExcelColumns';

const ExportExcelButton = ({ data, filteredData, filename = 'exportacion', fetchData, columns }) => {
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
        if (columns && columns.length > 0) {
          for (const col of columns) {
            const colKey = typeof col === 'string' ? col : col.key;
            const colLabel = typeof col === 'string' ? col : (col.label || col.header || col.key);
            let rawValue = row[colKey];
            if (col.format && typeof col.format === 'function') {
              rawValue = col.format(rawValue, row);
            }
            newRow[colLabel] = formatExcelValue(rawValue);
          }
        } else {
          for (const [key, value] of Object.entries(row)) {
            newRow[key] = formatExcelValue(value);
          }
        }
        return newRow;
      });

      const worksheet = XLSX.utils.json_to_sheet(processedData);
      
      // Auto-fit column widths
      if (processedData && processedData.length > 0) {
        const colKeys = Object.keys(processedData[0]);
        worksheet['!cols'] = colKeys.map(k => {
          let maxLen = k.length;
          for (let i = 0; i < Math.min(processedData.length, 500); i++) {
            const val = processedData[i][k];
            if (val !== undefined && val !== null) {
              const len = (val && typeof val === 'object' && val.v !== undefined) ? (val.z === 'mm/yyyy' ? 7 : 10) : String(val).length;
              if (len > maxLen) maxLen = len;
            }
          }
          return { wch: Math.min(Math.max(maxLen + 4, 12), 48) };
        });
      }

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
        style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: isExporting ? 'not-allowed' : 'pointer', height: '100%' }}
      >
        <Download size={16} />
        {isExporting ? 'Exportando...' : 'Exportar a Excel'}
      </button>

      {isOpen && (
        <div 
          className="glass-panel" 
          style={{
            position: 'absolute',
            right: 0,
            top: '100%',
            marginTop: '4px',
            zIndex: 100,
            display: 'flex',
            flexDirection: 'column',
            minWidth: '160px',
            padding: '4px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            borderRadius: '6px'
          }}
        >
          <button 
            style={{
              padding: '8px 12px',
              textAlign: 'left',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-color)',
              cursor: 'pointer',
              fontSize: '13px',
              borderRadius: '4px'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.05)'}
            onMouseOut={(e) => e.target.style.backgroundColor = 'transparent'}
            onClick={() => handleExport('filtrada')}
          >
            Vista Actual {filteredData && `(${filteredData.length})`}
          </button>
          
          <button 
            style={{
              padding: '8px 12px',
              textAlign: 'left',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-color)',
              cursor: 'pointer',
              fontSize: '13px',
              borderRadius: '4px'
            }}
            onMouseOver={(e) => e.target.style.backgroundColor = 'rgba(255, 255, 255, 0.05)'}
            onMouseOut={(e) => e.target.style.backgroundColor = 'transparent'}
            onClick={() => handleExport('completa')}
          >
            Tabla Completa {data && `(${data.length})`}
          </button>
        </div>
      )}
    </div>
  );
};

export default ExportExcelButton;
