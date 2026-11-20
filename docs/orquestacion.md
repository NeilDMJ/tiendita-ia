# Orquestación de agentes

Un solo chat (`POST /chat`). El **orquestador** elige al agente; cada agente tiene sus herramientas sobre la base de datos. Todos usan el mismo modelo (LLM/LoRA) con distinto prompt de rol. Sin `LLM_URL`/`NVIDIA_API_KEY` funciona en **modo simulado** con reglas (la respuesta lo indica con `simulado: true`).

## Flujo

```
Mensaje ─► /chat {texto, sesion_id}
  1. Ruteo: sesión (si el agente pidió datos) → LLM → reglas de respaldo
  2. El agente propone {tool, args, respuesta}
  3. Se completa con la sesión (carrito, método, última venta) y se valida
     · faltan datos      → pregunta al vendedor (el mismo agente sigue activo)
     · tool de LECTURA   → se ejecuta y responde
     · tool de ESCRITURA → propuesta con requiere_confirmacion=true
  4. "sí" en el chat, o POST /confirmar {tool,args} → se ejecuta (transacción); "no" cancela
  5. Respuesta: {agente, ruteo, tool, args, respuesta, faltantes, requiere_confirmacion,
                 resultado, fuentes[bd|externa], delegaciones[]}
Proactivo: GET /alertas → avisos que "dice" cada agente (stock bajo → Control,
           por caducar → Publicista ofrece promoción, pagos sin conciliar → Vendedor/Control)
```

Si el modelo propone una herramienta de otro rol, el orquestador **delega** en su dueño (`ruteo: "...+delegado"`). El Analista consulta a Control e Investigador al generar un reporte; el Publicista pide a Control los productos por caducar (`delegaciones`).

## Agentes y herramientas (L = lectura, E = escritura con confirmación)

| Agente | Herramientas |
|---|---|
| **Control** | `consultar_inventario` L, `stock_bajo` L, `productos_por_caducar` L, `cierre_de_caja` L, `crear_producto` E, `actualizar_precio` E, `ajustar_stock` E, `registrar_gasto` E, `conciliar_pagos` E |
| **Vendedor** | `agregar_al_carrito` L, `quitar_del_carrito` L, `sugerir_complemento` L, `registrar_venta` E, `registrar_pago` E |
| **Analista** | `consultar_ventas` L, `calcular_margenes` L, `top_productos` L, `generar_reporte` L (se guarda en `reportes`; cada sección indica `bd`, `externa` o `hipotesis`) |
| **Investigador** | `buscar_referencias` L, `resumen_mercado` L (datos locales **simulados**, fuente `externa`) |
| **Publicista** | `generar_promocion` L (texto para WhatsApp; avisa si el precio queda bajo el costo) |

`generar_reporte` y `generar_promocion` son de lectura: solo generan texto y no cambian el negocio.

## Reglas de negocio
- Stock nunca negativo; la venta descuenta stock y registra `movimientos_inventario` (salida) en una sola transacción.
- Método de pago: efectivo, transferencia, qr o tarjeta. Los digitales crean un pago `pendiente`.
- Estados del pago: `pendiente → enviado → recibido → conciliado` (solo avanzan; `recibido` exige referencia o comprobante).
- El monto de un pago debe coincidir con el total de la venta.

## Ejemplo
1. "cóbrame 2 Cocas y un Gansito" → **Vendedor** arma el carrito (total $58).
2. "transferencia" → propuesta `registrar_venta`; "sí" → venta #1, pago `pendiente`.
3. "ya llegó, referencia 99887" → propuesta `registrar_pago`; "sí" → pago `recibido`.
4. "cierre de caja" → **Control** muestra ventas, efectivo/digital y diferencias; "concilia los pagos" → `conciliado`.
5. "arma una promo" → **Publicista** pide a Control lo que caduca y genera el texto.
6. "hazme un reporte" → **Analista** con secciones etiquetadas por fuente.
