import asyncio
import base64
import io
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import HTTPException, UploadFile

import src.services.arca_service as arca_service
from src.api.routes.facturacion import generar_qr_afip_url
from src.api.routes.system import (
    ArcaConfigUpdateSchema,
    ArcaGenerarCsrSchema,
    download_arca_csr_endpoint,
    download_arca_key_endpoint,
    generate_arca_csr_endpoint,
    get_arca_system_status,
    test_arca_connection_endpoint as probar_conexion_arca_endpoint,
    update_arca_system_config,
    upload_arca_certificate_endpoint,
)
from src.config import COMPANY_DATA
from src.database.models.creditos.facturacion import Factura


@pytest.fixture
def isolated_arca_dir(tmp_path, monkeypatch):
    """Redirige todos los archivos de ARCA a un directorio temporal aislado por test."""
    certs_dir = tmp_path / "certs" / "arca"
    monkeypatch.setattr(arca_service, "ARCA_CERTS_DIR", certs_dir)
    monkeypatch.setattr(arca_service, "ARCA_CONFIG_PATH", certs_dir / "arca_config.json")
    monkeypatch.setattr(arca_service, "ARCA_KEY_PATH", certs_dir / "arca.key")
    monkeypatch.setattr(arca_service, "ARCA_CSR_PATH", certs_dir / "arca.csr")
    monkeypatch.setattr(arca_service, "ARCA_CRT_PATH", certs_dir / "arca.crt")
    monkeypatch.setattr(arca_service, "ARCA_TA_CACHE_PATH", certs_dir / "arca_ta_cache.json")
    return certs_dir


def _build_synthetic_cert_pem(
    private_key: rsa.RSAPrivateKey,
    subject: x509.Name,
    days_valid: int,
    serial_number: int = 1001,
) -> bytes:
    """Construye un certificado X.509 autofirmado sintético en memoria."""
    now = datetime.now(timezone.utc)
    if days_valid >= 0:
        not_before = now - timedelta(days=1)
        not_after = now + timedelta(days=days_valid)
    else:
        not_before = now + timedelta(days=days_valid - 10)
        not_after = now + timedelta(days=days_valid)

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(serial_number)
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .sign(private_key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM)


def test_generar_key_rsa_2048_y_csr_atributos_x509(isolated_arca_dir):
    """
    1. Valida la generación de arca.key (RSA 2048 bits) y arca.csr con los
    atributos fiscales X.509 requeridos en Argentina (C=AR, O=..., CN=..., serialNumber=CUIT ...).
    """
    res = arca_service.generar_key_y_csr(
        cuit="30-71234567-8",
        razon_social="Yoyo S.A.",
        alias="yoyo-wsfe",
    )

    assert (isolated_arca_dir / "arca.key").is_file()
    assert (isolated_arca_dir / "arca.csr").is_file()

    private_key = serialization.load_pem_private_key(
        (isolated_arca_dir / "arca.key").read_bytes(),
        password=None,
    )
    assert isinstance(private_key, rsa.RSAPrivateKey)
    assert private_key.key_size == 2048

    csr = x509.load_pem_x509_csr(res["csr_pem"].encode("utf-8"))
    assert csr.is_signature_valid

    country = csr.subject.get_attributes_for_oid(NameOID.COUNTRY_NAME)[0].value
    org = csr.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
    cn = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    serial_attr = csr.subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)[0].value

    assert country == "AR"
    assert org == "Yoyo S.A."
    assert cn == "yoyo-wsfe"
    assert serial_attr == "CUIT 30712345678"

    # Verificar descarga por endpoints REST
    resp_csr = generate_arca_csr_endpoint(
        ArcaGenerarCsrSchema(cuit="30712345678", razon_social="Yoyo S.A.", alias="yoyo-wsfe"),
        current_user=None,
    )
    assert b"BEGIN CERTIFICATE REQUEST" in resp_csr.body
    assert download_arca_csr_endpoint(current_user=None).body == resp_csr.body
    assert b"PRIVATE KEY" in download_arca_key_endpoint(current_user=None).body


