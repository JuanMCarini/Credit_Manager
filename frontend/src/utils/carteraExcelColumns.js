// Configuración de encabezados y formateadores para exportaciones a Excel de Carteras

// Función para convertir fechas (string, Date) en celda nativa de fecha de Excel
// Excel almacena las fechas como número de serie (días desde 1899-12-30) con formato 'dd/mm/yyyy'.
export const toExcelDateCell = (value, defaultFormat = 'dd/mm/yyyy') => {
  if (value === undefined || value === null || value === '' || value === '-') {
    return '';
  }

  let y, m, d;
  let isMonthOnly = false;

  if (value instanceof Date) {
    if (isNaN(value.getTime())) return '';
    y = value.getFullYear();
    m = value.getMonth() + 1;
    d = value.getDate();
  } else if (typeof value === 'string') {
    const trimmed = value.trim();
    if (trimmed === '' || trimmed === '-') return '';

    // Formato ISO: YYYY-MM-DD o YYYY-MM-DDTHH:mm:ss o con espacio
    const isoDateMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (isoDateMatch) {
      y = Number(isoDateMatch[1]);
      m = Number(isoDateMatch[2]);
      d = Number(isoDateMatch[3]);
    } else {
      // Formato YYYY-MM (ej. "2026-07")
      const ymMatch = trimmed.match(/^(\d{4})-(\d{2})$/);
      if (ymMatch) {
        y = Number(ymMatch[1]);
        m = Number(ymMatch[2]);
        d = 1;
        isMonthOnly = true;
      } else {
        // Formato DD/MM/YYYY
        const dmyMatch = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
        if (dmyMatch) {
          d = Number(dmyMatch[1]);
          m = Number(dmyMatch[2]);
          y = Number(dmyMatch[3]);
        } else {
          // Formato MM/YYYY
          const myMatch = trimmed.match(/^(\d{1,2})\/(\d{4})$/);
          if (myMatch) {
            d = 1;
            m = Number(myMatch[1]);
            y = Number(myMatch[2]);
            isMonthOnly = true;
          }
        }
      }
    }
  }

  if (y && m && d && !isNaN(y) && !isNaN(m) && !isNaN(d) && y > 1900 && m >= 1 && m <= 12 && d >= 1 && d <= 31) {
    const epoch = Date.UTC(1899, 11, 30);
    const target = Date.UTC(y, m - 1, d);
    const serial = Math.round((target - epoch) / 86400000);
    const numFmt = isMonthOnly ? 'mm/yyyy' : defaultFormat;
    return { t: 'n', v: serial, z: numFmt };
  }

  return value;
};

// Formateador general para celdas de Excel (fechas, números, strings)
export const formatExcelValue = (value) => {
  if (value === undefined || value === null) return '';
  if (typeof value === 'number' || typeof value === 'boolean') return value;

  // Si ya es un objeto celda de Excel ({ t: 'n', v: ..., z: ... }), retornarlo directo
  if (typeof value === 'object' && value !== null && value.t !== undefined && value.v !== undefined) {
    return value;
  }

  // Verificar si es una fecha (ISO, Date, DD/MM/YYYY, etc.)
  const dateCell = toExcelDateCell(value);
  if (dateCell && typeof dateCell === 'object' && dateCell.t === 'n') {
    return dateCell;
  }

  if (typeof value === 'string') {
    const strVal = value.trim();
    if (strVal === '-' || strVal === '') return '';

    // Regex para números (enteros o decimales)
    const numRegex = /^-?\d+(\.\d+)?$/;
    if (numRegex.test(strVal)) {
      if (strVal.length > 1 && strVal.startsWith('0') && !strVal.startsWith('0.')) {
        return strVal;
      } else if (strVal.length > 15) {
        return strVal;
      } else {
        return Number(strVal);
      }
    }
    return strVal;
  }

  return value;
};

