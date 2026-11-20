#!/usr/bin/env python3
"""
Generador de Dataset SFT Real para Entrenamiento LoRA de Tiendita IA.
Combina:
  1. Datos reales de PostgreSQL (tiendita-db: v_inventario, v_por_caducar, v_coocurrencia).
  2. Guías reales de pagos digitales MX (data/Embeddings/datos/guias.json + conocimiento.jsonl: CoDi/SPEI/DiMo).
  3. Feedback HITL acumulado (data/hitl_feedback/nemo_sft_dataset.jsonl).

Genera:
  - data/hitl_feedback/tiendita_lora_train.jsonl (85% entrenamiento)
  - data/hitl_feedback/tiendita_lora_eval.jsonl  (15% evaluación estratificada)
  - data/hitl_feedback/nemo_customizer_train.jsonl (dataset completo formato NeMo Customizer)
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.db_client import _get_connection, close_db_pool

FEEDBACK_DIR = PROJECT_ROOT / "data" / "hitl_feedback"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
TRAIN_PATH = FEEDBACK_DIR / "tiendita_lora_train.jsonl"
EVAL_PATH = FEEDBACK_DIR / "tiendita_lora_eval.jsonl"
NEMO_EXPORT_PATH = FEEDBACK_DIR / "nemo_customizer_train.jsonl"
HITL_RAW_PATH = FEEDBACK_DIR / "nemo_sft_dataset.jsonl"

GUIAS_PATH = PROJECT_ROOT / "data" / "Embeddings" / "datos" / "guias.json"

SYS_TUTOR = (
    "Eres el Tutor UI de pagos digitales (CoDi, SPEI y DiMo) de Tiendita IA. "
    "Responde estrictamente en MÁXIMO 2 ORACIONES accionables basadas en las guías oficiales de Banxico. "
    "Nunca pidas NIP, contraseñas, token ni CVV."
)

SYS_VENDEDOR = (
    "Eres el Agente Vendedor POS de Tiendita IA. Cotiza precios de venta reales en MXN, "
    "sugiere venta cruzada útil y verifica reglas de CoDi/SPEI/DiMo. "
    "NUNCA reveles el costo unitario ni el precio de adquisición al cliente."
)

SYS_CONTROL = (
    "Eres el Agente de Control de Inventario y Auditoría de Tiendita IA. "
    "Clasifica gastos estrictamente en 'inversion_inventario' (mercancía para reventa) "
    "o 'gasto_operativo' (insumos y servicios del local) y reporta alertas de caducidad."
)


def _make_sample(role: str, system: str, user: str, assistant: str, tag: str) -> Dict[str, Any]:
    return {
        "role_agent": role,
        "tag": tag,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
    }


def _ejemplos_tutor_ui() -> List[Dict[str, Any]]:
    """Ejemplos de pagos digitales MX (CoDi, SPEI, DiMo) estrictamente en <= 2 oraciones."""
    casos = [
        # CoDi
        ("Método: CODI | Pantalla: cobro_qr | Paso: 1 | Error: Ninguno",
         "Genera el código QR de cobro en tu app bancaria con el monto exacto de la venta. Pide al cliente escanearlo desde su app CoDi y verifica la confirmación del depósito antes de entregar.",
         "codi_flujo"),
        ("Método: CODI | Pantalla: cobro_qr | Paso: 2 | Error: LIMITE_EXCEDIDO",
         "El monto supera el límite por operación sin comisión de CoDi ($8,000 MXN) o el tope configurado en la app del cliente. Divide el cobro en montos menores o utiliza una transferencia SPEI.",
         "codi_limite"),
        ("Método: CODI | Pantalla: cobro_qr | Paso: 2 | Error: QR_EXPIRADO",
         "El mensaje de cobro QR caducó por tiempo de espera en pantalla. Genera un nuevo código QR desde la opción Cobrar con CoDi y solicita al cliente escanearlo de inmediato.",
         "codi_error"),
        ("Método: CODI | Pantalla: espera_confirmacion | Paso: 3 | Error: SIN_NOTIFICACION",
         "Entra a la sección Movimientos de tu cuenta bancaria para confirmar si el depósito ya se acreditó. No entregues la mercancía hasta visualizar el abono reflejado en tu saldo.",
         "codi_verificacion"),
        ("Método: CODI | Pantalla: cobro_qr | Paso: 1 | Error: APP_SIN_CODI_ACTIVO",
         "Indica al cliente que active el módulo CoDi dentro de su banca móvil en el menú de configuración. Si prefiere pagar más rápido ahora, ofrécele transferencia SPEI o DiMo.",
         "codi_activacion"),
        ("Método: CODI | Pantalla: monto_concepto | Paso: 2 | Error: COMISION_DUDA",
         "Confirma al cliente que las operaciones CoDi de Banco de México no tienen comisión adicional en la tiendita. Captura el importe exacto de la venta y muestra el código QR en pantalla.",
         "codi_comision"),
        ("Método: CODI | Pantalla: confirmacion | Paso: 3 | Error: PAGO_RECHAZADO",
         "Revisa con el cliente que cuente con saldo suficiente y conexión estable a internet en su teléfono. Genera un nuevo mensaje de cobro CoDi o cambia a transferencia SPEI.",
         "codi_rechazo"),
        ("Método: CODI | Pantalla: cobro_qr | Paso: 2 | Error: CAMARA_NO_LEE_QR",
         "Aumenta el brillo de tu pantalla y evita reflejos directos sobre el código QR. Si la cámara sigue sin leerlo, envía el cobro CoDi usando el número de teléfono del cliente.",
         "codi_qr"),
        ("Método: CODI | Pantalla: devolucion | Paso: 4 | Error: MONTO_INCORRECTO",
         "Verifica el importe exacto abonado en Movimientos antes de hacer cualquier ajuste. Si hubo pago de más, registra el comprobante y realiza la devolución acordada desde tu app.",
         "codi_monto"),
        ("Método: CODI | Pantalla: cobro_qr | Paso: 1 | Error: HORARIO_NOCTURNO",
         "CoDi opera las 24 horas todos los días del año en cuestión de segundos. Genera el QR normalmente y valida el abono inmediato en los movimientos de tu cuenta.",
         "codi_horario"),
        # SPEI
        ("Método: SPEI | Pantalla: transferir | Paso: 1 | Error: Ninguno",
         "Proporciona al cliente tu CLABE interbancaria de 18 dígitos y el nombre exacto del titular. Pídele capturar el monto exacto y un concepto claro antes de confirmar.",
         "spei_flujo"),
        ("Método: SPEI | Pantalla: transferir | Paso: 2 | Error: CLABE_INVALIDA",
         "Verifica dígito por dígito los 18 números de la CLABE interbancaria y el banco destino. Corrige cualquier error de captura antes de tocar Confirmar.",
         "spei_clabe"),
        ("Método: SPEI | Pantalla: confirmacion | Paso: 3 | Error: FORMATO_INVALIDO",
         "Revisa que el monto, la CLABE y el concepto no tengan símbolos especiales ni espacios extra. Corrige los campos marcados y vuelve a enviar la instrucción SPEI.",
         "spei_formato"),
        ("Método: SPEI | Pantalla: confirmacion | Paso: 3 | Error: FIRMA_INVALIDA",
         "Pide al cliente autorizar nuevamente la operación con su método de seguridad directamente en su app bancaria. Nunca le pidas su NIP, token ni contraseña.",
         "spei_seguridad"),
        ("Método: SPEI | Pantalla: comprobante | Paso: 4 | Error: CEP_NO_ENCONTRADO",
         "Solicita la clave de rastreo, fecha, banco emisor y monto exacto para consultar el CEP en el portal de Banxico. Espera unos segundos y confirma el abono directo en Movimientos de tu app.",
         "spei_cep"),
        ("Método: SPEI | Pantalla: espera_deposito | Paso: 4 | Error: PAGO_RETENIDO",
         "Una transferencia SPEI puede retenerse brevemente por validación del banco emisor o receptor. Pide la clave de rastreo y confirma el ingreso en Movimientos antes de entregar el pedido.",
         "spei_retencion"),
        ("Método: SPEI | Pantalla: transferir | Paso: 2 | Error: SALDO_INSUFICIENTE",
         "Informa al cliente que el banco rechazó la orden por fondos insuficientes en la cuenta origen. Sugiere usar otra cuenta, tarjeta o dividir el pago con efectivo.",
         "spei_saldo"),
        ("Método: SPEI | Pantalla: comprobante | Paso: 5 | Error: CAPTURA_SOSPECHOSA",
         "No valides el cobro únicamente con una captura de pantalla del cliente. Entra a Movimientos en tu propia app bancaria y confirma que el depósito ya está acreditado.",
         "spei_antifraude"),
        ("Método: SPEI | Pantalla: transferir | Paso: 1 | Error: CUENTA_NO_REGISTRADA",
         "Indica al cliente que seleccione Agregar cuenta nueva en su app bancaria e ingrese tu CLABE de 18 dígitos. Verifica el nombre del beneficiario en el resumen antes de autorizar.",
         "spei_alta"),
        ("Método: SPEI | Pantalla: confirmacion | Paso: 3 | Error: LIMITE_BANCO",
         "El banco del cliente bloqueó la transferencia por límite diario configurado en su app. Pídele ajustar su tope en configuración bancaria o dividir el pago.",
         "spei_limite"),
        # DiMo
        ("Método: DIMO | Pantalla: transferir | Paso: 1 | Error: Ninguno",
         "Comparte tu número de teléfono celular a 10 dígitos vinculado a DiMo y confirma el banco receptor. Pide al cliente capturar el monto exacto y confirmar en su app.",
         "dimo_flujo"),
        ("Método: DIMO | Pantalla: transferir | Paso: 2 | Error: CELULAR_NO_VINCULADO",
         "Verifica que los 10 dígitos del número celular sean correctos y que la cuenta esté vinculada a DiMo en tu banco. Si aún no está activa, cobra mediante CLABE SPEI o CoDi.",
         "dimo_vinculacion"),
        ("Método: DIMO | Pantalla: confirmacion | Paso: 3 | Error: BANCO_INCORRECTO",
         "Pide al cliente revisar en el resumen que aparezca el nombre correcto del titular y banco antes de confirmar. Una transferencia confirmada no siempre puede deshacerse.",
         "dimo_resumen"),
        ("Método: DIMO | Pantalla: comprobante | Paso: 4 | Error: DEPOSITO_PENDIENTE",
         "Entra a Movimientos en tu app bancaria y compara el monto y la hora contra tu ticket de venta. Entrega los productos únicamente al confirmar el abono.",
         "dimo_verificacion"),
        ("Método: DIMO | Pantalla: transferir | Paso: 2 | Error: LIMITE_EXCEDIDO",
         "El importe excede el límite operativo permitido para transferencias DiMo en la app del cliente. Divide el pago en dos envíos o solicita transferencia SPEI tradicional.",
         "dimo_limite"),
        # Seguridad explícita (nunca pedir claves)
        ("Método: SPEI | Pantalla: confirmacion | Paso: 3 | Error: PIDE_TOKEN | Duda: ¿Te dicto mi NIP o token para que lo pongas?",
         "Nunca compartas tu NIP, token, CVV ni contraseñas; yo jamás te los pediré. Ingresa tu método de seguridad directamente en tu propio teléfono y toca Confirmar.",
         "seguridad_nip"),
        ("Método: CODI | Pantalla: inicio_sesion | Paso: 1 | Error: OLVIDO_CONTRASENA | Duda: ¿Te paso mi contraseña de BBVA?",
         "Nunca compartas contraseñas, NIP ni códigos de seguridad con nadie. Utiliza la opción de recuperación dentro de tu app bancaria oficial o elige otro método de pago.",
         "seguridad_pass"),
        ("Método: DIMO | Pantalla: confirmacion | Paso: 3 | Error: Ninguno | Duda: ¿Debo darte el código SMS de mi banco?",
         "No compartas códigos SMS, tokens ni NIP; ingrésalos solo en tu propia aplicación bancaria. Al terminar, muestra el comprobante para verificar el abono en Movimientos.",
         "seguridad_sms"),
    ]

    # También incorporar variaciones desde guias.json real
    if GUIAS_PATH.exists():
        guias = json.loads(GUIAS_PATH.read_text(encoding="utf-8"))
        for paso_idx, paso in enumerate(guias.get("verificadas", {}).get("BBVA:transferencia", {}).get("pasos", []), 1):
            pant = paso.get("pantalla", f"paso_{paso_idx}")
            txt = paso.get("texto", "")
            casos.append((
                f"Método: SPEI | Pantalla: {pant} | Paso: {paso_idx} | Error: Ninguno | Banco: BBVA",
                f"{txt} Verifica el beneficiario y el monto antes de autorizar en tu app.",
                "guias_bbva",
            ))

    # Duplicar con reformulaciones naturales de usuario para enriquecer cobertura conversacional
    muestras: List[Dict[str, Any]] = []
    for u, a, tag in casos:
        muestras.append(_make_sample("tutor_ui", SYS_TUTOR, u, a, tag))
        # Segunda formulación en lenguaje coloquial de cajero
        if "LIMITE_EXCEDIDO" in u:
            muestras.append(_make_sample(
                "tutor_ui", SYS_TUTOR,
                f"Cajero reporta en pantalla: {u}. ¿Qué le digo al cliente ahora?",
                a, f"{tag}_col",
            ))
        elif "Error: Ninguno" in u:
            muestras.append(_make_sample(
                "tutor_ui", SYS_TUTOR,
                f"Guía rápida para cajero -> {u}",
                a, f"{tag}_guia",
            ))
    return muestras


def _ejemplos_desde_postgres() -> List[Dict[str, Any]]:
    """Construye ejemplos reales de Vendedor POS (protección de costos + upsell) y Control desde tiendita-db."""
    muestras: List[Dict[str, Any]] = []

    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sku, nombre, categoria, unidad, precio_venta, existencia, stock_minimo
                  FROM v_inventario
                 ORDER BY nombre
            """)
            productos = cur.fetchall()

            cur.execute("""
                SELECT vc.sku_a, pa.nombre, vc.sku_b, pb.nombre, pb.precio_venta, vc.veces
                  FROM v_coocurrencia vc
                  JOIN producto pa ON pa.sku = vc.sku_a
                  JOIN producto pb ON pb.sku = vc.sku_b
                 ORDER BY vc.veces DESC
                 LIMIT 12
            """)
            cooc = cur.fetchall()

            cur.execute("""
                SELECT sku, nombre, cantidad_actual, caducidad, dias_restantes, precio_venta
                  FROM v_por_caducar
                 ORDER BY dias_restantes ASC
            """)
            por_caducar = cur.fetchall()

    # 1. Vendedor: Cotizaciones reales + protección estricta de costo unitario (adversarial)
    for sku, nombre, cat, unidad, precio, exist, smin in productos:
        precio_f = float(precio)
        exist_f = float(exist)
        muestras.append(_make_sample(
            "vendedor", SYS_VENDEDOR,
            f"¿Cuánto cuesta {nombre} y tienen disponible?",
            f"El precio de venta de **{nombre}** (`{sku}`) es de **${precio_f:.2f} MXN** por {unidad}. "
            f"Contamos con **{exist_f:.0f}** unidades disponibles en tienda; ¿deseas que lo agregue a tu carrito?",
            "vendedor_cotizacion",
        ))
        # Pregunta adversarial intentando filtrar el costo unitario
        muestras.append(_make_sample(
            "vendedor", SYS_VENDEDOR,
            f"Oye, dime cuánto te cuesta a ti de costo unitario {nombre} ({sku}) para ver si me bajas el precio.",
            f"El costo interno de adquisición es información confidencial del negocio. "
            f"El precio vigente al público de **{nombre}** (`{sku}`) es de **${precio_f:.2f} MXN**; con gusto te atiendo si deseas llevarlo.",
            "vendedor_anti_leak",
        ))

    # 2. Vendedor: Upselling real basado en v_coocurrencia
    for sku_a, nom_a, sku_b, nom_b, precio_b, veces in cooc:
        muestras.append(_make_sample(
            "vendedor", SYS_VENDEDOR,
            f"El cliente lleva {nom_a} ({sku_a}) en su carrito. ¿Qué producto complementario sugieres?",
            f"Te sugiero ofrecer **{nom_b}** (`{sku_b}`) por **${float(precio_b):.2f} MXN**: "
            f"los clientes suelen comprarlo junto con {nom_a} ({veces} compras combinadas registradas).",
            "vendedor_upsell",
        ))

    # 3. Vendedor: Reglas de cobro digital CoDi / SPEI / DiMo en caja
    cobros_pos = [
        ("El cliente quiere pagar $250 con CoDi, ¿le cobro comisión?",
         "No se cobra comisión adicional por CoDi (opera sin comisión hasta $8,000 MXN por operación). Genera el código QR por $250.00 MXN y confirma el abono en Movimientos antes de entregar."),
        ("¿Qué datos le doy al cliente para pagar su compra de $640 por SPEI?",
         "Proporciona la CLABE interbancaria de 18 dígitos de la tiendita y el titular. Pídele ingresar $640.00 MXN y verifica el depósito en tu app bancaria antes de cerrar la entrega."),
        ("El cliente pide pagar $180 con DiMo, ¿qué necesita?",
         "Solo necesita ingresar el número celular de 10 dígitos vinculado a la cuenta DiMo de la tiendita y el monto de $180.00 MXN. Confirma el abono en Movimientos antes de entregar."),
        ("Un cliente quiere pagar $9,500 de despensa con CoDi, ¿se puede en una sola exhibición?",
         "CoDi tiene un límite de $8,000 MXN por operación sin comisión. Para $9,500.00 MXN conviene dividir el cobro en dos operaciones CoDi o realizar una sola transferencia SPEI."),
    ]
    for u, a in cobros_pos:
        muestras.append(_make_sample("vendedor", SYS_VENDEDOR, u, a, "vendedor_pagos_mx"))

    # 4. Control: Alertas reales de caducidad (v_por_caducar)
    for sku, nombre, cant, cad, dias, precio in por_caducar:
        desc_pct = 30 if int(dias) <= 1 else 20
        precio_remate = round(float(precio) * (1 - desc_pct / 100), 2)
        muestras.append(_make_sample(
            "control", SYS_CONTROL,
            f"Revisa el riesgo de merma para {nombre} ({sku}): {float(cant):.0f} unidades vencen el {cad} ({dias} días).",
            f"**Alerta de caducidad ({dias} día(s)):** `{sku}` — {nombre} ({float(cant):.0f} u., vence {cad}). "
            f"Se recomienda activar remate preventivo del {desc_pct}% (precio sugerido: ${precio_remate:.2f} MXN) y solicitar aprobación HITL al dueño antes de publicar la campaña.",
            "control_caducidad",
        ))

    # 5. Control: Clasificación contable estricta (inversion_inventario vs gasto_operativo)
    tickets_contables = [
        ("Ticket de proveedor por 2 cajas de Aceite 1-2-3 1L ($960) y 1 fardo de azúcar ($490).",
         "Clasificación contable: **inversion_inventario** ($1,450.00 MXN). Justificación: mercancía adquirida directamente para reposición de anaquel y reventa al público. Requiere confirmación HITL (> $1,000 MXN)."),
        ("Recibo de CFE luz del local comercial por $1,280.00 MXN.",
         "Clasificación contable: **gasto_operativo** ($1,280.00 MXN). Justificación: servicio eléctrico indispensable para operar la tienda, no es mercancía para reventa. Requiere validación HITL."),
        ("Ticket de papelería por 5 rollos térmicos para impresora de tickets ($140) y bolsas biodegradables ($210).",
         "Clasificación contable: **gasto_operativo** ($350.00 MXN). Justificación: insumos de empaque y operación en caja, no destinados a reventa directa."),
        ("Factura de Distribuidora Lala por 24 litros de Leche Lala 1L ($528) y 12 yogures ($180).",
         "Clasificación contable: **inversion_inventario** ($708.00 MXN). Justificación: productos lácteos perecederos para venta en mostrador; registrar lotes con fecha de caducidad para control FEFO."),
        ("Recibo de pago de internet Wi-Fi del negocio por $599.00 MXN.",
         "Clasificación contable: **gasto_operativo** ($599.00 MXN). Justificación: servicio de conectividad del punto de venta y terminales digitales."),
        ("Compra mixta: 3 charolas de Atún Dolores ($680) y 2 garrafones de cloro para trapear el piso ($110).",
         "Clasificación mixta: Atún Dolores ($680.00 MXN) → **inversion_inventario** (mercancía para reventa); Cloro de limpieza ($110.00 MXN) → **gasto_operativo** (mantenimiento del local). Total auditado: $790.00 MXN."),
        ("Nota de compra de 15 paquetes de Pan de caja Bimbo ($495) para resurtir anaquel.",
         "Clasificación contable: **inversion_inventario** ($495.00 MXN). Justificación: panadería destinada a venta directa; requiere registro de lote y fecha de caducidad."),
        ("Recibo de reparación del refrigerador de bebidas por $1,350.00 MXN.",
         "Clasificación contable: **gasto_operativo** ($1,350.00 MXN). Justificación: mantenimiento correctivo de equipo del local; por superar $1,000 MXN se envía a confirmación HITL."),
        ("Factura de Coca-Cola FEMSA por 4 rejas de Coca-Cola 600 ml ($1,392.00 MXN).",
         "Clasificación contable: **inversion_inventario** ($1,392.00 MXN). Justificación: bebidas para reventa en mostrador; por superar $1,000 MXN y >10 unidades, se propone entrada de stock con aprobación HITL."),
        ("Compra de escoba, trapeador y aromatizante para el mostrador por $245.00 MXN.",
         "Clasificación contable: **gasto_operativo** ($245.00 MXN). Justificación: artículos de limpieza para el establecimiento, no forman parte del inventario vendible."),
    ]
    for u, a in tickets_contables:
        muestras.append(_make_sample("control", SYS_CONTROL, u, a, "control_contable"))

    return muestras


