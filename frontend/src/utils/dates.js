export const getLocalDateISO = (d = new Date()) => {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export const getLocalMonthISO = (d = new Date()) => {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
};

export const parseLocalDate = (dateStr) => {
  if (!dateStr) return new Date(NaN);
  if (dateStr instanceof Date) return dateStr;
  const str = String(dateStr).split('T')[0];
  const parts = str.split('-');
  if (parts.length === 3) {
    const [y, m, d] = parts.map(Number);
    return new Date(y, m - 1, d);
  }
  return new Date(dateStr);
};