export const CARTERAS_EXPORT_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'nombre', label: 'Nombre de Cartera' },
  { key: 'tipo_operacion', label: 'Tipo de Operación' },
  { key: 'estado', label: 'Estado' },
  { key: 'socio', label: 'Socio Comercial' },
  { key: 'fecha_compra', label: 'Fecha de Operación' },
  { key: 'tna_descuento', label: 'TNA Descuento (%)', format: val => val != null ? `${Number(val).toFixed(2)}%` : '' },
  { key: 'recurso', label: 'Con Recurso', format: val => val ? 'Sí' : 'No' },
  { key: 'iva', label: 'Aplica IVA', format: val => val ? 'Sí' : 'No' },
  { key: 'tiene_contrato_firmado', label: 'Contrato Firmado', format: val => val ? 'Sí' : 'No' },
];

export const COLUMNS_PREVIEW_CREDITOS_VENTA = [
  { key: 'id', label: 'ID Crédito' },
  { key: 'cliente', label: 'Cliente' },
  { key: 'fecha_emision', label: 'Fecha de Emisión' },
  { key: 'estado', label: 'Estado' },
  { key: 'monto_otorgado', label: 'Monto Otorgado' },
  { key: 'total_cuotas', label: 'Total Cuotas' },
  { key: 'cuotas_a_ceder', label: 'Cuotas a Ceder' },
  { key: 'valor_actual', label: 'Valor Actual' },
];

export const COLUMNS_PREVIEW_CREDITOS_COMPRA = [
  { key: 'id_externo', label: 'ID Externo' },
  { key: 'cliente_nombre', label: 'Cliente' },
  { key: 'fecha_emision', label: 'Fecha de Emisión' },
  { key: 'capital_vendido', label: 'Capital Vendido' },
  { key: 'plazo', label: 'Plazo' },
  { key: 'cuotas_compradas', label: 'Cuotas Adquiridas' },
  { key: 'valor_actual', label: 'Valor Actual' },
];

export const COLUMNS_PREVIEW_CUOTAS_VENTA = [
  { key: 'credito_id', label: 'ID Crédito' },
  { key: 'nro_cuota', label: 'Nro. Cuota' },
  { key: 'fecha_vencimiento', label: 'Fecha Vencimiento' },
  { key: 'capital', label: 'Capital' },
  { key: 'interes', label: 'Interés' },
  { key: 'iva', label: 'IVA' },
  { key: 'total_cuota', label: 'Total Cuota' },
  { key: 'valor_actual', label: 'Valor Actual' },
  { key: 'incluida', label: 'Incluida en Operación', format: val => (val === true || val === 'Sí' || val === 'SI') ? 'Sí' : 'No' },
];

export const COLUMNS_PREVIEW_CUOTAS_COMPRA = [
  { key: 'credito_id_externo', label: 'ID Crédito Externo' },
  { key: 'nro_cuota', label: 'Nro. Cuota' },
  { key: 'fecha_vencimiento', label: 'Fecha Vencimiento' },
  { key: 'fecha_vencimiento_pago', label: 'Fecha Vto. Pago' },
  { key: 'capital', label: 'Capital' },
  { key: 'interes', label: 'Interés' },
  { key: 'iva', label: 'IVA' },
  { key: 'total', label: 'Total Cuota' },
  { key: 'valor_actual', label: 'Valor Actual' },
  { key: 'comprada', label: 'Comprada', format: val => (val === true || val === 'Sí' || val === 'SI') ? 'Sí' : 'No' },
];

export const COLUMNS_PREVIEW_RESUMEN_VENTA = [
  { key: 'fecha_vencimiento', label: 'Mes Vencimiento' },
  { key: 'cantidad', label: 'Cantidad de Cuotas' },
  { key: 'capital', label: 'Capital Total' },
  { key: 'interes', label: 'Interés Total' },
  { key: 'iva', label: 'IVA Total' },
  { key: 'total_cuota', label: 'Monto Total' },
  { key: 'valor_actual', label: 'Valor Actual' },
];

export const COLUMNS_PREVIEW_RESUMEN_COMPRA = [
  { key: 'mes', label: 'Mes Vencimiento' },
  { key: 'cantidad_cuotas', label: 'Cantidad de Cuotas' },
  { key: 'capital_total', label: 'Capital Total' },
  { key: 'interes_total', label: 'Interés Total' },
  { key: 'iva_total', label: 'IVA Total' },
  { key: 'monto_total', label: 'Monto Total' },
  { key: 'valor_actual', label: 'Valor Actual' },
];