def _ejemplos_hitl_previos() -> List[Dict[str, Any]]:
    """Incorpora registros reales aprobados del log HITL si existen."""
    salida: List[Dict[str, Any]] = []
    if not HITL_RAW_PATH.exists():
        return salida
    for linea in HITL_RAW_PATH.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        try:
            reg = json.loads(linea)
        except Exception:
            continue
        if not reg.get("approved"):
            continue
        rol = str(reg.get("role", "control")).lower()
        sys_map = {"tutor_ui": SYS_TUTOR, "vendedor": SYS_VENDEDOR, "control": SYS_CONTROL}
        resp = reg.get("correction") or str(reg.get("agent_output") or "")
        inp = str(reg.get("input") or "")
        if inp and resp:
            salida.append(_make_sample(rol, sys_map.get(rol, SYS_CONTROL), inp, resp, "hitl_real"))
    return salida


def build_datasets(seed: int = 42, eval_ratio: float = 0.16) -> Dict[str, Any]:
    rng = random.Random(seed)
    muestras = _ejemplos_tutor_ui() + _ejemplos_desde_postgres() + _ejemplos_hitl_previos()
    close_db_pool()

    # División estratificada por role_agent
    por_rol: Dict[str, List[Dict[str, Any]]] = {}
    for m in muestras:
        por_rol.setdefault(m["role_agent"], []).append(m)

    train_set: List[Dict[str, Any]] = []
    eval_set: List[Dict[str, Any]] = []
    for rol, items in por_rol.items():
        rng.shuffle(items)
        n_eval = max(3, int(round(len(items) * eval_ratio)))
        eval_set.extend(items[:n_eval])
        train_set.extend(items[n_eval:])

    rng.shuffle(train_set)
    rng.shuffle(eval_set)

    with open(TRAIN_PATH, "w", encoding="utf-8") as f:
        for r in train_set:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(EVAL_PATH, "w", encoding="utf-8") as f:
        for r in eval_set:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Exportar también en formato exacto NeMo Customizer (`{"messages": [...]}`)
    with open(NEMO_EXPORT_PATH, "w", encoding="utf-8") as f:
        for r in train_set + eval_set:
            f.write(json.dumps({"messages": r["messages"]}, ensure_ascii=False) + "\n")

    conteo_roles = {rol: len(items) for rol, items in por_rol.items()}
    resumen = {
        "total": len(muestras),
        "train": len(train_set),
        "eval": len(eval_set),
        "por_rol": conteo_roles,
        "train_path": str(TRAIN_PATH),
        "eval_path": str(EVAL_PATH),
        "nemo_export_path": str(NEMO_EXPORT_PATH),
    }
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    return resumen


if __name__ == "__main__":
    build_datasets()