def test_subir_certificado_coincidente_y_rechazo_http_400_no_coincidente(isolated_arca_dir):
    """
    2. Valida la carga exitosa de un .crt sintético correspondiente a la .key generada
    y verifica el rechazo con HTTP 400 cuando el .crt pertenece a otra clave privada
    o tiene formato PEM inválido.
    """
    csr_info = arca_service.generar_key_y_csr(
        cuit="30712345678",
        razon_social="Yoyo S.A.",
        alias="yoyo-wsfe",
    )
    key_local = serialization.load_pem_private_key(
        (isolated_arca_dir / "arca.key").read_bytes(),
        password=None,
    )
    csr_obj = x509.load_pem_x509_csr(csr_info["csr_pem"].encode("utf-8"))

    # Certificado firmado con UNA CLAVE DISTINTA -> debe rechazarse con HTTP 400
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    mismatched_crt_pem = _build_synthetic_cert_pem(other_key, csr_obj.subject, days_valid=30)

    with pytest.raises(HTTPException) as exc_mismatch:
        upload_arca_certificate_endpoint(
            crt_file=UploadFile(filename="bad.crt", file=io.BytesIO(mismatched_crt_pem)),
            current_user=None,
        )
    assert exc_mismatch.value.status_code == 400
    assert "no coincide" in exc_mismatch.value.detail.lower()

    # Archivo PEM inválido -> debe rechazarse con HTTP 400
    with pytest.raises(HTTPException) as exc_invalid_pem:
        upload_arca_certificate_endpoint(
            crt_file=UploadFile(filename="corrupt.crt", file=io.BytesIO(b"NO ES UN CERTIFICADO")),
            current_user=None,
        )
    assert exc_invalid_pem.value.status_code == 400

    # Certificado firmado con la clave correcta -> validación exitosa
    valid_crt_pem = _build_synthetic_cert_pem(key_local, csr_obj.subject, days_valid=45, serial_number=98765)
    upload_res = upload_arca_certificate_endpoint(
        crt_file=UploadFile(filename="arca.crt", file=io.BytesIO(valid_crt_pem)),
        current_user=None,
    )
    assert upload_res["status"] == "success"
    assert upload_res["estado_vigencia"] == "VIGENTE"
    assert upload_res["dias_restantes"] == 45
    assert upload_res["alerta_vencimiento"] is False
    assert upload_res["serial_number"] == "98765"


