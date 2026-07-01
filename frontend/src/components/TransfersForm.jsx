import React, { useState } from 'react';
import CurrencyInput from './CurrencyInput';

const formatCurrency = (value) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value);
};

const TransfersForm = ({ transfers, onChange, totalRequired }) => {
  const [newTransfer, setNewTransfer] = useState({
    cbu: '',
    monto: '',
    cuit: '',
    razon_social: ''
  });

  const currentTotal = transfers.reduce((sum, t) => sum + parseFloat(t.monto || 0), 0);
  const remaining = totalRequired - currentTotal;

  const handleAddTransfer = () => {
    if (!newTransfer.cbu || !newTransfer.monto || !newTransfer.cuit || !newTransfer.razon_social) {
      alert("Por favor complete todos los campos de la transferencia.");
      return;
    }
    
    const montoFloat = parseFloat(newTransfer.monto);
    if (montoFloat <= 0) {
      alert("El monto debe ser mayor a 0.");
      return;
    }

    let updatedTransfers = [...transfers];
    if (updatedTransfers.length > 0) {
      // La primera transferencia actúa como el saldo restante del cliente
      if (montoFloat > updatedTransfers[0].monto + 0.01) {
        alert("El monto supera el disponible en la transferencia principal del cliente.");
        return;
      }
      updatedTransfers[0].monto -= montoFloat;
    } else {
      if (montoFloat > remaining + 0.01) {
        alert("El monto supera el capital restante a transferir.");
        return;
      }
    }

    updatedTransfers.push({ ...newTransfer, monto: montoFloat });
    onChange(updatedTransfers);
    setNewTransfer({ cbu: '', monto: '', cuit: '', razon_social: '' });
  };

  const handleRemoveTransfer = (index) => {
    const updated = [...transfers];
    const removed = updated.splice(index, 1)[0];
    
    // Si eliminamos una transferencia secundaria, le sumamos el monto a la primera
    if (index > 0 && updated.length > 0) {
      updated[0].monto += parseFloat(removed.monto);
    }
    
    onChange(updated);
  };

  return (
    <div className="transfers-form" style={{ marginTop: '20px' }}>
      <h4 style={{ fontFamily: 'var(--font-heading)', fontSize: '16px', marginBottom: '16px' }}>
        Detalle de Transferencias
      </h4>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', padding: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
        <div><strong>Capital del Crédito:</strong> {formatCurrency(totalRequired)}</div>
        <div style={{ color: transfers.length > 0 && transfers[0].monto > 0 ? 'var(--success-color, #2ecc71)' : 'var(--text-color, #e0e0e0)' }}>
          <strong>Neto al Cliente:</strong> {transfers.length > 0 ? formatCurrency(transfers[0].monto) : formatCurrency(0)}
        </div>
        <div>
          <strong>Terceros:</strong> {formatCurrency(currentTotal - (transfers.length > 0 ? transfers[0].monto : 0))}
        </div>
      </div>

      {transfers.length > 0 && (
        <div className="table-responsive" style={{ marginBottom: '20px' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>CBU/CVU</th>
                <th>CUIT</th>
                <th>Razón Social</th>
                <th>Monto</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {transfers.map((t, index) => (
                <tr key={index}>
                  <td>{t.cbu}</td>
                  <td>{t.cuit}</td>
                  <td>{t.razon_social}</td>
                  <td>{formatCurrency(t.monto)}</td>
                  <td>
                    {index > 0 && (
                      <button 
                        type="button" 
                        className="btn-secondary" 
                        style={{ padding: '4px 8px', fontSize: '12px' }}
                        onClick={() => handleRemoveTransfer(index)}
                      >
                        Eliminar
                      </button>
                    )}
                    {index === 0 && (
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Titular</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(transfers.length === 0 || transfers[0].monto > 0.01) && (
        <div className="glass-panel" style={{ padding: '16px' }}>
          <h5 style={{ marginBottom: '12px', fontSize: '14px' }}>Agregar Transferencia a Terceros</h5>
          <div className="form-row">
            <div className="form-group">
              <label>CBU / CVU *</label>
              <input 
                type="text" 
                maxLength="22"
                value={newTransfer.cbu} 
                onChange={(e) => setNewTransfer({...newTransfer, cbu: e.target.value})} 
                placeholder="22 dígitos"
              />
            </div>
            <div className="form-group">
              <label>CUIT *</label>
              <input 
                type="text" 
                maxLength="11"
                value={newTransfer.cuit} 
                onChange={(e) => setNewTransfer({...newTransfer, cuit: e.target.value})} 
                placeholder="Sin guiones"
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Razón Social / Titular *</label>
              <input 
                type="text" 
                value={newTransfer.razon_social} 
                onChange={(e) => setNewTransfer({...newTransfer, razon_social: e.target.value})} 
              />
            </div>
            <div className="form-group">
              <label>Monto *</label>
              <CurrencyInput 
                value={newTransfer.monto} 
                onChange={(val) => setNewTransfer({...newTransfer, monto: val})} 
                placeholder="0,00"
              />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
            <button 
              type="button" 
              className="btn-secondary" 
              onClick={handleAddTransfer}
            >
              + Agregar Transferencia
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TransfersForm;
