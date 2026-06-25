import React, { useState, useMemo, useEffect, useRef } from 'react';
import { ChevronRight, ChevronDown, Filter, Check, Minus } from 'lucide-react';

const ExcelDateFilter = ({ availableDates, selectedDates, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  
  // Local state for the set of selected dates during interaction
  const [localSet, setLocalSet] = useState(new Set());
  
  const dropdownRef = useRef(null);

  // Initialize local set when opening
  useEffect(() => {
    if (isOpen) {
      if (selectedDates && selectedDates.length > 0) {
        setLocalSet(new Set(selectedDates));
      } else {
        // If empty, it means "No filter applied", so everything is selected
        setLocalSet(new Set(availableDates));
      }
      setSearch('');
    }
  }, [isOpen, selectedDates, availableDates]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Grouping dates into Years > Months > Days
  const hierarchy = useMemo(() => {
    const validDates = availableDates.filter(d => typeof d === 'string' && d.trim() !== '');
    // apply search filter
    const searchLower = search.toLowerCase();
    
    const h = {};
    for (const d of validDates) {
      if (!d.includes(searchLower)) continue; // basic search over YYYY-MM-DD
      let year, month, day;
      if (d.includes('/')) {
        [day, month, year] = d.split('/');
      } else {
        [year, month, day] = d.split('-');
      }
      if (!year || !month || !day) continue;
      
      if (!h[year]) h[year] = { dates: [], months: {} };
      h[year].dates.push(d);
      
      if (!h[year].months[month]) h[year].months[month] = { dates: [], days: {} };
      h[year].months[month].dates.push(d);
      
      if (!h[year].months[month].days[day]) h[year].months[month].days[day] = [];
      h[year].months[month].days[day].push(d);
    }
    
    return h;
  }, [availableDates, search]);

  const toggleYear = (year) => {
    const yearDates = hierarchy[year].dates;
    const allSelected = yearDates.every(d => localSet.has(d));
    
    setLocalSet(prev => {
      const next = new Set(prev);
      if (allSelected) {
        yearDates.forEach(d => next.delete(d));
      } else {
        yearDates.forEach(d => next.add(d));
      }
      return next;
    });
  };

  const toggleMonth = (year, month) => {
    const monthDates = hierarchy[year].months[month].dates;
    const allSelected = monthDates.every(d => localSet.has(d));
    
    setLocalSet(prev => {
      const next = new Set(prev);
      if (allSelected) {
        monthDates.forEach(d => next.delete(d));
      } else {
        monthDates.forEach(d => next.add(d));
      }
      return next;
    });
  };

  const toggleDay = (year, month, day) => {
    const dayDates = hierarchy[year].months[month].days[day];
    const allSelected = dayDates.every(d => localSet.has(d));
    
    setLocalSet(prev => {
      const next = new Set(prev);
      if (allSelected) {
        dayDates.forEach(d => next.delete(d));
      } else {
        dayDates.forEach(d => next.add(d));
      }
      return next;
    });
  };

  const handleAceptar = () => {
    // If everything is selected, return empty array to clear filter
    if (localSet.size === availableDates.length) {
      onChange([]);
    } else {
      onChange(Array.from(localSet));
    }
    setIsOpen(false);
  };

  const isFilterActive = selectedDates && selectedDates.length > 0;

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
          {isFilterActive ? `${selectedDates.length} selec.` : "Todos"}
        </span>
        <Filter size={12} color={isFilterActive ? '#4caf50' : 'currentColor'} />
      </div>

      {isOpen && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, zIndex: 1000,
          background: 'var(--surface-color)', border: '1px solid var(--border-color)',
          borderRadius: '6px', padding: '8px', width: '220px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px',
          display: 'flex', flexDirection: 'column', gap: '8px',
          color: 'var(--text-color)', textAlign: 'left', fontWeight: 'normal'
        }} onClick={e => e.stopPropagation()}>
          
          <input 
            type="text" 
            placeholder="Buscar..." 
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ padding: '6px', fontSize: '12px', width: '100%', boxSizing: 'border-box', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.05)', color: 'inherit' }}
          />

          <div style={{ maxHeight: '200px', overflowY: 'auto', fontSize: '13px' }}>
            {Object.keys(hierarchy).sort((a,b)=>b.localeCompare(a)).map(year => {
              const yearDates = hierarchy[year].dates;
              const selectedCount = yearDates.filter(d => localSet.has(d)).length;
              const isChecked = selectedCount === yearDates.length;
              const isIndeterminate = selectedCount > 0 && selectedCount < yearDates.length;

              return (
                <TreeNode 
                  key={year} 
                  label={year} 
                  isChecked={isChecked} 
                  isIndeterminate={isIndeterminate}
                  onToggle={() => toggleYear(year)}
                >
                  {Object.keys(hierarchy[year].months).sort((a,b)=>a.localeCompare(b)).map(month => {
                    const monthDates = hierarchy[year].months[month].dates;
                    const selectedCountMonth = monthDates.filter(d => localSet.has(d)).length;
                    const isCheckedMonth = selectedCountMonth === monthDates.length;
                    const isIndeterminateMonth = selectedCountMonth > 0 && selectedCountMonth < monthDates.length;

                    return (
                      <TreeNode 
                        key={month} 
                        label={month} 
                        isChecked={isCheckedMonth} 
                        isIndeterminate={isIndeterminateMonth}
                        onToggle={() => toggleMonth(year, month)}
                      >
                        {Object.keys(hierarchy[year].months[month].days).sort((a,b)=>a.localeCompare(b)).map(day => {
                          const dayDates = hierarchy[year].months[month].days[day];
                          const selectedCountDay = dayDates.filter(d => localSet.has(d)).length;
                          const isCheckedDay = selectedCountDay === dayDates.length;

                          return (
                            <TreeNode 
                              key={day} 
                              label={day} 
                              isChecked={isCheckedDay} 
                              isIndeterminate={false}
                              onToggle={() => toggleDay(year, month, day)}
                              isLeaf={true}
                            />
                          );
                        })}
                      </TreeNode>
                    );
                  })}
                </TreeNode>
              );
            })}
            {Object.keys(hierarchy).length === 0 && (
              <div style={{ padding: '8px', textAlign: 'center', opacity: 0.5, fontSize: '12px' }}>Sin resultados</div>
            )}
          </div>

          <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end', marginTop: '4px' }}>
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
      )}
    </div>
  );
};