def test_calculo_alerta_vencimiento_y_estados(isolated_arca_dir):
    """
    3. Verifica el cálculo correcto de alerta_vencimiento y estado_vigencia:
      - SIN_CERTIFICADO -> alerta_vencimiento = False
      - > 5 días (ej. 20 días) -> VIGENTE, alerta_vencimiento = False
      - <= 5 días (ej. 5 y 2 días) -> PROXIMO_A_VENCER, alerta_vencimiento = True
      - < 0 días (ya vencido) -> VENCIDO, alerta_vencimiento = True
    """
    # Estado inicial sin certificado
    st_empty = get_arca_system_status(current_user=None)
    assert st_empty["estado_vigencia"] == "SIN_CERTIFICADO"
    assert st_empty["alerta_vencimiento"] is False

    csr_info = arca_service.generar_key_y_csr("30712345678", "Yoyo S.A.", "yoyo-wsfe")
    key_local = serialization.load_pem_private_key(
        (isolated_arca_dir / "arca.key").read_bytes(),
        password=None,
    )
    subject = x509.load_pem_x509_csr(csr_info["csr_pem"].encode("utf-8")).subject

    # Caso A: Vence en 20 días (> 5 días) -> VIGENTE, alerta_vencimiento = False
    crt_20d = _build_synthetic_cert_pem(key_local, subject, days_valid=20)
    arca_service.guardar_y_validar_certificado(crt_20d)
    st_vigente = get_arca_system_status(current_user=None)
    assert st_vigente["estado_vigencia"] == "VIGENTE"
    assert st_vigente["dias_restantes"] == 20
    assert st_vigente["alerta_vencimiento"] is False

    # Caso B: Vence en exactamente 5 días (<= 5 días) -> PROXIMO_A_VENCER, alerta_vencimiento = True
    crt_5d = _build_synthetic_cert_pem(key_local, subject, days_valid=5)
    arca_service.guardar_y_validar_certificado(crt_5d)
    st_5d = get_arca_system_status(current_user=None)
    assert st_5d["estado_vigencia"] == "PROXIMO_A_VENCER"
    assert st_5d["dias_restantes"] == 5
    assert st_5d["alerta_vencimiento"] is True

    # Caso C: Vence en 2 días (<= 5 días) -> PROXIMO_A_VENCER, alerta_vencimiento = True
    crt_2d = _build_synthetic_cert_pem(key_local, subject, days_valid=2)
    arca_service.guardar_y_validar_certificado(crt_2d)
    st_2d = get_arca_system_status(current_user=None)
    assert st_2d["estado_vigencia"] == "PROXIMO_A_VENCER"
    assert st_2d["dias_restantes"] == 2
    assert st_2d["alerta_vencimiento"] is True

    # Prueba de conexión en modo mock con certificado vigente/próximo a vencer
    conn_ok = probar_conexion_arca_endpoint(current_user=None)
    assert conn_ok["ok"] is True
    assert conn_ok["environment"] == "mock"

    # Caso D: Ya venció (-3 días) -> VENCIDO, alerta_vencimiento = True
    crt_expired = _build_synthetic_cert_pem(key_local, subject, days_valid=-3)
    arca_service.guardar_y_validar_certificado(crt_expired)
    st_exp = get_arca_system_status(current_user=None)
    assert st_exp["estado_vigencia"] == "VENCIDO"
    assert st_exp["dias_restantes"] < 0
    assert st_exp["alerta_vencimiento"] is True

    # Actualizar configuración y verificar validaciones
    cfg_updated = update_arca_system_config(
        ArcaConfigUpdateSchema(
            environment="homologacion",
            cuit="30712345678",
            punto_venta_default=3,
            dias_alerta_vencimiento=10,
        ),
        current_user=None,
    )
    assert cfg_updated["environment"] == "homologacion"
    assert cfg_updated["punto_venta_default"] == 3
    assert cfg_updated["dias_alerta_vencimiento"] == 10

    # Verificar generación de URL QR RG 4892/2020
    fac = Factura(
        punto_venta=3,
        tipo_comprobante=1,
        nro_comprobante=42,
        fecha_emision=date(2026, 11, 13),
        cuit_cliente="30711122233",
        tipo_doc_receptor="CUIT",
        importe_total=121000.0,
        cae="74123456789012",
    )
    qr_url = generar_qr_afip_url(fac, COMPANY_DATA)
    assert qr_url.startswith("https://www.afip.gob.ar/fe/qr/?p=")
    decoded = json.loads(base64.b64decode(qr_url.split("?p=")[1]).decode("utf-8"))
    assert decoded["ver"] == 1
    assert decoded["ptoVta"] == 3
    assert decoded["tipoCmp"] == 1
    assert decoded["nroCmp"] == 42
    assert decoded["codAut"] == 74123456789012
    assert decoded["cuit"] == 30712345678


