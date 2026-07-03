import React, { useState, useEffect } from 'react';
import useAppStore from '../store/useAppStore';
import CurrencyInput from './CurrencyInput';

const ClientForm = ({ initialData, onSubmit, loading, feedback, buttonText = "Guardar Cliente" }) => {
  const { provincias, empleadores } = useAppStore();

  const [form, setForm] = useState({
    cuil: '',
    documento: '',
    nombre: '',
    apellido: '',
    fecha_nacimiento: '',
    sexo: '',
    estado_civil: '',
    nacionalidad: '',
    telefono: '',
    telefono_2: '',
    mail: '',
    calle: '',
    calle_nro: '',
    piso: '',
    depto: '',
    localidad: '',
    id_codigo_postal: '',
    id_provincia: '',
    fecha_ingreso: '',
    remuneracion: 0,
    legajo: '',
    empleador_id: '',
    cbu: '',
    estado: 'ACTIVO',
    ...initialData
  });

  useEffect(() => {
    if (initialData) {
      setForm((prev) => ({ ...prev, ...initialData }));
    }
  }, [initialData]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'mail') {
      setForm({ ...form, [name]: value.toLowerCase() });
    } else {
      setForm({ ...form, [name]: value.toUpperCase() });
    }
  };

  const [localError, setLocalError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setLocalError('');

    const docClean = form.documento.replace(/\D/g, '');
    const cuilClean = form.cuil.replace(/\D/g, '');

    if (docClean && cuilClean && !cuilClean.includes(docClean)) {
      setLocalError('El Documento (DNI) no coincide con el CUIL.');
      return;
    }

    onSubmit(form);
  };

  return (
    <form onSubmit={handleSubmit}>
      <h3 style={{ marginBottom: '12px', fontFamily: 'var(--font-heading)', fontSize: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
        Datos Personales
      </h3>
      <div className="form-row">
        <div className="form-group"><label>CUIL (Sin guiones) *</label><input type="text" name="cuil" value={form.cuil || ''} onChange={handleChange} maxLength="11" required disabled={!!initialData?.cuil} /></div>
        <div className="form-group"><label>Documento (DNI) *</label><input type="text" name="documento" value={form.documento || ''} onChange={handleChange} maxLength="10" required /></div>
        <div className="form-group"><label>Nombre *</label><input type="text" name="nombre" value={form.nombre || ''} onChange={handleChange} required /></div>
        <div className="form-group"><label>Apellido *</label><input type="text" name="apellido" value={form.apellido || ''} onChange={handleChange} required /></div>
      </div>
      <div className="form-row">
        <div className="form-group"><label>Fecha Nacimiento</label><input type="date" name="fecha_nacimiento" value={form.fecha_nacimiento || ''} onChange={handleChange} /></div>
        <div className="form-group">
          <label>Sexo</label>
          <select name="sexo" value={form.sexo || ''} onChange={handleChange}>
            <option value="">Seleccione</option>
            <option value="M">Masculino</option>
            <option value="F">Femenino</option>
            <option value="O">Otro</option>
          </select>
        </div>
        <div className="form-group">
          <label>Estado Civil</label>
          <select name="estado_civil" value={form.estado_civil || ''} onChange={handleChange}>
            <option value="">Seleccione</option>
            <option value="Soltero/a">Soltero/a</option>
            <option value="Casado/a">Casado/a</option>
            <option value="Divorciado/a">Divorciado/a</option>
            <option value="Viudo/a">Viudo/a</option>
            <option value="Unión Convivencial">Unión Convivencial</option>
          </select>
        </div>
        <div className="form-group"><label>Nacionalidad</label><input type="text" name="nacionalidad" value={form.nacionalidad || ''} onChange={handleChange} /></div>
      </div>

      <h3 style={{ marginTop: '24px', marginBottom: '12px', fontFamily: 'var(--font-heading)', fontSize: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
        Contacto y Domicilio
      </h3>
      <div className="form-row">
        <div className="form-group"><label>Teléfono Principal</label><input type="text" name="telefono" value={form.telefono || ''} onChange={handleChange} /></div>
        <div className="form-group"><label>Teléfono Secundario</label><input type="text" name="telefono_2" value={form.telefono_2 || ''} onChange={handleChange} /></div>
        <div className="form-group"><label>Email</label><input type="email" name="mail" value={form.mail || ''} onChange={handleChange} /></div>
      </div>
      <div className="form-row">
        <div className="form-group" style={{ flex: 2 }}><label>Calle</label><input type="text" name="calle" value={form.calle || ''} onChange={handleChange} /></div>
        <div className="form-group"><label>Nro</label><input type="number" name="calle_nro" value={form.calle_nro || ''} onChange={handleChange} /></div>
        <div className="form-group"><label>Piso</label><input type="text" name="piso" value={form.piso || ''} onChange={handleChange} /></div>
        <div className="form-group"><label>Depto</label><input type="text" name="depto" value={form.depto || ''} onChange={handleChange} /></div>
      </div>
      <div className="form-row">
        <div className="form-group"><label>Localidad</label><input type="text" name="localidad" value={form.localidad || ''} onChange={handleChange} /></div>
        <div className="form-group"><label>Código Postal</label><input type="text" name="id_codigo_postal" value={form.id_codigo_postal || ''} onChange={handleChange} /></div>
        <div className="form-group">
          <label>Provincia</label>
          <select name="id_provincia" value={form.id_provincia || ''} onChange={handleChange}>
            <option value="">(Opcional)</option>
            {provincias.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </div>
      </div>

      <h3 style={{ marginTop: '24px', marginBottom: '12px', fontFamily: 'var(--font-heading)', fontSize: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
        Laboral y Financiero
      </h3>
      <div className="form-row">
        <div className="form-group"><label>Fecha Ingreso</label><input type="date" name="fecha_ingreso" value={form.fecha_ingreso || ''} onChange={handleChange} /></div>
        <div className="form-group">
          <label>Remuneración Declarada ($)</label>
          <CurrencyInput
            value={form.remuneracion}
            onChange={(val) => setForm({ ...form, remuneracion: val })}
          />
        </div>
        <div className="form-group"><label>Nro. Legajo Laboral</label><input type="text" name="legajo" value={form.legajo || ''} onChange={handleChange} /></div>
        <div className="form-group">
          <label>Empleador</label>
          <select name="empleador_id" value={form.empleador_id || ''} onChange={handleChange}>
            <option value="">(Opcional)</option>
            {empleadores.map(e => <option key={e.id} value={e.id}>{e.razon_social} {e.cuit && `(CUIT: ${e.cuit})`}</option>)}
          </select>
        </div>
        <div className="form-group"><label>CBU / CVU Bancario</label><input type="text" name="cbu" value={form.cbu || ''} onChange={handleChange} maxLength="22" /></div>

        {initialData && (
          <div className="form-group">
            <label>Estado</label>
            <select name="estado" value={form.estado || 'ACTIVO'} onChange={handleChange}>
              <option value="ACTIVO">ACTIVO</option>
              <option value="INACTIVO">INACTIVO</option>
              <option value="MOROSO">MOROSO</option>
              <option value="INCOBRABLE">INCOBRABLE</option>
            </select>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '24px' }}>
        <div style={{ fontSize: '14px', fontWeight: 500, color: (localError || feedback?.type === 'error') ? 'var(--error)' : 'var(--accent-secondary)' }}>
          {localError || feedback?.message || ''}
        </div>
        <div>
          <button type="submit" className="btn-primary" disabled={loading} style={{ minWidth: '200px' }}>
            {loading ? "Guardando..." : buttonText}
          </button>
        </div>
      </div>
    </form>
  );
};

export default ClientForm;
