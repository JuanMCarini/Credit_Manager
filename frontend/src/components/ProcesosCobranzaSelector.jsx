import React, { useState, useMemo } from 'react';
import { Search, X, ChevronDown, ChevronUp, Check, Calendar, Layers } from 'lucide-react';

const formatMoney = (amount) => {
  if (amount === undefined || amount === null || isNaN(amount)) return '$ 0,00';
  return '$ ' + new Intl.NumberFormat('es-AR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Number(amount));
};

const formatDate = (dateStr) => {
  if (!dateStr || dateStr === '-') return '-';
  const parts = dateStr.split('-');
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }
  return dateStr;
};

// Normalizes input date to YYYY-MM-DD
const normalizeDateInput = (val) => {
  if (!val) return '';
  const trimmed = String(val).trim();
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(trimmed)) {
    const [d, m, y] = trimmed.split('/');
    return `${y}-${m}-${d}`;
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return trimmed;
  }
  return trimmed;
};

// Robust 4-level fallback to resolve emission dates for any process
const getProcessEmissionDates = (p) => {
  let minDate = p["Fecha Emision Min"];
  let maxDate = p["Fecha Emision Max"];

  // 1. Try Fecha Emisión Cobranza
  if (!minDate || !maxDate) {
    const emis = p["Fecha Emisión Cobranza"];
    if (emis && emis !== '-') {
      if (emis.includes(' al ')) {
        const parts = emis.split(' al ');
        minDate = minDate || parts[0];
        maxDate = maxDate || parts[1];
      } else {
        minDate = minDate || emis;
        maxDate = maxDate || emis;
      }
    }
  }

  // 2. Try regex in Descripción (e.g. "2026-10-14.xlsx" or "2026-10")
  if (!minDate && p.Descripción) {
    const match = p.Descripción.match(/\b(20\d{2}-\d{2}-\d{2})\b/);
    if (match) {
      minDate = match[1];
      maxDate = match[1];
    } else {
      const matchMonth = p.Descripción.match(/\b(20\d{2}-\d{2})\b/);
      if (matchMonth) {
        minDate = `${matchMonth[1]}-01`;
        maxDate = `${matchMonth[1]}-28`;
      }
    }
  }

  // 3. Fallback to Fecha Ejecución
  if (!minDate && p["Fecha Ejecución"]) {
    const exec = p["Fecha Ejecución"].split(' ')[0];
    minDate = exec;
    maxDate = exec;
  }

  return { minDate: minDate || null, maxDate: maxDate || null };
};

