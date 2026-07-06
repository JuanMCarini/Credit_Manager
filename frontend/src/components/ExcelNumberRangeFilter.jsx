import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

const ExcelNumberRangeFilter = ({ selectedRange, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [minVal, setMinVal] = useState('');
  const [maxVal, setMaxVal] = useState('');
  const dropdownRef = useRef(null);
  const popupRef = useRef(null);
  const [coords, setCoords] = useState(null);

  // Update position for portal
  useEffect(() => {
    const updatePosition = () => {
      if (isOpen && dropdownRef.current) {
        const rect = dropdownRef.current.getBoundingClientRect();
        setCoords({
          left: rect.left,
          top: rect.bottom + 4,
          width: Math.max(200, rect.width)
        });
      }
    };

    if (isOpen) {
      updatePosition();
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
    }
    
    return () => {
      window.removeEventListener('scroll', updatePosition, true);
      window.removeEventListener('resize', updatePosition);
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      setMinVal(selectedRange?.min !== undefined ? selectedRange.min : '');
      setMaxVal(selectedRange?.max !== undefined ? selectedRange.max : '');
    }
  }, [isOpen, selectedRange]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        dropdownRef.current && !dropdownRef.current.contains(e.target) &&
        (!popupRef.current || !popupRef.current.contains(e.target))
      ) {
        setIsOpen(false);
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleApply = () => {
    onChange({ 
      min: minVal === '' ? undefined : Number(minVal), 
      max: maxVal === '' ? undefined : Number(maxVal) 
    });
    setIsOpen(false);
  };

  const handleClear = () => {
    setMinVal('');
    setMaxVal('');
    onChange({ min: undefined, max: undefined });
    setIsOpen(false);
  };

  const isActive = selectedRange && (selectedRange.min !== undefined || selectedRange.max !== undefined);

  return (
    <div className="excel-filter-container" ref={dropdownRef} style={{ position: 'relative', display: 'inline-block', width: '100%', marginTop: '5px' }}>
      <button 
        type="button"
        className={`excel-filter-trigger ${isActive ? 'active' : ''}`}
        onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen); }}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '4px 8px',
          background: isActive ? 'var(--primary)' : 'var(--surface-color)',
          color: isActive ? 'white' : 'var(--text-color)',
          border: `1px solid ${isActive ? 'var(--primary)' : 'var(--border-color)'}`,
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '12px'
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {isActive 
            ? `Rango: ${selectedRange.min !== undefined ? selectedRange.min : '-'} a ${selectedRange.max !== undefined ? selectedRange.max : '-'}`
            : 'Todos'}
        </span>
        <span style={{ opacity: 0.7, fontSize: '10px' }}>▼</span>
      </button>

      {isOpen && coords && createPortal(
        <div className="excel-filter-dropdown" ref={popupRef} onClick={e => e.stopPropagation()} style={{
          position: 'fixed',
          top: coords.top,
          left: coords.left,
          background: 'var(--surface-color)',
          border: '1px solid var(--border-color)',
          borderRadius: '6px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          zIndex: 9999,
          width: `${coords.width}px`,
          padding: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', marginBottom: '4px', color: 'var(--text-secondary)', textAlign: 'left' }}>Desde:</label>
            <input 
              type="number" 
              value={minVal} 
              onChange={e => setMinVal(e.target.value)}
              placeholder="Min..."
              style={{ width: '100%', padding: '6px', fontSize: '12px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.2)', color: 'var(--text-color)' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '12px', marginBottom: '4px', color: 'var(--text-secondary)', textAlign: 'left' }}>Hasta:</label>
            <input 
              type="number" 
              value={maxVal} 
              onChange={e => setMaxVal(e.target.value)}
              placeholder="Max..."
              style={{ width: '100%', padding: '6px', fontSize: '12px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'rgba(0,0,0,0.2)', color: 'var(--text-color)' }}
            />
          </div>
          
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            <button 
              type="button" 
              onClick={handleClear}
              style={{ flex: 1, padding: '6px', fontSize: '12px', background: 'transparent', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--text-color)', cursor: 'pointer' }}
            >
              Limpiar
            </button>
            <button 
              type="button" 
              onClick={handleApply}
              style={{ flex: 1, padding: '6px', fontSize: '12px', background: 'var(--primary)', border: 'none', borderRadius: '4px', color: 'white', cursor: 'pointer' }}
            >
              Aplicar
            </button>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default ExcelNumberRangeFilter;
