import React, { useState, useMemo, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Filter, Check, Minus } from 'lucide-react';

const ExcelListFilter = ({ availableOptions, selectedOptions, onChange, title = "Filtrar..." }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  
  // Local state for the set of selected options during interaction
  const [localSet, setLocalSet] = useState(new Set());
  
  const dropdownRef = useRef(null);
  const popupRef = useRef(null);
  const [coords, setCoords] = useState(null);

  // Update position for portal
  useEffect(() => {
    const updatePosition = () => {
      if (isOpen && dropdownRef.current) {
        const rect = dropdownRef.current.getBoundingClientRect();
        
        const popupEstimatedHeight = 280; 
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;
        
        if (spaceBelow < popupEstimatedHeight && spaceAbove > spaceBelow) {
          setCoords({
            left: rect.left,
            bottom: window.innerHeight - rect.top + 4,
            width: Math.max(220, rect.width)
          });
        } else {
          setCoords({
            left: rect.left,
            top: rect.bottom + 4,
            width: Math.max(220, rect.width)
          });
        }
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

  // Initialize local set when opening
  useEffect(() => {
    if (isOpen) {
      if (selectedOptions && selectedOptions.length > 0) {
        setLocalSet(new Set(selectedOptions.map(String)));
      } else {
        // If empty, it means "No filter applied", so everything is selected
        setLocalSet(new Set(availableOptions.map(String)));
      }
      setSearch('');
    }
  }, [isOpen, selectedOptions, availableOptions]);

  // Click outside to close
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

  const filteredOptions = useMemo(() => {
    const searchLower = search.toLowerCase();
    const combinedOptions = [...availableOptions, ...(selectedOptions || [])];
    const uniqueOptions = [...new Set(combinedOptions.filter(opt => opt !== null && opt !== undefined).map(String))];
    
    if (!searchLower) return uniqueOptions;
    return uniqueOptions.filter(opt => opt.toLowerCase().includes(searchLower));
  }, [availableOptions, selectedOptions, search]);

  const toggleOption = (option) => {
    setLocalSet(prev => {
      const next = new Set(prev);
      if (next.has(option)) {
        next.delete(option);
      } else {
        next.add(option);
      }
      return next;
    });
  };

  const toggleAllFiltered = () => {
    const allFilteredSelected = filteredOptions.every(opt => localSet.has(opt));
    setLocalSet(prev => {
      const next = new Set(prev);
      if (allFilteredSelected) {
        filteredOptions.forEach(opt => next.delete(opt));
      } else {
        filteredOptions.forEach(opt => next.add(opt));
      }
      return next;
    });
  };

  const handleAceptar = () => {
    const combinedOptions = [...availableOptions, ...(selectedOptions || [])];
    const allAvailable = new Set(combinedOptions.filter(opt => opt !== null && opt !== undefined).map(String));
    
    // If everything available is selected (or nothing to filter from), return empty array to clear filter
    if (localSet.size === allAvailable.size) {
      onChange([]);
    } else {
      onChange(Array.from(localSet));
    }
    setIsOpen(false);
  };

  const isFilterActive = selectedOptions && selectedOptions.length > 0;
  
  const allFilteredSelected = filteredOptions.length > 0 && filteredOptions.every(opt => localSet.has(opt));
  const someFilteredSelected = filteredOptions.length > 0 && filteredOptions.some(opt => localSet.has(opt));
  const isIndeterminate = someFilteredSelected && !allFilteredSelected;

  return (
    <div style={{ position: 'relative', display: 'inline-block', width: '100%', boxSizing: 'border-box' }} ref={dropdownRef}>
      <div 
        onClick={(e) => { e.stopPropagation(); setIsOpen(!isOpen); }}
        style={{
          width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px',
          background: isFilterActive ? 'rgba(76, 175, 80, 0.2)' : 'var(--surface-color)',
          border: `1px solid ${isFilterActive ? '#4caf50' : 'var(--border-color)'}`,
          borderRadius: '4px', display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', cursor: 'pointer', boxSizing: 'border-box',
          height: '26px'
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 'normal' }}>
          {isFilterActive ? `${selectedOptions.length} selec.` : "Todos"}
        </span>
        <Filter size={12} color={isFilterActive ? '#4caf50' : 'currentColor'} />
      </div>

      {isOpen && coords && createPortal(
        <div 
          ref={popupRef}
          style={{
            position: 'fixed', 
            top: coords.top !== undefined ? coords.top : 'auto', 
            bottom: coords.bottom !== undefined ? coords.bottom : 'auto',
            left: coords.left, zIndex: 9999,
            background: 'var(--surface-color)', border: '1px solid var(--border-color)',
            borderRadius: '6px', padding: '8px', width: `${coords.width}px`,
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            display: 'flex', flexDirection: 'column', gap: '8px',
            color: 'var(--text-color)', textAlign: 'left', fontWeight: 'normal'
          }} onClick={e => e.stopPropagation()}
        >
          
          <input 
            type="text" 
            placeholder={title}
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ padding: '6px', fontSize: '12px', width: '100%', boxSizing: 'border-box', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.05)', color: 'inherit' }}
          />

          <div style={{ maxHeight: '200px', overflowY: 'auto', fontSize: '13px' }}>
            {filteredOptions.length > 0 && (
               <div style={{ display: 'flex', alignItems: 'center', padding: '4px 0', gap: '6px', borderBottom: '1px solid var(--border-color)', marginBottom: '4px' }}>
                 <div 
                   onClick={toggleAllFiltered}
                   style={{ 
                     width: '14px', height: '14px', border: '1px solid var(--border-color)', borderRadius: '3px',
                     display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
                     background: allFilteredSelected || isIndeterminate ? 'var(--primary-color)' : 'transparent',
                     borderColor: allFilteredSelected || isIndeterminate ? 'var(--primary-color)' : 'var(--border-color)',
                     flexShrink: 0
                   }}
                 >
                   {allFilteredSelected && <Check size={10} color="white" />}
                   {isIndeterminate && <Minus size={10} color="white" />}
                 </div>
                 <span style={{ cursor: 'pointer', userSelect: 'none', fontWeight: 'bold' }} onClick={toggleAllFiltered}>(Seleccionar todos)</span>
               </div>
            )}
            
            {filteredOptions.map(opt => {
              const isChecked = localSet.has(opt);
              return (
                <div key={opt} style={{ display: 'flex', alignItems: 'center', padding: '3px 0', gap: '6px' }}>
                  <div 
                    onClick={() => toggleOption(opt)}
                    style={{ 
                      width: '14px', height: '14px', border: '1px solid var(--border-color)', borderRadius: '3px',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
                      background: isChecked ? 'var(--primary-color)' : 'transparent',
                      borderColor: isChecked ? 'var(--primary-color)' : 'var(--border-color)',
                      flexShrink: 0
                    }}
                  >
                    {isChecked && <Check size={10} color="white" />}
                  </div>
                  <span style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => toggleOption(opt)}>{opt}</span>
                </div>
              );
            })}
            {filteredOptions.length === 0 && (
              <div style={{ padding: '8px', textAlign: 'center', opacity: 0.5, fontSize: '12px' }}>Sin resultados</div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '6px', justifyContent: 'space-between', marginTop: '4px' }}>
            <button 
              onClick={() => { onChange([]); setIsOpen(false); }}
              style={{ padding: '4px 8px', fontSize: '12px', background: 'transparent', border: 'none', color: 'var(--danger-color)', cursor: 'pointer', borderRadius: '4px', fontWeight: 'bold' }}
            >
              Limpiar
            </button>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button 
                onClick={() => setIsOpen(false)}
                style={{ padding: '4px 8px', fontSize: '12px', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-color)', cursor: 'pointer', borderRadius: '4px' }}
              >Cancelar</button>
              <button 
                onClick={handleAceptar}
                style={{ padding: '4px 8px', fontSize: '12px', background: 'var(--primary-color)', border: 'none', color: 'white', borderRadius: '4px', cursor: 'pointer' }}
              >Aceptar</button>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

export default ExcelListFilter;