def test_wsfev1_soap_xsd_order_y_reglas_arca(isolated_arca_dir, monkeypatch):
    """
    4. Verifica la serialización SOAP de FECAEDetRequest contra el XSD de WSFEv1:
       - Orden estricto de nodos XML (<CondicionIVAReceptorId>, <CbtesAsoc>, <Tributos>, <Iva>, <Opcionales>)
       - Alícuota 0% (<Id>3</Id>)
       - Factura C (ImpNeto = subtotal, ImpOpEx = 0, ImpIVA = 0, sin <Iva>)
       - Bloqueo de Clase E (19, 20, 21) en homologación/producción
    """
    import xml.etree.ElementTree as ET
    from src.services.arca_service import ArcaService, ArcaServiceError

    arca_service.save_arca_config(
        {
            "environment": "homologacion",
            "cuit": "30712345678",
            "punto_venta_default": 4,
            "condicion_iva_emisor": "RESPONSABLE_INSCRIPTO",
            "nro_iibb": "901-888999-1",
            "inicio_actividades": "01/03/2021",
            "cbu_fce_default": "0720000720000000123456",
            "fce_sistema_circulacion": "SCA",
        }
    )

    captured_xmls = []

    def fake_creds(self, service: str = "wsfe"):
        return {"token": "TOK_TEST", "sign": "SIGN_TEST", "cuit": "30712345678"}

    def fake_soap_call(environment: str, soap_action: str, body_xml: str):
        captured_xmls.append((soap_action, body_xml))
        if soap_action == "FECompUltimoAutorizado":
            xml_resp = """<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <FECompUltimoAutorizadoResponse xmlns="http://ar.gov.afip.dif.FEV1/">
                  <FECompUltimoAutorizadoResult>
                    <CbteNro>10</CbteNro>
                  </FECompUltimoAutorizadoResult>
                </FECompUltimoAutorizadoResponse>
              </soap:Body>
            </soap:Envelope>"""
            return ET.fromstring(xml_resp)

        if soap_action == "FECAESolicitar":
            xml_resp = """<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <FECAESolicitarResponse xmlns="http://ar.gov.afip.dif.FEV1/">
                  <FECAESolicitarResult>
                    <FeCabResp><Resultado>A</Resultado></FeCabResp>
                    <FeDetResp>
                      <FECAEDetResponse>
                        <Resultado>A</Resultado>
                        <CAE>75000011112222</CAE>
                        <CAEFchVto>20261123</CAEFchVto>
                      </FECAEDetResponse>
                    </FeDetResp>
                  </FECAESolicitarResult>
                </FECAESolicitarResponse>
              </soap:Body>
            </soap:Envelope>"""
            return ET.fromstring(xml_resp)

        raise AssertionError(f"Unexpected SOAP action {soap_action}")

    monkeypatch.setattr(ArcaService, "obtener_ticket_acceso", fake_creds)
    monkeypatch.setattr(arca_service, "_call_wsfev1_soap", fake_soap_call)

    svc = ArcaService(use_mock=False)

    # Caso 1: Nota de Crédito FCE MiPyME A (203) con CbtesAsoc, Tributos, IVA (21% + 0%) y Opcional 22
    res_fce_nc = svc.emitir_factura(
        cuit_cliente="30711122233",
        tipo_doc_receptor="CUIT",
        tipo_comprobante=203,
        punto_venta=4,
        concepto=2,
        importe_total=126000.0,
        importe_no_gravado=0.0,
        importe_exento=0.0,
        neto_gravado_0=1000.0,
        neto_gravado_21=100000.0,
        iva_21=21000.0,
        percepcion_iva=1500.0,
        percepcion_iibb=2500.0,
        condicion_iva_receptor="Responsable Inscripto",
        comprobantes_asociados=[
            {
                "tipo": 201,
                "pto_vta": 4,
                "nro": 9,
                "cuit": "30712345678",
                "fecha": date(2026, 11, 1),
            }
        ],
        fce_anulacion="N",
    )
    assert res_fce_nc["cae"] == "75000011112222"
    assert res_fce_nc["nro_comprobante"] == 11

    _, fecae_xml = captured_xmls[-1]
    root = ET.fromstring(fecae_xml)
    det = next(el for el in root.iter() if el.tag.endswith("FECAEDetRequest"))
    child_tags = [ch.tag.split("}")[-1] for ch in list(det)]

    expected_order = [
        "Concepto",
        "DocTipo",
        "DocNro",
        "CbteDesde",
        "CbteHasta",
        "CbteFch",
        "ImpTotal",
        "ImpTotConc",
        "ImpNeto",
        "ImpOpEx",
        "ImpTrib",
        "ImpIVA",
        "FchServDesde",
        "FchServHasta",
        "MonId",
        "MonCotiz",
        "CondicionIVAReceptorId",
        "CbtesAsoc",
        "Tributos",
        "Iva",
        "Opcionales",
    ]
    assert child_tags == expected_order
    assert "<Id>3</Id>" in fecae_xml  # IVA 0%
    assert "<Id>5</Id>" in fecae_xml  # IVA 21%
    assert "<Id>22</Id><Valor>N</Valor>" in fecae_xml  # FCE Anulación

    # Caso 2: Factura C (11) -> ImpNeto = subtotal, ImpOpEx = 0, ImpIVA = 0, sin nodo <Iva>
    svc.emitir_factura(
        cuit_cliente="20301112223",
        tipo_doc_receptor="CUIT",
        tipo_comprobante=11,
        punto_venta=4,
        concepto=2,
        importe_total=15000.0,
        importe_exento=15000.0,
        condicion_iva_receptor="Monotributista",
    )
    _, fc_xml = captured_xmls[-1]
    assert "<ImpNeto>15000.00</ImpNeto>" in fc_xml
    assert "<ImpOpEx>0.00</ImpOpEx>" in fc_xml
    assert "<ImpIVA>0.00</ImpIVA>" in fc_xml
    assert "<Iva>" not in fc_xml

    # Caso 3: Factura E (19) bloqueada en entorno real
    with pytest.raises(ArcaServiceError) as exc_e:
        svc.emitir_factura(
            cuit_cliente="55000000018",
            tipo_comprobante=19,
            punto_venta=4,
            importe_total=1000.0,
            importe_exento=1000.0,
        )
    assert exc_e.value.code == "CLASE_E_NO_SOPORTADA"


