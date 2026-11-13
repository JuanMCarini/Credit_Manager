import { useState, useEffect, useCallback, useMemo } from 'react';
import axiosClient, { downloadFile } from '../api/axiosClient';
import ExportExcelButton from '../components/ExportExcelButton';
import CurrencyInput from '../components/CurrencyInput';
import { getLocalDateISO } from '../utils/dates';
import {
  FileText,
  Plus,
  Download,
  Search,
  Calendar,
  Building2,
  CheckCircle2,
  AlertCircle,
  X,
  Trash2,
  RotateCcw,
  Receipt,
} from 'lucide-react';

const CONDICIONES_IVA = [
  'Responsable Inscripto',
  'Consumidor Final',
  'Monotributista',
  'IVA Exento',
  'Sujeto No Categorizado',
  'Cliente del Exterior',
];

const ALICUOTAS_IVA = [
  { value: '21', label: '21%' },
  { value: '10.5', label: '10.5%' },
  { value: '27', label: '27%' },
  { value: '0', label: '0%' },
  { value: 'EXENTO', label: 'Exento' },
  { value: 'NO_GRAVADO', label: 'No Gravado' },
];

const NC_CODE_BY_FACTURA = {
  1: 3,
  2: 3,
  6: 8,
  7: 8,
  11: 13,
  12: 13,
  19: 21,
  20: 21,
  51: 53,
  52: 53,
  201: 203,
  202: 203,
  206: 208,
  207: 208,
  211: 213,
  212: 213,
};