const ProcesosCobranzaSelector = ({ 
  procesos = [], 
  selectedIds = [], 
  onChange, 
  placeholder = "Todos los procesos (Sin filtro - se procesarán todas las cobranzas pendientes)" 
}) => {
  // Start expanded by default so user immediately sees the list
  const [isExpanded, setIsExpanded] = useState(true);
  
  // External filters
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL'); // 'ALL', 'MASIVO_CSV', 'INDIVIDUAL'
  const [fechaEmisionDesde, setFechaEmisionDesde] = useState('');
  const [fechaEmisionHasta, setFechaEmisionHasta] = useState('');

  const normDesde = useMemo(() => normalizeDateInput(fechaEmisionDesde), [fechaEmisionDesde]);
  const normHasta = useMemo(() => normalizeDateInput(fechaEmisionHasta), [fechaEmisionHasta]);

  // Filter processes based on search term, type, and Fecha de Emisión de Cobranza
  const filteredProcesos = useMemo(() => {
    return procesos.filter(p => {
      // 1. Type filter
      if (typeFilter !== 'ALL' && p.Tipo !== typeFilter) {
        return false;
      }

      // 2. Fecha de Emisión de Cobranza filter (Desde / Hasta)
      const { minDate, maxDate } = getProcessEmissionDates(p);

      if (normDesde) {
        if (!maxDate || maxDate < normDesde) {
          return false;
        }
      }

      if (normHasta) {
        if (!minDate || minDate > normHasta) {
          return false;
        }
      }

      // 3. Search term (matches ID, tipo, descripción, fecha ejecución, or fecha emisión)
      if (!searchTerm.trim()) return true;
      const term = searchTerm.toLowerCase();

      const idMatch = String(p.ID).toLowerCase().includes(term);
      const tipoMatch = String(p.Tipo || '').toLowerCase().includes(term);
      const descMatch = String(p.Descripción || '').toLowerCase().includes(term);
      const fechaEjecMatch = String(p["Fecha Ejecución"] || '').toLowerCase().includes(term);
      const fechaEmisMatch = String(p["Fecha Emisión Cobranza"] || minDate || '').toLowerCase().includes(term);

      return idMatch || tipoMatch || descMatch || fechaEjecMatch || fechaEmisMatch;
    });
  }, [procesos, searchTerm, typeFilter, normDesde, normHasta]);

  // Counters for tabs
  const countMasivo = useMemo(() => procesos.filter(p => p.Tipo === 'MASIVO_CSV').length, [procesos]);
  const countIndiv = useMemo(() => procesos.filter(p => p.Tipo === 'INDIVIDUAL').length, [procesos]);

  const toggleOption = (id) => {
    let next;
    if (selectedIds.includes(id)) {
      next = selectedIds.filter(val => val !== id);
    } else {
      next = [...selectedIds, id];
    }
    onChange(next);
  };

  const handleSelectAllVisible = () => {
    const visibleIds = filteredProcesos.map(p => p.ID);
    const combined = [...new Set([...selectedIds, ...visibleIds])];
    onChange(combined);
  };

  const handleClearAll = () => {
    onChange([]);
  };

  const handleClearDateFilter = () => {
    setFechaEmisionDesde('');
    setFechaEmisionHasta('');
  };

  const selectedCount = selectedIds.length;
  const hasDateFilter = Boolean(normDesde || normHasta);

  // Selected processes full objects for chips
  const selectedProcessObjects = useMemo(() => {
    const map = new Map(procesos.map(p => [p.ID, p]));
    return selectedIds.map(id => map.get(id) || { ID: id, Descripción: `Proceso #${id}` });
  }, [procesos, selectedIds]);

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      
      {/* ─────────────────────────────────────────────────────────────
          1. FILTROS EXTERNOS (Siempre visibles fuera de la lista)
          ───────────────────────────────────────────────────────────── */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.45)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '8px',
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        {/* Row 1: Buscador de texto & Tipo de Proceso */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          
          {/* Buscador */}
          <div style={{ position: 'relative', flex: '1 1 240px', minWidth: '220px' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Buscar por ID, archivo o descripción..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                padding: '7px 28px 7px 30px',
                fontSize: '12.5px',
                background: 'rgba(0, 0, 0, 0.25)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '6px',
                color: 'var(--text-primary)',
                outline: 'none'
              }}
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                style={{
                  position: 'absolute',
                  right: '8px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center'
                }}
              >
                <X size={13} />
              </button>
            )}
          </div>

          {/* Tipo de Proceso Tabs */}
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginRight: '4px' }}>Tipo:</span>
            {[
              { id: 'ALL', label: `Todos (${procesos.length})` },
              { id: 'MASIVO_CSV', label: `Masivos (${countMasivo})` },
              { id: 'INDIVIDUAL', label: `Individuales (${countIndiv})` }
            ].map(tab => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setTypeFilter(tab.id)}
                style={{
                  padding: '4px 9px',
                  fontSize: '11.5px',
                  borderRadius: '5px',
                  border: typeFilter === tab.id ? '1px solid var(--accent-primary)' : '1px solid rgba(255, 255, 255, 0.08)',
                  background: typeFilter === tab.id ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                  color: typeFilter === tab.id ? '#60a5fa' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontWeight: typeFilter === tab.id ? 600 : 400,
                  transition: 'all 0.15s ease'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: Filtro por Fecha de Emisión de Cobranza & Acciones de selección */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          
          {/* Fecha Emisión Cobranza Desde / Hasta */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            flexWrap: 'wrap',
            background: hasDateFilter ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255, 255, 255, 0.02)',
            border: hasDateFilter ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(255, 255, 255, 0.06)',
            borderRadius: '6px',
            padding: '4px 10px'
          }}>
            <Calendar size={13} style={{ color: hasDateFilter ? '#10b981' : 'var(--text-muted)' }} />
            <span style={{ fontSize: '11.5px', color: hasDateFilter ? '#10b981' : 'var(--text-secondary)', fontWeight: 500 }}>
              Fecha Emisión Cobranza:
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Desde:</span>
              <input
                type="date"
                value={fechaEmisionDesde}
                onChange={(e) => setFechaEmisionDesde(e.target.value)}
                style={{
                  background: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '4px',
                  color: 'var(--text-primary)',
                  fontSize: '11.5px',
                  padding: '3px 6px',
                  width: '125px'
                }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Hasta:</span>
              <input
                type="date"
                value={fechaEmisionHasta}
                onChange={(e) => setFechaEmisionHasta(e.target.value)}
                style={{
                  background: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '4px',
                  color: 'var(--text-primary)',
                  fontSize: '11.5px',
                  padding: '3px 6px',
                  width: '125px'
                }}
              />
            </div>
            {hasDateFilter && (
              <button
                type="button"
                onClick={handleClearDateFilter}
                title="Quitar filtro de fechas de emisión"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#f87171',
                  cursor: 'pointer',
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '2px',
                  padding: '2px 4px'
                }}
              >
                <X size={12} /> Limpiar fecha
              </button>
            )}
          </div>

          {/* Quick selection actions */}
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
              ({filteredProcesos.length} visible{filteredProcesos.length !== 1 ? 's' : ''})
            </span>
            <button
              type="button"
              onClick={handleSelectAllVisible}
              style={{
                background: 'rgba(59, 130, 246, 0.12)',
                border: '1px solid rgba(59, 130, 246, 0.25)',
                borderRadius: '4px',
                color: '#60a5fa',
                fontSize: '11.5px',
                padding: '4px 10px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: 500
              }}
            >
              <Check size={12} /> Marcar todos los visibles
            </button>
            {selectedCount > 0 && (
              <button
                type="button"
                onClick={handleClearAll}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#f87171',
                  fontSize: '11.5px',
                  cursor: 'pointer',
                  textDecoration: 'underline'
                }}
              >
                Deseleccionar todos
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          2. CABECERA DE CONTROL DE LISTA (Barra de estado / Toggle)
          ───────────────────────────────────────────────────────────── */}
      <div
        onClick={() => setIsExpanded(prev => !prev)}
        style={{
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'rgba(15, 23, 42, 0.65)',
          border: isExpanded ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
          borderRadius: isExpanded ? '8px 8px 0 0' : '8px',
          padding: '10px 14px',
          minHeight: '44px',
          transition: 'all 0.2s ease',
          boxShadow: isExpanded ? '0 0 0 1px var(--accent-glow)' : 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden', flex: 1, marginRight: '8px' }}>
          <Layers size={16} style={{ color: selectedCount > 0 ? 'var(--accent-primary)' : 'var(--text-muted)', flexShrink: 0 }} />
          {selectedCount === 0 ? (
            <span style={{ color: 'var(--text-secondary)', fontSize: '13.5px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {filteredProcesos.length === procesos.length
                ? placeholder
                : `Todos los procesos filtrados (${filteredProcesos.length} disponibles) - Clic para ver / ocultar`}
            </span>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'nowrap' }}>
              <span style={{
                background: 'rgba(59, 130, 246, 0.2)',
                color: '#60a5fa',
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '12px',
                fontWeight: 600,
                whiteSpace: 'nowrap'
              }}>
                {selectedCount} proceso{selectedCount > 1 ? 's' : ''} seleccionado{selectedCount > 1 ? 's' : ''}
              </span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                ({selectedIds.map(id => `#${id}`).slice(0, 5).join(', ')}{selectedIds.length > 5 ? ` +${selectedIds.length - 5}` : ''})
              </span>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          {selectedCount > 0 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                handleClearAll();
              }}
              title="Quitar todos los procesos seleccionados"
              style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: 'none',
                color: '#f87171',
                borderRadius: '50%',
                width: '20px',
                height: '20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                padding: 0
              }}
            >
              <X size={12} />
            </button>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <span>{isExpanded ? 'Ocultar listado' : 'Ver listado'}</span>
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          3. LISTADO EXPANDIDO INTEGRADO (Sin popovers flotantes)
          ───────────────────────────────────────────────────────────── */}
      {isExpanded && (
        <div style={{
          background: '#161b22',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderTop: 'none',
          borderRadius: '0 0 8px 8px',
          maxHeight: '280px',
          overflowY: 'auto',
          boxShadow: '0 8px 20px rgba(0, 0, 0, 0.4)'
        }}>
          {filteredProcesos.length === 0 ? (
            <div style={{ padding: '28px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No se encontraron procesos que coincidan con los filtros aplicados arriba.
              {hasDateFilter && (
                <div style={{ marginTop: '8px' }}>
                  <button
                    type="button"
                    onClick={handleClearDateFilter}
                    style={{
                      background: 'rgba(59, 130, 246, 0.15)',
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                      color: '#60a5fa',
                      borderRadius: '4px',
                      padding: '4px 10px',
                      fontSize: '11.5px',
                      cursor: 'pointer'
                    }}
                  >
                    Limpiar filtro de fechas de emisión
                  </button>
                </div>
              )}
            </div>
          ) : (
            filteredProcesos.map(p => {
              const isSelected = selectedIds.includes(p.ID);
              const isMasivo = p.Tipo === 'MASIVO_CSV';
              const hasTotal = p.Total !== undefined && p.Total !== null && Number(p.Total) > 0;
              const { minDate } = getProcessEmissionDates(p);
              const fechaEmisionDisplay = p["Fecha Emisión Cobranza"] || minDate;

              return (
                <div
                  key={p.ID}
                  onClick={() => toggleOption(p.ID)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 14px',
                    cursor: 'pointer',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                    background: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
                    borderLeft: isSelected ? '3px solid #3b82f6' : '3px solid transparent',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  {/* Left: Checkbox, Badges, Description */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: 0, marginRight: '12px' }}>
                    {/* Checkbox */}
                    <div style={{
                      width: '17px',
                      height: '17px',
                      borderRadius: '4px',
                      border: isSelected ? '1px solid #3b82f6' : '1px solid rgba(255, 255, 255, 0.3)',
                      background: isSelected ? '#3b82f6' : 'rgba(0, 0, 0, 0.2)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0
                    }}>
                      {isSelected && <Check size={12} color="white" strokeWidth={3} />}
                    </div>

                    {/* Process ID Badge */}
                    <span style={{
                      background: 'rgba(59, 130, 246, 0.18)',
                      color: '#93c5fd',
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                      borderRadius: '4px',
                      padding: '1px 6px',
                      fontSize: '11px',
                      fontWeight: 700,
                      fontFamily: 'monospace',
                      flexShrink: 0
                    }}>
                      #{p.ID}
                    </span>

                    {/* Process Type Badge */}
                    <span style={{
                      background: isMasivo ? 'rgba(168, 85, 247, 0.18)' : 'rgba(20, 184, 166, 0.18)',
                      color: isMasivo ? '#d8b4fe' : '#5eead4',
                      border: isMasivo ? '1px solid rgba(168, 85, 247, 0.3)' : '1px solid rgba(20, 184, 166, 0.3)',
                      borderRadius: '4px',
                      padding: '1px 6px',
                      fontSize: '10.5px',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      flexShrink: 0
                    }}>
                      {isMasivo ? 'MASIVO' : p.Tipo}
                    </span>

                    {/* Description / Filename */}
                    <span style={{
                      color: isSelected ? '#ffffff' : 'var(--text-primary)',
                      fontSize: '13px',
                      fontWeight: isSelected ? 600 : 400,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {p.Descripción || 'Sin descripción'}
                    </span>
                  </div>

                  {/* Right: Fecha Emisión Cobranza, Total, Fecha Ejecución */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexShrink: 0, fontSize: '11.5px' }}>
                    {/* Fecha Emisión Cobranza Badge */}
                    {fechaEmisionDisplay && fechaEmisionDisplay !== '-' && (
                      <span 
                        title="Fecha de Emisión de Cobranza (del pago)"
                        style={{
                          background: 'rgba(16, 185, 129, 0.15)',
                          color: '#34d399',
                          border: '1px solid rgba(16, 185, 129, 0.3)',
                          borderRadius: '4px',
                          padding: '2px 6px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontWeight: 500,
                          whiteSpace: 'nowrap'
                        }}
                      >
                        <Calendar size={11} />
                        Cob: {formatDate(fechaEmisionDisplay)}
                      </span>
                    )}

                    {/* Total recaudado */}
                    {hasTotal && (
                      <span style={{ color: '#10b981', fontWeight: 600, fontFamily: 'monospace', minWidth: '85px', textAlign: 'right' }}>
                        {formatMoney(p.Total)}
                      </span>
                    )}

                    {/* Fecha de Ingesta / Ejecución */}
                    <span 
                      title={`Fecha y hora de importación: ${p["Fecha Ejecución"]}`}
                      style={{ color: 'var(--text-muted)', fontSize: '11px', whiteSpace: 'nowrap' }}
                    >
                      {p["Fecha Ejecución"] ? p["Fecha Ejecución"].split(' ')[0] : '-'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Selected Chips Area (Under trigger / list) */}
      {selectedCount > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '2px', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Seleccionados ({selectedCount}):
          </span>
          {selectedProcessObjects.map(p => {
            const { minDate } = getProcessEmissionDates(p);
            const emision = p["Fecha Emisión Cobranza"] || minDate;
            return (
              <span
                key={p.ID}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  background: 'rgba(30, 41, 59, 0.8)',
                  border: '1px solid rgba(59, 130, 246, 0.3)',
                  borderRadius: '6px',
                  padding: '3px 8px',
                  fontSize: '12px',
                  color: 'var(--text-primary)'
                }}
              >
                <span style={{ fontWeight: 600, color: '#60a5fa' }}>#{p.ID}</span>
                <span style={{ maxWidth: '180px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {p.Descripción || 'Sin descripción'}
                </span>
                {emision && emision !== '-' && (
                  <span style={{ fontSize: '10.5px', color: '#34d399', opacity: 0.9 }}>
                    ({formatDate(emision)})
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => toggleOption(p.ID)}
                  title="Quitar este proceso"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '1px',
                    borderRadius: '3px'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.color = '#ef4444'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                >
                  <X size={12} />
                </button>
              </span>
            );
          })}
          <button
            type="button"
            onClick={handleClearAll}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#ef4444',
              fontSize: '11px',
              cursor: 'pointer',
              textDecoration: 'underline',
              padding: '2px 4px'
            }}
          >
            Limpiar selección
          </button>
        </div>
      )}
    </div>
  );
};

export default ProcesosCobranzaSelector;