def test_padron_a5_soap_parser(isolated_arca_dir, monkeypatch):
    """
    5. Verifica que ArcaConsultaService parsee correctamente la respuesta SOAP
       getPersona_v2 de ws_sr_constancia_inscripcion en modo real.
    """
    from src.services.arca_consulta import ArcaConsultaService

    arca_service.save_arca_config(
        {
            "environment": "homologacion",
            "cuit": "30712345678",
            "punto_venta_default": 1,
        }
    )

    monkeypatch.setattr(
        "src.services.arca_consulta.login_cms_wsaa",
        lambda env, service="ws_sr_constancia_inscripcion": {
            "token": "PADRON_TOKEN",
            "sign": "PADRON_SIGN",
        },
    )

    class FakeResponse:
        status_code = 200
        text = """<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <ns2:getPersona_v2Response xmlns:ns2="http://a5.soap.ws.server.puc.sr/">
              <personaReturn>
                <datosGenerales>
                  <idPersona>30712345678</idPersona>
                  <razonSocial>FINANCIERA DEL LITORAL S.A.</razonSocial>
                  <estadoClave>ACTIVO</estadoClave>
                  <tipoPersona>JURIDICA</tipoPersona>
                  <domicilioFiscal>
                    <direccion>AV CORRIENTES 1234</direccion>
                    <localidad>CABA</localidad>
                    <codPostal>1043</codPostal>
                    <descripcionProvincia>CIUDAD AUTONOMA BUENOS AIRES</descripcionProvincia>
                  </domicilioFiscal>
                </datosGenerales>
                <datosRegimenGeneral>
                  <impuesto>
                    <idImpuesto>30</idImpuesto>
                    <descripcionImpuesto>IVA</descripcionImpuesto>
                  </impuesto>
                </datosRegimenGeneral>
              </personaReturn>
            </ns2:getPersona_v2Response>
          </soap:Body>
        </soap:Envelope>"""

    monkeypatch.setattr(
        "src.services.arca_consulta.httpx.Client.post",
        lambda self, url, content=None, headers=None: FakeResponse(),
    )

    consulta = ArcaConsultaService(use_mock=False)
    res = consulta.consultar_cuit("30-71234567-8")
    assert res["cuit"] == "30712345678"
    assert res["razon_social"] == "FINANCIERA DEL LITORAL S.A."
    assert res["condicion_iva"] == "Responsable Inscripto"
    assert res["condicion_iva_receptor_id"] == 1
    assert res["domicilio_fiscal"] == "AV CORRIENTES 1234"
    assert res["provincia"] == "CIUDAD AUTONOMA BUENOS AIRES"
    assert res["estado_clave"] == "ACTIVO"