// Subcomponente recursivo para manejar el UI del nodo
const TreeNode = ({ label, isChecked, isIndeterminate, onToggle, isLeaf, children }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', padding: '3px 0', gap: '6px' }}>
        {!isLeaf ? (
          <div onClick={() => setExpanded(!expanded)} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', width: '16px', justifyContent: 'center' }}>
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>
        ) : <div style={{ width: '16px' }} />}
        
        <div 
          onClick={onToggle}
          style={{ 
            width: '14px', height: '14px', border: '1px solid var(--border-color)', borderRadius: '3px',
            display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
            background: isChecked || isIndeterminate ? 'var(--primary-color)' : 'transparent',
            borderColor: isChecked || isIndeterminate ? 'var(--primary-color)' : 'var(--border-color)',
            flexShrink: 0
          }}
        >
          {isChecked && <Check size={10} color="white" />}
          {isIndeterminate && <Minus size={10} color="white" />}
        </div>
        
        <span style={{ cursor: 'pointer', userSelect: 'none' }} onClick={onToggle}>{label}</span>
      </div>
      
      {expanded && !isLeaf && (
        <div style={{ marginLeft: '22px', display: 'flex', flexDirection: 'column' }}>
          {children}
        </div>
      )}
    </div>
  );
};

export default ExcelDateFilter;
