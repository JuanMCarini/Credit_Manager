import React, { useState, useEffect } from 'react';

const CurrencyInput = ({ value, onChange, name, className, placeholder, required, disabled, readOnly, style }) => {
  const [displayValue, setDisplayValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const formatCurrency = (val) => {
    if (val === '' || val === null || val === undefined) return '';
    const parsed = parseFloat(String(val).replace(',', '.'));
    if (isNaN(parsed)) return val;
    return '$ ' + new Intl.NumberFormat('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(parsed);
  };

  useEffect(() => {
    if (!isFocused) {
      if (value === '' || value === null || value === undefined) {
        setDisplayValue('');
      } else {
        setDisplayValue(formatCurrency(value));
      }
    }
  }, [value, isFocused]);

  const handleFocus = () => {
    setIsFocused(true);
    if (value !== '' && value !== null && value !== undefined) {
      // Remove thousands separators and use comma for decimals during editing
      const editValue = String(value).replace('.', ',');
      setDisplayValue(editValue);
    }
  };

  const handleBlur = () => {
    setIsFocused(false);
    // On blur, the formatting will automatically be applied by the useEffect
    // but we can also eagerly do it here
    setDisplayValue(formatCurrency(value));
  };

  const handleChange = (e) => {
    let raw = e.target.value;
    
    // Convert all dots to commas to unify decimal separator while editing
    raw = raw.replace(/\./g, ',');
    
    // Keep only digits and commas
    let filtered = raw.replace(/[^\d,]/g, '');
    
    // Ensure at most one comma
    const parts = filtered.split(',');
    if (parts.length > 2) {
      filtered = parts[0] + ',' + parts.slice(1).join('');
    }
    
    setDisplayValue(filtered);
    
    // Pass standard float string to parent
    const floatStr = filtered.replace(',', '.');
    
    if (onChange) {
      onChange(floatStr, {
        target: {
          name: name,
          value: floatStr
        }
      });
    }
  };

  return (
    <input
      type="text"
      name={name}
      className={className || "form-control"}
      value={displayValue}
      onChange={handleChange}
      onFocus={handleFocus}
      onBlur={handleBlur}
      placeholder={placeholder || "$ 0,00"}
      required={required}
      disabled={disabled}
      readOnly={readOnly}
      style={{ textAlign: 'right', ...style }}
    />
  );
};

export default CurrencyInput;