const FacturacionArcaFinanzasPage = () => {
  const [tiposComprobante, setTiposComprobante] = useState([]);
  const [receptores, setReceptores] = useState([]);
  const [provincias, setProvincias] = useState([]);
  const [facturas, setFacturas] = useState([]);
  const [kpis, setKpis] = useState({
    total_facturado_neto: 0,
    total_iva_debito: 0,
    total_notas_credito: 0,
    cantidad_comprobantes: 0,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Filtros de listado
  const [fechaDesde, setFechaDesde] = useState(() => {
    const now = new Date();
    return getLocalDateISO(new Date(now.getFullYear(), now.getMonth(), 1));
  });
  const [fechaHasta, setFechaHasta] = useState(() => getLocalDateISO());
  const [filtroOrigen, setFiltroOrigen] = useState('FINANZAS');
  const [filtroTipo, setFiltroTipo] = useState('');
  const [search, setSearch] = useState('');

  // Modal de emisión individual
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [emitting, setEmitting] = useState(false);
  const [modalError, setModalError] = useState('');
  const [emittedSuccess, setEmittedSuccess] = useState(null);

  const [receptorSearch, setReceptorSearch] = useState('');
  const [selectedReceptorKey, setSelectedReceptorKey] = useState('');
  const [arcaStatus, setArcaStatus] = useState({
    environment: 'mock',
    punto_venta_default: 1,
    cbu_fce_default: '',
    fce_sistema_circulacion: 'ADC',
  });
  const [consultingPadron, setConsultingPadron] = useState(false);
  const [padronMsg, setPadronMsg] = useState('');

  const [formData, setFormData] = useState({
    punto_venta: 1,
    tipo_comprobante: 1,
    fecha_emision: getLocalDateISO(),
    concepto_arca: 2,
    fecha_servicio_desde: getLocalDateISO(),
    fecha_servicio_hasta: getLocalDateISO(),
    fecha_vencimiento_pago: getLocalDateISO(),
    tipo_doc_receptor: 'CUIT',
    cuit_cliente: '',
    razon_social_receptor: '',
    domicilio_receptor: '',
    condicion_iva_receptor: 'Responsable Inscripto',
    provincia_id: '',
    comprobante_asociado_id: '',
    comprobante_asociado_str: '',
    comprobante_asociado_tipo: 1,
    comprobante_asociado_punto_venta: 1,
    comprobante_asociado_nro: '',
    comprobante_asociado_fecha: getLocalDateISO(),
    cbu_emisor: '',
    fce_sistema_circulacion: 'ADC',
    fce_anulacion: 'N',
    percepcion_iva: 0,
    percepcion_iibb: 0,
    otros_impuestos: 0,
    observaciones: '',
  });

  const [items, setItems] = useState([
    { descripcion: '', cantidad: 1, precio_unitario: 0, alicuota_iva: '21' },
  ]);

  const formatCurrency = (val) =>
    new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
      minimumFractionDigits: 2,
    }).format(val || 0);

  const fetchCatalogos = useCallback(async () => {
    try {
      const [resTipos, resRec, resStatus] = await Promise.all([
        axiosClient.get('/api/v1/facturacion/tipos-comprobante'),
        axiosClient.get('/api/v1/facturacion/receptores'),
        axiosClient.get('/api/v1/system/arca/status').catch(() => ({ data: null })),
      ]);
      setTiposComprobante(resTipos.data || []);
      setReceptores(resRec.data?.receptores || []);
      setProvincias(resRec.data?.provincias || []);
      if (resStatus?.data) {
        setArcaStatus({
          environment: resStatus.data.environment || 'mock',
          punto_venta_default: resStatus.data.punto_venta_default || 1,
          cbu_fce_default: resStatus.data.cbu_fce_default || '',
          fce_sistema_circulacion: resStatus.data.fce_sistema_circulacion || 'ADC',
          condicion_iva_emisor_label: resStatus.data.condicion_iva_emisor_label || '',
        });
      }
    } catch (err) {
      console.error('Error cargando catálogos ARCA:', err);
    }
  }, []);

  const fetchEmitidas = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { limit: 1000 };
      if (fechaDesde) params.fecha_desde = fechaDesde;
      if (fechaHasta) params.fecha_hasta = fechaHasta;
      if (filtroOrigen && filtroOrigen !== 'TODOS') params.origen = filtroOrigen;
      if (filtroTipo) params.tipo_comprobante = filtroTipo;
      if (search.trim()) params.search = search.trim();

      const res = await axiosClient.get('/api/v1/facturacion/emitidas', { params });
      setFacturas(res.data?.items || []);
      setKpis(
        res.data?.kpis || {
          total_facturado_neto: 0,
          total_iva_debito: 0,
          total_notas_credito: 0,
          cantidad_comprobantes: 0,
        }
      );
    } catch (err) {
      console.error(err);
      setError('Error al cargar los comprobantes emitidos.');
    } finally {
      setLoading(false);
    }
  }, [fechaDesde, fechaHasta, filtroOrigen, filtroTipo, search]);

  useEffect(() => {
    fetchCatalogos();
  }, [fetchCatalogos]);

  useEffect(() => {
    fetchEmitidas();
  }, [fetchEmitidas]);

  const tipoSeleccionadoInfo = useMemo(() => {
    return (
      tiposComprobante.find((t) => Number(t.codigo) === Number(formData.tipo_comprobante)) || {
        codigo: 1,
        letra: 'A',
        nombre: 'Factura A',
        discrimina_iva: true,
        requiere_cuit: true,
        es_nota_credito: false,
        es_nota_debito: false,
        es_fce: false,
      }
    );
  }, [tiposComprobante, formData.tipo_comprobante]);

  const tiposPorClase = useMemo(() => {
    const groups = {};
    tiposComprobante.forEach((t) => {
      if (arcaStatus.environment !== 'mock' && [19, 20, 21].includes(Number(t.codigo))) {
        return;
      }
      const cl = t.clase || 'Otros';
      if (!groups[cl]) groups[cl] = [];
      groups[cl].push(t);
    });
    return groups;
  }, [tiposComprobante, arcaStatus.environment]);

  const receptoresFiltrados = useMemo(() => {
    if (!receptorSearch.trim()) return receptores.slice(0, 150);
    const q = receptorSearch.toLowerCase();
    return receptores
      .filter(
        (r) =>
          (r.razon_social || '').toLowerCase().includes(q) ||
          (r.nro_doc || '').toLowerCase().includes(q) ||
          (r.tipo_entidad || '').toLowerCase().includes(q)
      )
      .slice(0, 150);
  }, [receptores, receptorSearch]);

  const handleSelectReceptor = (key) => {
    setSelectedReceptorKey(key);
    const found = receptores.find((r) => r.key === key);
    if (!found) return;
    setFormData((prev) => ({
      ...prev,
      tipo_doc_receptor: found.tipo_doc || 'CUIT',
      cuit_cliente: found.nro_doc || '',
      razon_social_receptor: found.razon_social || '',
      domicilio_receptor: found.domicilio || '',
      condicion_iva_receptor: found.condicion_iva || prev.condicion_iva_receptor,
      provincia_id: found.provincia_id || '',
    }));
  };

  // Cálculo en tiempo real de desglose fiscal según ítems y tipo de comprobante
  const resumenCalculado = useMemo(() => {
    let no_gravado = 0;
    let exento = 0;
    let neto_0 = 0;
    let neto_21 = 0;
    let neto_105 = 0;
    let neto_27 = 0;
    let bruto_21 = 0;
    let bruto_105 = 0;
    let bruto_27 = 0;

    const esClaseCoE = ['C', 'E'].includes(tipoSeleccionadoInfo.letra);
    const discrimina = Boolean(tipoSeleccionadoInfo.discrimina_iva);

    items.forEach((it) => {
      const cant = parseFloat(it.cantidad) || 0;
      const unit = parseFloat(it.precio_unitario) || 0;
      const sub = Math.round(cant * unit * 100) / 100;
      const alic = String(it.alicuota_iva || '21').toUpperCase();

      if (esClaseCoE || alic === 'EXENTO') {
        exento += sub;
      } else if (alic === '0') {
        neto_0 += sub;
      } else if (alic === 'NO_GRAVADO') {
        no_gravado += sub;
      } else if (alic === '10.5') {
        bruto_105 += sub;
        neto_105 += discrimina ? sub : sub / 1.105;
      } else if (alic === '27') {
        bruto_27 += sub;
        neto_27 += discrimina ? sub : sub / 1.27;
      } else {
        bruto_21 += sub;
        neto_21 += discrimina ? sub : sub / 1.21;
      }
    });

    no_gravado = Math.round(no_gravado * 100) / 100;
    exento = Math.round(exento * 100) / 100;
    neto_0 = Math.round(neto_0 * 100) / 100;
    neto_21 = Math.round(neto_21 * 100) / 100;
    neto_105 = Math.round(neto_105 * 100) / 100;
    neto_27 = Math.round(neto_27 * 100) / 100;
    bruto_21 = Math.round(bruto_21 * 100) / 100;
    bruto_105 = Math.round(bruto_105 * 100) / 100;
    bruto_27 = Math.round(bruto_27 * 100) / 100;

    const iva_21 = esClaseCoE
      ? 0
      : discrimina
      ? Math.round(neto_21 * 0.21 * 100) / 100
      : Math.round((bruto_21 - neto_21) * 100) / 100;
    const iva_105 = esClaseCoE
      ? 0
      : discrimina
      ? Math.round(neto_105 * 0.105 * 100) / 100
      : Math.round((bruto_105 - neto_105) * 100) / 100;
    const iva_27 = esClaseCoE
      ? 0
      : discrimina
      ? Math.round(neto_27 * 0.27 * 100) / 100
      : Math.round((bruto_27 - neto_27) * 100) / 100;

    const perc_iva = parseFloat(formData.percepcion_iva) || 0;
    const perc_iibb = parseFloat(formData.percepcion_iibb) || 0;
    const otros_imp = parseFloat(formData.otros_impuestos) || 0;

    const neto_total = Math.round((neto_0 + neto_21 + neto_105 + neto_27) * 100) / 100;
    const iva_total = Math.round((iva_21 + iva_105 + iva_27) * 100) / 100;
    const otros_total = Math.round((perc_iva + perc_iibb + otros_imp) * 100) / 100;
    const importe_total =
      Math.round((no_gravado + exento + neto_total + iva_total + otros_total) * 100) / 100;

    return {
      importe_no_gravado: no_gravado,
      importe_exento: exento,
      neto_gravado_0: neto_0,
      neto_gravado_21: neto_21,
      neto_gravado_105: neto_105,
      neto_gravado_27: neto_27,
      neto_total,
      iva_21,
      iva_105,
      iva_27,
      iva_total,
      otros_total,
      importe_total,
    };
  }, [items, tipoSeleccionadoInfo, formData.percepcion_iva, formData.percepcion_iibb, formData.otros_impuestos]);

  const handleOpenNewModal = (presetFactura = null) => {
    setModalError('');
    setPadronMsg('');
    setEmittedSuccess(null);
    setSelectedReceptorKey('');
    setReceptorSearch('');
    const ptoVtaDefault = Number(arcaStatus.punto_venta_default) || 1;
    const cbuDefault = arcaStatus.cbu_fce_default || '';
    const fceCircDefault = arcaStatus.fce_sistema_circulacion || 'ADC';

    if (presetFactura) {
      const ncCodigo = NC_CODE_BY_FACTURA[presetFactura.tipo_comprobante] || 3;
      setFormData({
        punto_venta: presetFactura.punto_venta || ptoVtaDefault,
        tipo_comprobante: ncCodigo,
        fecha_emision: getLocalDateISO(),
        concepto_arca: 2,
        fecha_servicio_desde: getLocalDateISO(),
        fecha_servicio_hasta: getLocalDateISO(),
        fecha_vencimiento_pago: getLocalDateISO(),
        tipo_doc_receptor: presetFactura.tipo_doc_receptor || 'CUIT',
        cuit_cliente: presetFactura.cuit_cliente || '',
        razon_social_receptor: presetFactura.razon_social_receptor || 'Consumidor Final',
        domicilio_receptor: '',
        condicion_iva_receptor: presetFactura.condicion_iva_receptor || 'Responsable Inscripto',
        provincia_id: presetFactura.provincia_id || '',
        comprobante_asociado_id: presetFactura.id,
        comprobante_asociado_str: `${presetFactura.tipo_comprobante_nombre} ${presetFactura.comprobante_formateado}`,
        comprobante_asociado_tipo: presetFactura.tipo_comprobante || 1,
        comprobante_asociado_punto_venta: presetFactura.punto_venta || ptoVtaDefault,
        comprobante_asociado_nro: presetFactura.nro_comprobante || '',
        comprobante_asociado_fecha: presetFactura.fecha_emision || getLocalDateISO(),
        cbu_emisor: cbuDefault,
        fce_sistema_circulacion: fceCircDefault,
        fce_anulacion: 'N',
        percepcion_iva: 0,
        percepcion_iibb: 0,
        otros_impuestos: 0,
        observaciones: `Anulación / Nota de Crédito s/ ${presetFactura.tipo_comprobante_nombre} ${presetFactura.comprobante_formateado}`,
      });
      const saldoTotal =
        typeof presetFactura.saldo_pendiente_nc === 'number' && presetFactura.saldo_pendiente_nc > 0
          ? presetFactura.saldo_pendiente_nc
          : presetFactura.importe_total;
      const ratioSaldo =
        presetFactura.importe_total > 0 ? saldoTotal / presetFactura.importe_total : 1;
      const basePrecio =
        presetFactura.letra === 'A' || presetFactura.letra === 'M'
          ? Math.round(((presetFactura.neto_gravado || presetFactura.importe_total) * ratioSaldo) * 100) / 100
          : Math.round(saldoTotal * 100) / 100;
      setItems([
        {
          descripcion: `Nota de Crédito sobre ${presetFactura.tipo_comprobante_nombre} ${presetFactura.comprobante_formateado}`,
          cantidad: 1,
          precio_unitario: basePrecio,
          alicuota_iva: '21',
        },
      ]);
    } else {
      setFormData({
        punto_venta: ptoVtaDefault,
        tipo_comprobante: 1,
        fecha_emision: getLocalDateISO(),
        concepto_arca: 2,
        fecha_servicio_desde: getLocalDateISO(),
        fecha_servicio_hasta: getLocalDateISO(),
        fecha_vencimiento_pago: getLocalDateISO(),
        tipo_doc_receptor: 'CUIT',
        cuit_cliente: '',
        razon_social_receptor: '',
        domicilio_receptor: '',
        condicion_iva_receptor: 'Responsable Inscripto',
        provincia_id: '',
        comprobante_asociado_id: '',
        comprobante_asociado_str: '',
        comprobante_asociado_tipo: 1,
        comprobante_asociado_punto_venta: ptoVtaDefault,
        comprobante_asociado_nro: '',
        comprobante_asociado_fecha: getLocalDateISO(),
        cbu_emisor: cbuDefault,
        fce_sistema_circulacion: fceCircDefault,
        fce_anulacion: 'N',
        percepcion_iva: 0,
        percepcion_iibb: 0,
        otros_impuestos: 0,
        observaciones: '',
      });
      setItems([{ descripcion: '', cantidad: 1, precio_unitario: 0, alicuota_iva: '21' }]);
    }

    setIsModalOpen(true);
  };

  const handleConsultarPadronArca = async () => {
    const cleanCuit = String(formData.cuit_cliente || '').replace(/\D/g, '');
    if (cleanCuit.length !== 11) {
      setPadronMsg('Ingrese un CUIT/CUIL válido de 11 dígitos para consultar en ARCA.');
      return;
    }
    setConsultingPadron(true);
    setPadronMsg('');
    try {
      const res = await axiosClient.get(`/api/v1/facturacion/consultar-cuit/${cleanCuit}`);
      const d = res.data;
      setFormData((prev) => ({
        ...prev,
        cuit_cliente: cleanCuit,
        razon_social_receptor: d.razon_social || prev.razon_social_receptor,
        domicilio_receptor:
          [d.domicilio_fiscal, d.localidad, d.provincia].filter(Boolean).join(', ') ||
          prev.domicilio_receptor,
        condicion_iva_receptor: d.condicion_iva || prev.condicion_iva_receptor,
        provincia_id: d.provincia_id_sugerida || prev.provincia_id,
      }));
      setPadronMsg(
        `✅ Padrón ARCA: ${d.razon_social} — ${d.condicion_iva} (${d.estado_clave || 'ACTIVO'})`
      );
    } catch (err) {
      setPadronMsg(
        `⚠️ ${err.response?.data?.detail || 'No se pudo consultar el CUIT en Padrón ARCA.'}`
      );
    } finally {
      setConsultingPadron(false);
    }
  };

  const handleItemChange = (index, field, value) => {
    setItems((prev) =>
      prev.map((it, idx) => (idx === index ? { ...it, [field]: value } : it))
    );
  };

  const handleAddItem = () => {
    setItems((prev) => [
      ...prev,
      { descripcion: '', cantidad: 1, precio_unitario: 0, alicuota_iva: '21' },
    ]);
  };

  const handleRemoveItem = (index) => {
    if (items.length <= 1) return;
    setItems((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmitEmision = async (e) => {
    e.preventDefault();
    setEmitting(true);
    setModalError('');

    try {
      const payload = {
        punto_venta: Number(formData.punto_venta) || 1,
        tipo_comprobante: Number(formData.tipo_comprobante),
        fecha_emision: formData.fecha_emision || null,
        concepto_arca: Number(formData.concepto_arca) || 2,
        fecha_servicio_desde: formData.fecha_servicio_desde || null,
        fecha_servicio_hasta: formData.fecha_servicio_hasta || null,
        fecha_vencimiento_pago: formData.fecha_vencimiento_pago || null,
        tipo_doc_receptor: formData.tipo_doc_receptor || 'CUIT',
        cuit_cliente: formData.cuit_cliente?.trim() || null,
        razon_social_receptor: formData.razon_social_receptor?.trim() || 'Consumidor Final',
        domicilio_receptor: formData.domicilio_receptor?.trim() || null,
        condicion_iva_receptor: formData.condicion_iva_receptor || 'Consumidor Final',
        provincia_id: formData.provincia_id ? Number(formData.provincia_id) : null,
        comprobante_asociado_id: formData.comprobante_asociado_id
          ? Number(formData.comprobante_asociado_id)
          : null,
        comprobante_asociado_str: formData.comprobante_asociado_str?.trim() || null,
        comprobante_asociado_tipo: formData.comprobante_asociado_tipo
          ? Number(formData.comprobante_asociado_tipo)
          : null,
        comprobante_asociado_punto_venta: formData.comprobante_asociado_punto_venta
          ? Number(formData.comprobante_asociado_punto_venta)
          : null,
        comprobante_asociado_nro: formData.comprobante_asociado_nro
          ? Number(formData.comprobante_asociado_nro)
          : null,
        comprobante_asociado_fecha: formData.comprobante_asociado_fecha || null,
        cbu_emisor: formData.cbu_emisor?.trim() || null,
        fce_sistema_circulacion: formData.fce_sistema_circulacion || null,
        fce_anulacion: formData.fce_anulacion || null,
        importe_no_gravado: resumenCalculado.importe_no_gravado,
        importe_exento: resumenCalculado.importe_exento,
        neto_gravado_0: resumenCalculado.neto_gravado_0,
        neto_gravado_21: resumenCalculado.neto_gravado_21,
        neto_gravado_105: resumenCalculado.neto_gravado_105,
        neto_gravado_27: resumenCalculado.neto_gravado_27,
        iva_21: resumenCalculado.iva_21,
        iva_105: resumenCalculado.iva_105,
        iva_27: resumenCalculado.iva_27,
        percepcion_iva: parseFloat(formData.percepcion_iva) || 0,
        percepcion_iibb: parseFloat(formData.percepcion_iibb) || 0,
        otros_impuestos: parseFloat(formData.otros_impuestos) || 0,
        importe_total: resumenCalculado.importe_total,
        items: items.map((it) => ({
          descripcion: it.descripcion?.trim() || 'Servicios Financieros',
          cantidad: parseFloat(it.cantidad) || 1,
          precio_unitario: parseFloat(it.precio_unitario) || 0,
          alicuota_iva: String(it.alicuota_iva || '21'),
        })),
        observaciones: formData.observaciones?.trim() || null,
      };

      const res = await axiosClient.post('/api/v1/facturacion/emitir-individual', payload);
      setEmittedSuccess(res.data);
      fetchEmitidas();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setModalError(detail.map((d) => `${d.loc?.join('.')}: ${d.msg}`).join(', '));
      } else {
        setModalError(detail || 'Error al emitir el comprobante en ARCA.');
      }
    } finally {
      setEmitting(false);
    }
  };

  const handleDescargarPdfIndividual = async (factura) => {
    const filename = `${(factura.tipo_comprobante_nombre || 'Factura').replace(/\s+/g, '_')}_${factura.comprobante_formateado}.pdf`;
    await downloadFile(`/api/v1/facturacion/${factura.id}/pdf`, {}, filename);
  };

  const handleDescargarLibroIva = async () => {
    const params = {};
    if (fechaDesde) params.fecha_desde = fechaDesde;
    if (fechaHasta) params.fecha_hasta = fechaHasta;
    await downloadFile('/api/v1/facturacion/libro-iva', params, 'libro_iva_ventas.xlsx');
  };

  const handleDescargarPdfsZip = async () => {
    const params = {};
    if (fechaDesde) params.fecha_desde = fechaDesde;
    if (fechaHasta) params.fecha_hasta = fechaHasta;
    await downloadFile('/api/v1/facturacion/descargar-masivo', params, 'facturas_arca.zip');
  };

  return (
    <div className="page-container" style={{ padding: '24px', margin: '0 auto' }}>
      <header
        className="page-header"
        style={{
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <h1
            className="page-title"
            style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '28px', fontWeight: 'bold', margin: 0, flexWrap: 'wrap' }}
          >
            <Receipt size={32} color="var(--primary-color)" />
            Finanzas — Facturación Electrónica ARCA
            <span
              style={{
                padding: '4px 12px',
                borderRadius: '999px',
                fontSize: '12px',
                fontWeight: 700,
                background:
                  arcaStatus.environment === 'produccion'
                    ? 'rgba(239, 68, 68, 0.15)'
                    : arcaStatus.environment === 'homologacion'
                    ? 'rgba(245, 158, 11, 0.15)'
                    : 'rgba(100, 116, 139, 0.15)',
                color:
                  arcaStatus.environment === 'produccion'
                    ? '#ef4444'
                    : arcaStatus.environment === 'homologacion'
                    ? '#f59e0b'
                    : 'var(--text-muted)',
                border: '1px solid currentColor',
              }}
            >
              {arcaStatus.environment === 'produccion'
                ? '🔴 PRODUCCIÓN ARCA'
                : arcaStatus.environment === 'homologacion'
                ? '🟡 HOMOLOGACIÓN ARCA'
                : '🧪 MODO MOCK'}
            </span>
          </h1>
          <p className="page-description" style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '6px' }}>
            Emisión individual de comprobantes electrónicos de ARCA (Facturas A, B, C, M, Notas de Crédito/Débito, Recibos y FCE MiPyME) con impacto automático en Libro IVA, Posición IVA e IIBB.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            className="btn-secondary"
            onClick={handleDescargarLibroIva}
            style={{ height: '42px', padding: '0 16px' }}
          >
            📥 Libro IVA Ventas
          </button>
          <button
            className="btn-secondary"
            onClick={handleDescargarPdfsZip}
            style={{ height: '42px', padding: '0 16px' }}
          >
            📦 Descargar PDFs (ZIP)
          </button>
          <button
            className="btn-primary"
            onClick={() => handleOpenNewModal(null)}
            style={{ width: 'auto', height: '42px', padding: '0 20px' }}
          >
            <Plus size={18} />
            Emitir Comprobante ARCA
          </button>
        </div>
      </header>

      {/* Tarjetas de KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="card" style={{ padding: '20px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 500 }}>Total Neto Facturado (Período)</span>
          <h3 style={{ fontSize: '24px', fontWeight: 'bold', margin: '8px 0 0 0', color: 'var(--primary-color)' }}>
            {formatCurrency(kpis.total_facturado_neto)}
          </h3>
        </div>
        <div className="card" style={{ padding: '20px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 500 }}>IVA Débito Fiscal Neto</span>
          <h3 style={{ fontSize: '24px', fontWeight: 'bold', margin: '8px 0 0 0' }}>
            {formatCurrency(kpis.total_iva_debito)}
          </h3>
        </div>
        <div className="card" style={{ padding: '20px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 500 }}>Total Notas de Crédito</span>
          <h3 style={{ fontSize: '24px', fontWeight: 'bold', margin: '8px 0 0 0', color: '#ef4444' }}>
            {formatCurrency(kpis.total_notas_credito)}
          </h3>
        </div>
        <div className="card" style={{ padding: '20px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 500 }}>Comprobantes Emitidos</span>
          <h3 style={{ fontSize: '24px', fontWeight: 'bold', margin: '8px 0 0 0' }}>
            {kpis.cantidad_comprobantes}
          </h3>
        </div>
      </div>

      {/* Barra de Filtros */}
      <div className="card" style={{ marginBottom: '24px', padding: '20px' }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 160px' }}>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Calendar size={14} /> Desde
            </label>
            <input
              type="date"
              className="form-control"
              value={fechaDesde}
              onChange={(e) => setFechaDesde(e.target.value)}
            />
          </div>
          <div style={{ flex: '1 1 160px' }}>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Calendar size={14} /> Hasta
            </label>
            <input
              type="date"
              className="form-control"
              value={fechaHasta}
              onChange={(e) => setFechaHasta(e.target.value)}
            />
          </div>
          <div style={{ flex: '1 1 180px' }}>
            <label className="form-label">Origen</label>
            <select
              className="form-control"
              value={filtroOrigen}
              onChange={(e) => setFiltroOrigen(e.target.value)}
            >
              <option value="FINANZAS">Finanzas (Individuales)</option>
              <option value="TODOS">Todos (Finanzas + Cobranzas)</option>
              <option value="COBRANZA">Cobranzas (Lotes Masivos)</option>
            </select>
          </div>
          <div style={{ flex: '1 1 220px' }}>
            <label className="form-label">Tipo de Comprobante</label>
            <select
              className="form-control"
              value={filtroTipo}
              onChange={(e) => setFiltroTipo(e.target.value)}
            >
              <option value="">Todos los tipos...</option>
              {tiposComprobante.map((t) => (
                <option key={t.codigo} value={t.codigo}>
                  [{t.letra}] {t.nombre} (Cod. {String(t.codigo).padStart(3, '0')})
                </option>
              ))}
            </select>
          </div>
          <div style={{ flex: '2 1 240px' }}>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Search size={14} /> Buscar Receptor / CUIT / Nro / CAE
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="Ej: 30712345678, Socio, 0001-00000005..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div>
            <ExportExcelButton
              data={facturas}
              filteredData={facturas}
              filename="comprobantes_arca_emitidos"
            />
          </div>
        </div>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>{error}</div>}

      {/* Tabla de Comprobantes */}
      <div className="card">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Comprobante</th>
                <th>Número</th>
                <th>Receptor</th>
                <th>CUIT / Doc</th>
                <th>Provincia (IIBB)</th>
                <th style={{ textAlign: 'right' }}>Neto / Exento</th>
                <th style={{ textAlign: 'right' }}>IVA</th>
                <th style={{ textAlign: 'right' }}>Total</th>
                <th>CAE</th>
                <th style={{ textAlign: 'center' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="11" style={{ textAlign: 'center', padding: '32px' }}>
                    Cargando comprobantes...
                  </td>
                </tr>
              ) : facturas.length === 0 ? (
                <tr>
                  <td colSpan="11" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No se encontraron comprobantes emitidos para los filtros seleccionados.
                  </td>
                </tr>
              ) : (
                facturas.map((f) => {
                  const sign = f.es_nota_credito ? -1 : 1;
                  const baseNeta = (f.neto_gravado || 0) + (f.importe_exento || 0) + (f.importe_no_gravado || 0);
                  return (
                    <tr key={f.id}>
                      <td style={{ whiteSpace: 'nowrap' }}>{f.fecha_emision}</td>
                      <td>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '12px',
                            fontWeight: 600,
                            background: f.es_nota_credito ? 'rgba(239, 68, 68, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                            color: f.es_nota_credito ? '#ef4444' : 'var(--primary-color)',
                          }}
                        >
                          [{f.letra}] {f.tipo_comprobante_nombre}
                        </span>
                        {f.comprobante_asociado_str && (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                            Asoc: {f.comprobante_asociado_str}
                          </div>
                        )}
                        {f.anulada_por_nc && (
                          <div
                            style={{
                              fontSize: '11px',
                              color: '#ef4444',
                              fontWeight: 600,
                              marginTop: '3px',
                            }}
                          >
                            Anulada 100% por NC
                          </div>
                        )}
                        {f.tiene_nc_parcial && (
                          <div
                            style={{
                              fontSize: '11px',
                              color: '#f59e0b',
                              fontWeight: 600,
                              marginTop: '3px',
                            }}
                          >
                            NC Parcial (Saldo: {formatCurrency(f.saldo_pendiente_nc)})
                          </div>
                        )}
                      </td>
                      <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{f.comprobante_formateado}</td>
                      <td>
                        <div style={{ fontWeight: 500 }}>{f.razon_social_receptor}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{f.condicion_iva_receptor}</div>
                      </td>
                      <td style={{ whiteSpace: 'nowrap' }}>{f.cuit_cliente || 'Consumidor Final'}</td>
                      <td>{f.provincia_nombre || '-'}</td>
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        {formatCurrency(sign * baseNeta)}
                      </td>
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        {formatCurrency(sign * (f.iva_total || 0))}
                      </td>
                      <td
                        style={{
                          textAlign: 'right',
                          fontWeight: 'bold',
                          whiteSpace: 'nowrap',
                          color: f.es_nota_credito ? '#ef4444' : 'inherit',
                        }}
                      >
                        {formatCurrency(sign * (f.importe_total || 0))}
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        <div>{f.cae || '-'}</div>
                        {f.vencimiento_cae && (
                          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Vto: {f.vencimiento_cae}</div>
                        )}
                      </td>
                      <td style={{ textAlign: 'center', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                          <button
                            className="btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '14px' }}
                            title="Descargar PDF del Comprobante"
                            onClick={() => handleDescargarPdfIndividual(f)}
                          >
                            📥
                          </button>
                          {!f.es_nota_credito && !f.anulada_por_nc && (
                            <button
                              className="btn-secondary"
                              style={{ padding: '4px 8px', fontSize: '14px', color: '#ef4444' }}
                              title={
                                f.tiene_nc_parcial
                                  ? `Emitir Nota de Crédito por el saldo restante (${formatCurrency(f.saldo_pendiente_nc)})`
                                  : 'Emitir Nota de Crédito asociada a este comprobante'
                              }
                              onClick={() => handleOpenNewModal(f)}
                            >
                              ↩️ NC
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Emisión Individual ARCA */}
      {isModalOpen && (
        <div
          className="modal-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
        >
          <div
            className="modal-content"
            style={{
              background: 'var(--surface-color)',
              padding: '24px',
              borderRadius: 'var(--radius-lg)',
              width: '100%',
              maxWidth: '940px',
              maxHeight: '92vh',
              overflowY: 'auto',
              boxShadow: 'var(--shadow-lg)',
              border: '1px solid var(--border-color)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Receipt size={22} color="var(--primary-color)" />
                Emitir Comprobante Individual en ARCA
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={24} />
              </button>
            </div>

            {emittedSuccess ? (
              <div style={{ padding: '16px 0' }}>
                <div
                  className="alert alert-success"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                    padding: '20px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid #22c55e',
                    background: 'rgba(34, 197, 94, 0.1)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '18px', fontWeight: 'bold', color: '#22c55e' }}>
                    <CheckCircle2 size={24} />
                    ¡Comprobante autorizado exitosamente por ARCA!
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginTop: '8px' }}>
                    <div>
                      <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Comprobante</span>
                      <div style={{ fontWeight: 'bold', fontSize: '15px' }}>
                        [{emittedSuccess.letra}] {emittedSuccess.tipo_comprobante_nombre} #{emittedSuccess.comprobante_formateado}
                      </div>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Receptor</span>
                      <div style={{ fontWeight: 'bold', fontSize: '15px' }}>
                        {emittedSuccess.razon_social_receptor} ({emittedSuccess.cuit_cliente || 'CF'})
                      </div>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Importe Total</span>
                      <div style={{ fontWeight: 'bold', fontSize: '16px', color: 'var(--primary-color)' }}>
                        {formatCurrency(emittedSuccess.importe_total)}
                      </div>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>CAE / Vencimiento</span>
                      <div style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                        {emittedSuccess.cae} ({emittedSuccess.vencimiento_cae})
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => handleOpenNewModal(null)}
                  >
                    Emitir Otro Comprobante
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => handleDescargarPdfIndividual(emittedSuccess)}
                    style={{ width: 'auto', padding: '0 20px' }}
                  >
                    📥 Descargar PDF Ahora
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setIsModalOpen(false)}
                  >
                    Cerrar
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmitEmision} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                {modalError && (
                  <div className="alert alert-error" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <AlertCircle size={18} />
                    <span>{modalError}</span>
                  </div>
                )}

                {/* 1. Datos del Comprobante */}
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: '14px' }}>
                  <div>
                    <label className="form-label">Tipo de Comprobante ARCA *</label>
                    <select
                      required
                      className="form-control"
                      value={formData.tipo_comprobante}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, tipo_comprobante: Number(e.target.value) }))
                      }
                    >
                      {Object.entries(tiposPorClase).map(([clase, lista]) => (
                        <optgroup key={clase} label={clase}>
                          {lista.map((t) => (
                            <option key={t.codigo} value={t.codigo}>
                              [{t.letra}] {t.nombre} (Cód. {String(t.codigo).padStart(3, '0')})
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="form-label">Punto de Venta *</label>
                    <input
                      required
                      type="number"
                      min="1"
                      max="99999"
                      className="form-control"
                      value={formData.punto_venta}
                      onChange={(e) => setFormData((prev) => ({ ...prev, punto_venta: e.target.value }))}
                    />
                  </div>

                  <div>
                    <label className="form-label">Fecha Emisión *</label>
                    <input
                      required
                      type="date"
                      className="form-control"
                      value={formData.fecha_emision}
                      onChange={(e) => setFormData((prev) => ({ ...prev, fecha_emision: e.target.value }))}
                    />
                  </div>

                  <div>
                    <label className="form-label">Concepto ARCA *</label>
                    <select
                      className="form-control"
                      value={formData.concepto_arca}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, concepto_arca: Number(e.target.value) }))
                      }
                    >
                      <option value={1}>1 - Productos</option>
                      <option value={2}>2 - Servicios</option>
                      <option value={3}>3 - Productos y Servicios</option>
                    </select>
                  </div>
                </div>

                {/* Fechas de servicio si Concepto ARCA es 2 o 3 */}
                {(Number(formData.concepto_arca) === 2 || Number(formData.concepto_arca) === 3) && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
                    <div>
                      <label className="form-label">Período Facturado Desde *</label>
                      <input
                        required
                        type="date"
                        className="form-control"
                        value={formData.fecha_servicio_desde}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, fecha_servicio_desde: e.target.value }))
                        }
                      />
                    </div>
                    <div>
                      <label className="form-label">Período Facturado Hasta *</label>
                      <input
                        required
                        type="date"
                        className="form-control"
                        value={formData.fecha_servicio_hasta}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, fecha_servicio_hasta: e.target.value }))
                        }
                      />
                    </div>
                    <div>
                      <label className="form-label">Vencimiento para el Pago *</label>
                      <input
                        required
                        type="date"
                        className="form-control"
                        value={formData.fecha_vencimiento_pago}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, fecha_vencimiento_pago: e.target.value }))
                        }
                      />
                    </div>
                  </div>
                )}

                {/* Comprobante asociado si es Nota de Crédito o Débito */}
                {(tipoSeleccionadoInfo.es_nota_credito || tipoSeleccionadoInfo.es_nota_debito) && (
                  <div
                    style={{
                      padding: '14px',
                      borderRadius: 'var(--radius-md)',
                      background: 'rgba(239, 68, 68, 0.06)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px',
                    }}
                  >
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                      <div>
                        <label className="form-label">Seleccionar Factura Emitida Asociada</label>
                        <select
                          className="form-control"
                          value={formData.comprobante_asociado_id || ''}
                          onChange={(e) => {
                            const idVal = e.target.value;
                            const fAsoc = facturas.find((f) => String(f.id) === String(idVal));
                            setFormData((prev) => ({
                              ...prev,
                              comprobante_asociado_id: idVal,
                              comprobante_asociado_str: fAsoc
                                ? `${fAsoc.tipo_comprobante_nombre} ${fAsoc.comprobante_formateado}`
                                : prev.comprobante_asociado_str,
                              comprobante_asociado_tipo: fAsoc
                                ? fAsoc.tipo_comprobante
                                : prev.comprobante_asociado_tipo,
                              comprobante_asociado_punto_venta: fAsoc
                                ? fAsoc.punto_venta
                                : prev.comprobante_asociado_punto_venta,
                              comprobante_asociado_nro: fAsoc
                                ? fAsoc.nro_comprobante
                                : prev.comprobante_asociado_nro,
                              comprobante_asociado_fecha: fAsoc
                                ? fAsoc.fecha_emision
                                : prev.comprobante_asociado_fecha,
                            }));
                          }}
                        >
                          <option value="">-- Seleccionar del historial o cargar manualmente --</option>
                          {facturas
                            .filter(
                              (f) =>
                                !f.es_nota_credito &&
                                !(tipoSeleccionadoInfo.es_nota_credito && f.anulada_por_nc)
                            )
                            .map((f) => (
                              <option key={f.id} value={f.id}>
                                {f.tipo_comprobante_nombre} {f.comprobante_formateado} — {f.razon_social_receptor} (
                                {f.tiene_nc_parcial
                                  ? `Saldo disp.: ${formatCurrency(f.saldo_pendiente_nc)}`
                                  : formatCurrency(f.importe_total)}
                                )
                              </option>
                            ))}
                        </select>
                      </div>
                      <div>
                        <label className="form-label">Referencia Comprobante Asociado *</label>
                        <input
                          required
                          type="text"
                          className="form-control"
                          placeholder="Ej: Factura A 0001-00000125"
                          value={formData.comprobante_asociado_str}
                          onChange={(e) =>
                            setFormData((prev) => ({ ...prev, comprobante_asociado_str: e.target.value }))
                          }
                        />
                      </div>
                    </div>

                    {!formData.comprobante_asociado_id && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr', gap: '12px' }}>
                        <div>
                          <label className="form-label">Tipo Cbte. Asociado (ARCA) *</label>
                          <select
                            className="form-control"
                            value={formData.comprobante_asociado_tipo}
                            onChange={(e) =>
                              setFormData((prev) => ({
                                ...prev,
                                comprobante_asociado_tipo: Number(e.target.value),
                              }))
                            }
                          >
                            {tiposComprobante
                              .filter((t) => !t.es_nota_credito)
                              .map((t) => (
                                <option key={t.codigo} value={t.codigo}>
                                  [{t.letra}] {t.nombre} (Cód. {t.codigo})
                                </option>
                              ))}
                          </select>
                        </div>
                        <div>
                          <label className="form-label">Pto. Venta Asoc. *</label>
                          <input
                            type="number"
                            min="1"
                            max="99999"
                            className="form-control"
                            value={formData.comprobante_asociado_punto_venta}
                            onChange={(e) =>
                              setFormData((prev) => ({
                                ...prev,
                                comprobante_asociado_punto_venta: e.target.value,
                              }))
                            }
                          />
                        </div>
                        <div>
                          <label className="form-label">Nro. Cbte. Asoc. *</label>
                          <input
                            type="number"
                            min="1"
                            className="form-control"
                            placeholder="Ej: 125"
                            value={formData.comprobante_asociado_nro}
                            onChange={(e) =>
                              setFormData((prev) => ({
                                ...prev,
                                comprobante_asociado_nro: e.target.value,
                              }))
                            }
                          />
                        </div>
                        <div>
                          <label className="form-label">Fecha Cbte. Asoc. *</label>
                          <input
                            type="date"
                            className="form-control"
                            value={formData.comprobante_asociado_fecha}
                            onChange={(e) =>
                              setFormData((prev) => ({
                                ...prev,
                                comprobante_asociado_fecha: e.target.value,
                              }))
                            }
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Campos adicionales si es FCE MiPyME */}
                {tipoSeleccionadoInfo.es_fce && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr', gap: '14px' }}>
                    {!tipoSeleccionadoInfo.es_nota_credito && !tipoSeleccionadoInfo.es_nota_debito ? (
                      <>
                        <div>
                          <label className="form-label">CBU del Emisor (FCE MiPyME) *</label>
                          <input
                            required
                            type="text"
                            maxLength={22}
                            className="form-control"
                            placeholder="22 dígitos del CBU"
                            value={formData.cbu_emisor}
                            onChange={(e) => setFormData((prev) => ({ ...prev, cbu_emisor: e.target.value }))}
                          />
                        </div>
                        <div>
                          <label className="form-label">Sistema Circulación FCE (Opc. 27) *</label>
                          <select
                            className="form-control"
                            value={formData.fce_sistema_circulacion}
                            onChange={(e) =>
                              setFormData((prev) => ({ ...prev, fce_sistema_circulacion: e.target.value }))
                            }
                          >
                            <option value="ADC">ADC — Agente de Depósito Colectivo</option>
                            <option value="SCA">SCA — Sistema de Circulación Abierta</option>
                          </select>
                        </div>
                        <div>
                          <label className="form-label">Fecha Vencimiento Pago *</label>
                          <input
                            required
                            type="date"
                            className="form-control"
                            value={formData.fecha_vencimiento_pago}
                            onChange={(e) =>
                              setFormData((prev) => ({ ...prev, fecha_vencimiento_pago: e.target.value }))
                            }
                          />
                        </div>
                      </>
                    ) : (
                      <div>
                        <label className="form-label">¿Es Anulación de FCE Rechazada? (Opc. 22) *</label>
                        <select
                          className="form-control"
                          value={formData.fce_anulacion}
                          onChange={(e) =>
                            setFormData((prev) => ({ ...prev, fce_anulacion: e.target.value }))
                          }
                        >
                          <option value="N">N — No (Nota de Crédito / Débito normal)</option>
                          <option value="S">S — Sí (Por rechazo del receptor)</option>
                        </select>
                      </div>
                    )}
                  </div>
                )}

                <hr style={{ margin: '2px 0', borderColor: 'var(--border-color)' }} />

                {/* 2. Selector Rápido de Receptor + Carga Manual */}
                <div>
                  <h4 style={{ margin: '0 0 10px 0', color: 'var(--primary-color)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Building2 size={16} /> Datos del Receptor
                  </h4>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '12px', marginBottom: '12px' }}>
                    <div>
                      <label className="form-label">Filtrar entidad registrada</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Buscar Socio, Proveedor, Inversor o Cliente..."
                        value={receptorSearch}
                        onChange={(e) => setReceptorSearch(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="form-label">Autocompletar desde entidad del sistema (Opcional)</label>
                      <select
                        className="form-control"
                        value={selectedReceptorKey}
                        onChange={(e) => handleSelectReceptor(e.target.value)}
                      >
                        <option value="">-- Carga manual libre o seleccione una entidad --</option>
                        {receptoresFiltrados.map((r) => (
                          <option key={r.key} value={r.key}>
                            [{r.tipo_entidad}] {r.razon_social} ({r.tipo_doc}: {r.nro_doc})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr 2fr 1.3fr', gap: '12px', marginBottom: '12px' }}>
                    <div>
                      <label className="form-label">Tipo Doc.</label>
                      <select
                        className="form-control"
                        value={formData.tipo_doc_receptor}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, tipo_doc_receptor: e.target.value }))
                        }
                      >
                        <option value="CUIT">CUIT</option>
                        <option value="CUIL">CUIL</option>
                        <option value="DNI">DNI</option>
                        <option value="CF">Cons. Final</option>
                      </select>
                    </div>
                    <div>
                      <label className="form-label">
                        Nro. Documento {tipoSeleccionadoInfo.requiere_cuit ? '*' : ''}
                      </label>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <input
                          required={tipoSeleccionadoInfo.requiere_cuit}
                          type="text"
                          className="form-control"
                          placeholder="11 dígitos sin guiones"
                          value={formData.cuit_cliente}
                          onChange={(e) =>
                            setFormData((prev) => ({ ...prev, cuit_cliente: e.target.value }))
                          }
                        />
                        <button
                          type="button"
                          className="btn-secondary"
                          title="Consultar CUIT en Padrón ARCA (A5)"
                          disabled={consultingPadron || String(formData.cuit_cliente || '').replace(/\D/g, '').length !== 11}
                          onClick={handleConsultarPadronArca}
                          style={{ padding: '0 10px', whiteSpace: 'nowrap', fontSize: '12px' }}
                        >
                          {consultingPadron ? '...' : '🔍 ARCA'}
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="form-label">Razón Social / Apellido y Nombre *</label>
                      <input
                        required
                        type="text"
                        className="form-control"
                        placeholder="Nombre o Razón Social del receptor"
                        value={formData.razon_social_receptor}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, razon_social_receptor: e.target.value }))
                        }
                      />
                    </div>
                    <div>
                      <label className="form-label">Condición frente al IVA *</label>
                      <select
                        className="form-control"
                        value={formData.condicion_iva_receptor}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, condicion_iva_receptor: e.target.value }))
                        }
                      >
                        {CONDICIONES_IVA.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
                    <div>
                      <label className="form-label">Domicilio Comercial</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Calle, número, localidad..."
                        value={formData.domicilio_receptor}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, domicilio_receptor: e.target.value }))
                        }
                      />
                    </div>
                    <div>
                      <label className="form-label">Jurisdicción / Provincia (IIBB)</label>
                      <select
                        className="form-control"
                        value={formData.provincia_id}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, provincia_id: e.target.value }))
                        }
                      >
                        <option value="">Sin especificar...</option>
                        {provincias.map((pr) => (
                          <option key={pr.id} value={pr.id}>
                            {pr.nombre}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  {padronMsg && (
                    <div
                      style={{
                        marginTop: '8px',
                        fontSize: '12px',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        background: padronMsg.startsWith('✅')
                          ? 'rgba(34, 197, 94, 0.12)'
                          : 'rgba(245, 158, 11, 0.12)',
                        color: padronMsg.startsWith('✅') ? '#22c55e' : '#f59e0b',
                      }}
                    >
                      {padronMsg}
                    </div>
                  )}
                </div>

                <hr style={{ margin: '2px 0', borderColor: 'var(--border-color)' }} />

                {/* 3. Grilla de Conceptos / Ítems */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <h4 style={{ margin: 0, color: 'var(--primary-color)' }}>
                      Conceptos / Ítems a Facturar{' '}
                      <span style={{ fontSize: '12px', fontWeight: 'normal', color: 'var(--text-muted)' }}>
                        ({tipoSeleccionadoInfo.discrimina_iva
                          ? 'Comprobante Clase A/M: ingrese precios unitarios NETOS sin IVA'
                          : 'Comprobante Clase B/C/E: ingrese precios unitarios FINALES'})
                      </span>
                    </h4>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={handleAddItem}
                      style={{ padding: '4px 12px', fontSize: '13px' }}
                    >
                      <Plus size={14} /> Agregar Ítem
                    </button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {items.map((it, idx) => {
                      const sub = (parseFloat(it.cantidad) || 0) * (parseFloat(it.precio_unitario) || 0);
                      return (
                        <div
                          key={idx}
                          style={{
                            display: 'grid',
                            gridTemplateColumns: '3fr 90px 150px 130px 130px 40px',
                            gap: '10px',
                            alignItems: 'center',
                          }}
                        >
                          <input
                            required
                            type="text"
                            className="form-control"
                            placeholder="Descripción del servicio o concepto..."
                            value={it.descripcion}
                            onChange={(e) => handleItemChange(idx, 'descripcion', e.target.value)}
                          />
                          <input
                            required
                            type="number"
                            step="0.01"
                            min="0.01"
                            className="form-control"
                            placeholder="Cant."
                            value={it.cantidad}
                            onChange={(e) => handleItemChange(idx, 'cantidad', e.target.value)}
                          />
                          <CurrencyInput
                            className="form-control"
                            value={it.precio_unitario}
                            onChange={(val) => handleItemChange(idx, 'precio_unitario', val)}
                          />
                          <select
                            className="form-control"
                            value={it.alicuota_iva}
                            onChange={(e) => handleItemChange(idx, 'alicuota_iva', e.target.value)}
                            disabled={['C', 'E'].includes(tipoSeleccionadoInfo.letra)}
                          >
                            {ALICUOTAS_IVA.map((a) => (
                              <option key={a.value} value={a.value}>
                                IVA {a.label}
                              </option>
                            ))}
                          </select>
                          <div style={{ textAlign: 'right', fontWeight: 600, fontSize: '14px' }}>
                            {formatCurrency(sub)}
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(idx)}
                            disabled={items.length <= 1}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: items.length <= 1 ? 'var(--border-color)' : '#ef4444',
                              cursor: items.length <= 1 ? 'default' : 'pointer',
                            }}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Percepciones y Observaciones */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 2fr', gap: '12px' }}>
                  <div>
                    <label className="form-label">Percepción IVA</label>
                    <CurrencyInput
                      className="form-control"
                      value={formData.percepcion_iva}
                      onChange={(val) => setFormData((prev) => ({ ...prev, percepcion_iva: val }))}
                    />
                  </div>
                  <div>
                    <label className="form-label">Percepción IIBB</label>
                    <CurrencyInput
                      className="form-control"
                      value={formData.percepcion_iibb}
                      onChange={(val) => setFormData((prev) => ({ ...prev, percepcion_iibb: val }))}
                    />
                  </div>
                  <div>
                    <label className="form-label">Otros Tributos</label>
                    <CurrencyInput
                      className="form-control"
                      value={formData.otros_impuestos}
                      onChange={(val) => setFormData((prev) => ({ ...prev, otros_impuestos: val }))}
                    />
                  </div>
                  <div>
                    <label className="form-label">Observaciones (Pie de Factura)</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Observaciones adicionales..."
                      value={formData.observaciones}
                      onChange={(e) => setFormData((prev) => ({ ...prev, observaciones: e.target.value }))}
                    />
                  </div>
                </div>

                {/* Resumen de Totales antes de emitir */}
                <div
                  style={{
                    background: 'rgba(59, 130, 246, 0.08)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    padding: '16px',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                    gap: '12px',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Neto Gravado</span>
                    <div style={{ fontWeight: 600 }}>{formatCurrency(resumenCalculado.neto_total)}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Exento / No Grav.</span>
                    <div style={{ fontWeight: 600 }}>
                      {formatCurrency(resumenCalculado.importe_exento + resumenCalculado.importe_no_gravado)}
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>IVA Total</span>
                    <div style={{ fontWeight: 600 }}>{formatCurrency(resumenCalculado.iva_total)}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Percepciones</span>
                    <div style={{ fontWeight: 600 }}>{formatCurrency(resumenCalculado.otros_total)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>TOTAL A AUTORIZAR</span>
                    <div style={{ fontSize: '20px', fontWeight: 'bold', color: 'var(--primary-color)' }}>
                      {formatCurrency(resumenCalculado.importe_total)}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setIsModalOpen(false)}
                    disabled={emitting}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={emitting || resumenCalculado.importe_total <= 0}
                    style={{ width: 'auto', padding: '0 24px', height: '42px', fontWeight: 600 }}
                  >
                    {emitting ? 'Autorizando en ARCA...' : `Emitir ${tipoSeleccionadoInfo.nombre} en ARCA ⚡`}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default FacturacionArcaFinanzasPage;