def test_arca_resiliencia_fchvtopago_neto_sin_iva_ta_cache_y_backup_key(isolated_arca_dir, monkeypatch):
    """
    6. Verifica:
       - Extracción de cuit_certificado y respaldo arca.active_backup.key al generar nuevo CSR
       - Invalidación de arca_ta_cache.json al cambiar certificado o CUIT/entorno
       - Ajuste de FchVtoPago >= today cuando fecha_emision es retroactiva
       - Reclasificación de neto_gravado_21 con iva_21=0 a AlicIva Id=3 (0%)
       - Resolución de alias en CbtesAsoc y advertencias en probar-conexion
    """
    import xml.etree.ElementTree as ET
    from src.services.arca_service import ArcaService

    # 1. Generar primer par key/csr y certificado activo
    arca_service.save_arca_config({"environment": "homologacion", "cuit": "30712345678", "punto_venta_default": 5})
    csr1 = arca_service.generar_key_y_csr("30712345678", "Yoyo S.A.", "alias-1")
    key1 = serialization.load_pem_private_key((isolated_arca_dir / "arca.key").read_bytes(), password=None)
    subj1 = x509.load_pem_x509_csr(csr1["csr_pem"].encode("utf-8")).subject
    crt1 = _build_synthetic_cert_pem(key1, subj1, days_valid=30, serial_number=111)
    arca_service.guardar_y_validar_certificado(crt1)

    st = get_arca_system_status(current_user=None)
    assert st["cuit_certificado"] == "30712345678"
    assert st["cuit_coincide_certificado"] is True
    assert st["key_matches_cert"] is True

    # Guardar un TA cacheado y verificar que sobrevive mientras no cambie config/cert
    arca_service._save_cached_ta("homologacion", "wsfe", "TOK_1", "SIGN_1", (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat())
    arca_service.save_arca_config({"environment": "homologacion", "cuit": "30712345678", "punto_venta_default": 5})
    assert arca_service._load_cached_ta("homologacion", "wsfe") is not None

    # Cambiar CUIT en config debe invalidar la caché de TA
    arca_service.save_arca_config({"environment": "homologacion", "cuit": "30799988877", "punto_venta_default": 5})
    assert arca_service._load_cached_ta("homologacion", "wsfe") is None
    st_diff = get_arca_system_status(current_user=None)
    assert st_diff["cuit_coincide_certificado"] is False

    # 2. Al generar un segundo CSR sin subir aún el nuevo .crt, debe conservar respaldo activo para firmar TRA
    arca_service.save_arca_config({"environment": "homologacion", "cuit": "30712345678", "punto_venta_default": 5})
    csr2 = arca_service.generar_key_y_csr("30712345678", "Yoyo S.A.", "alias-2")
    assert (isolated_arca_dir / "arca.active_backup.key").is_file()
    assert get_arca_system_status(current_user=None)["key_matches_cert"] is True
    tra = arca_service.generar_login_ticket_request("wsfe")
    cms_b64 = arca_service.firmar_tra_cms(tra)
    assert len(cms_b64) > 50

    # Al subir el segundo .crt coincidente con la nueva clave, se limpia el backup e invalida TA
    key2 = serialization.load_pem_private_key((isolated_arca_dir / "arca.key").read_bytes(), password=None)
    subj2 = x509.load_pem_x509_csr(csr2["csr_pem"].encode("utf-8")).subject
    crt2 = _build_synthetic_cert_pem(key2, subj2, days_valid=60, serial_number=222)
    arca_service._save_cached_ta("homologacion", "wsfe", "TOK_OLD", "SIGN_OLD", (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat())
    arca_service.guardar_y_validar_certificado(crt2)
    assert not (isolated_arca_dir / "arca.active_backup.key").exists()
    assert arca_service._load_cached_ta("homologacion", "wsfe") is None

    # 3. Verificar FchVtoPago >= today, neto_21 sin IVA -> Id=3, y CbtesAsoc con alias cortos
    captured = []
    monkeypatch.setattr(ArcaService, "obtener_ticket_acceso", lambda self, service="wsfe": {"token": "T", "sign": "S"})

    def fake_wsfe(environment, action, body_xml):
        captured.append((action, body_xml))
        if action == "FECompUltimoAutorizado":
            return ET.fromstring(
                '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
                '<FECompUltimoAutorizadoResponse xmlns="http://ar.gov.afip.dif.FEV1/">'
                '<FECompUltimoAutorizadoResult><CbteNro>5</CbteNro></FECompUltimoAutorizadoResult>'
                '</FECompUltimoAutorizadoResponse></soap:Body></soap:Envelope>'
            )
        if action == "FEParamGetPtosVenta":
            return ET.fromstring(
                '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
                '<FEParamGetPtosVentaResponse xmlns="http://ar.gov.afip.dif.FEV1/">'
                '<FEParamGetPtosVentaResult><ResultGet><PtoVenta><Nro>1</Nro><EmisionTipo>RECE</EmisionTipo><Bloqueado>N</Bloqueado></PtoVenta></ResultGet></FEParamGetPtosVentaResult>'
                '</FEParamGetPtosVentaResponse></soap:Body></soap:Envelope>'
            )
        if action == "FEDummy":
            return ET.fromstring(
                '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
                '<FEDummyResponse xmlns="http://ar.gov.afip.dif.FEV1/">'
                '<FEDummyResult><AppServer>OK</AppServer><DbServer>OK</DbServer><AuthServer>OK</AuthServer></FEDummyResult>'
                '</FEDummyResponse></soap:Body></soap:Envelope>'
            )
        return ET.fromstring(
            '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
            '<FECAESolicitarResponse xmlns="http://ar.gov.afip.dif.FEV1/">'
            '<FECAESolicitarResult><FeCabResp><Resultado>A</Resultado></FeCabResp>'
            '<FeDetResp><FECAEDetResponse><Resultado>A</Resultado><CAE>75000099998888</CAE><CAEFchVto>20261201</CAEFchVto></FECAEDetResponse></FeDetResp>'
            '</FECAESolicitarResult></FECAESolicitarResponse></soap:Body></soap:Envelope>'
        )

    monkeypatch.setattr(arca_service, "_call_wsfev1_soap", fake_wsfe)

    svc = ArcaService(use_mock=False)
    fecha_ayer = date.today() - timedelta(days=3)
    svc.emitir_factura(
        punto_venta=5,
        tipo_comprobante=8,  # NC B
        importe_total=1000.0,
        fecha_emision=fecha_ayer,
        tipo_doc_receptor="CF",
        cuit_cliente="99999999999",
        neto_gravado_21=1000.0,
        iva_21=0.0,
        comprobantes_asociados=[{"tipo": 6, "pto_vta": 5, "nro": 4, "fecha": fecha_ayer}],
    )
    _, xml_nc = captured[-1]
    assert f"<FchVtoPago>{date.today().strftime('%Y%m%d')}</FchVtoPago>" in xml_nc
    assert "<DocTipo>99</DocTipo><DocNro>0</DocNro>" in xml_nc
    assert "<AlicIva><Id>3</Id><BaseImp>1000.00</BaseImp><Importe>0.00</Importe></AlicIva>" in xml_nc
    assert "<Id>5</Id>" not in xml_nc
    assert "<Tipo>6</Tipo><PtoVta>5</PtoVta><Nro>4</Nro>" in xml_nc

    # 4. Probar conexión advierte que PV=5 no está entre los habilitados (solo está PV=1)
    conn_res = probar_conexion_arca_endpoint(current_user=None)
    assert conn_res["ok"] is True
    assert len(conn_res["advertencias"]) >= 1
    assert any("0005" in adv for adv in conn_res["advertencias"])


def test_auditoria_recuperacion_cae_der_mod11_y_rg5616(isolated_arca_dir, monkeypatch):
    """
    7. Verifica los hallazgos críticos y de seguridad implementados tras la auditoría técnica:
       - C-01: Recuperación automática de CAE vía FECompConsultar tras HTTP 502 en FECAESolicitar
               y persistencia en cae_recovery.jsonl ante error de guardado local
       - C-03: Validación Módulo 11 de CUIT y rechazo RG 5616 ante clase incompatible (ej. Factura A a Consumidor Final)
       - A-02: Soporte de certificado X.509 en formato DER binario (.cer) y cota de 64 KB en upload
    """
    import xml.etree.ElementTree as ET
    from src.services.arca_service import (
        ArcaService,
        ArcaServiceError,
        registrar_cae_contingencia,
        validar_compatibilidad_iva_receptor_comprobante,
        validar_cuit_mod11,
    )

    # 1. Validación Módulo 11
    assert validar_cuit_mod11("33-69345023-9") is True
    assert validar_cuit_mod11("30-71234567-8") is False
    assert validar_cuit_mod11("123") is False

    # 2. Matriz RG 5616: Factura A (1) no admite Consumidor Final (5) ni Exento (4)
    with pytest.raises(ArcaServiceError) as exc_rg:
        validar_compatibilidad_iva_receptor_comprobante(5, 1)
    assert exc_rg.value.code == "RG5616_CLASE_INCOMPATIBLE"

    with pytest.raises(ArcaServiceError) as exc_rg_b:
        validar_compatibilidad_iva_receptor_comprobante(1, 6)  # Factura B no admite RI (1)
    assert exc_rg_b.value.code == "RG5616_CLASE_INCOMPATIBLE"

    # Factura A admite Responsable Inscripto (1) y Monotributista (6)
    validar_compatibilidad_iva_receptor_comprobante(1, 1)
    validar_compatibilidad_iva_receptor_comprobante(6, 1)

    # 3. Certificado en formato DER binario (.cer) + límite 64 KB en endpoint
    csr_info = arca_service.generar_key_y_csr("33693450239", "ARCA Test SA", "arca-der")
    key_local = serialization.load_pem_private_key((isolated_arca_dir / "arca.key").read_bytes(), password=None)
    subj = x509.load_pem_x509_csr(csr_info["csr_pem"].encode("utf-8")).subject
    crt_pem = _build_synthetic_cert_pem(key_local, subj, days_valid=30, serial_number=333)
    crt_der = x509.load_pem_x509_certificate(crt_pem).public_bytes(serialization.Encoding.DER)

    up_der = upload_arca_certificate_endpoint(
        crt_file=UploadFile(filename="arca.cer", file=io.BytesIO(crt_der)),
        current_user=None,
    )
    assert up_der["status"] == "success"
    assert up_der["serial_number"] == "333"
    assert (isolated_arca_dir / "arca.crt").read_bytes().startswith(b"-----BEGIN CERTIFICATE-----")

    # Rechazo de archivo > 64 KB
    with pytest.raises(HTTPException) as exc_big:
        upload_arca_certificate_endpoint(
            crt_file=UploadFile(filename="giant.crt", file=io.BytesIO(b"A" * (65 * 1024))),
            current_user=None,
        )
    assert exc_big.value.status_code == 400

    # 4. Recuperación automática de CAE vía FECompConsultar ante fallo HTTP 502 en FECAESolicitar
    arca_service.save_arca_config({"environment": "homologacion", "cuit": "33693450239", "punto_venta_default": 2})
    monkeypatch.setattr(ArcaService, "obtener_ticket_acceso", lambda self, service="wsfe": {"token": "T", "sign": "S"})

    def fake_soap_recovery(environment, action, body_xml):
        if action == "FECompUltimoAutorizado":
            return ET.fromstring(
                '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
                '<FECompUltimoAutorizadoResponse xmlns="http://ar.gov.afip.dif.FEV1/">'
                '<FECompUltimoAutorizadoResult><CbteNro>20</CbteNro></FECompUltimoAutorizadoResult>'
                '</FECompUltimoAutorizadoResponse></soap:Body></soap:Envelope>'
            )
        if action == "FECAESolicitar":
            raise ArcaServiceError("Timeout esperando respuesta de ARCA", status_http=502)
        if action == "FECompConsultar":
            return ET.fromstring(
                '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
                '<FECompConsultarResponse xmlns="http://ar.gov.afip.dif.FEV1/">'
                '<FECompConsultarResult><ResultGet>'
                '<CodAutorizacion>75000088889999</CodAutorizacion>'
                '<FchVto>20261127</FchVto>'
                '<CbteFch>20261117</CbteFch>'
                '<ImpTotal>1210.00</ImpTotal>'
                '<Resultado>A</Resultado>'
                '</ResultGet></FECompConsultarResult>'
                '</FECompConsultarResponse></soap:Body></soap:Envelope>'
            )
        raise AssertionError(f"Unexpected SOAP action {action}")

    monkeypatch.setattr(arca_service, "_call_wsfev1_soap", fake_soap_recovery)
    svc = ArcaService(use_mock=False)
    res_rec = svc.emitir_factura(
        punto_venta=2,
        tipo_comprobante=1,
        importe_total=1210.0,
        cuit_cliente="33693450239",
        condicion_iva_receptor="Responsable Inscripto",
    )
    assert res_rec["nro_comprobante"] == 21
    assert res_rec["cae"] == "75000088889999"
    assert "FECompConsultar" in res_rec["observaciones_arca"][0]

    # 5. Bitácora de contingencia CAE local
    registrar_cae_contingencia(res_rec, "DB connection lost")
    recovery_file = isolated_arca_dir / "cae_recovery.jsonl"
    assert recovery_file.is_file()
    assert "75000088889999" in recovery_file.read_text(encoding="utf-8")



