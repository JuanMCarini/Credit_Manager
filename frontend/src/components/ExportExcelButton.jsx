import { useState, useRef, useEffect } from 'react';
import * as XLSX from 'xlsx';
import { Download } from 'lucide-react';

const ExportExcelButton = ({ data, filteredData, filename = 'exportacion' }) => {
  const [isOpen, setIsOpen] = useState(false);
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

  const handleExport = (type) => {
    const dataToExport = type === 'completa' ? data : filteredData;
    
    if (!dataToExport || dataToExport.length === 0) {
      alert("No hay datos para exportar.");
      return;
    }

    const worksheet = XLSX.utils.json_to_sheet(dataToExport);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Datos");
    
    // Generar archivo Excel
    XLSX.writeFile(workbook, `${filename}.xlsx`);
    setIsOpen(false);
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block', marginLeft: '8px' }} ref={dropdownRef}>
      <button 
        className="btn-secondary" 
        onClick={() => setIsOpen(!isOpen)}
        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px', height: '100%' }}
      >
        <Download size={16} />
        Exportar a Excel
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
