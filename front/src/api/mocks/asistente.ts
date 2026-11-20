/**
 * MOCK — respuestas sintéticas del asistente (EXPO_PUBLIC_USE_MOCKS=1). Simulación: no hay orquestador real.
 * Contesta por palabras clave con los MISMOS datos sintéticos del catálogo y las ventas mock.
 *
 * EXPO_PUBLIC_MOCK_ASISTENTE = ok (default) | lento (12 s: muestra "tardando" a los 8 s) | falla (error del servidor)
 */
import type { OpcionesPedido } from '../cliente';
import { ErrorApi } from '../cliente';
import type {
  AccionAsistente,
  ContextoAsistente,
  ItemContexto,
  ItemPropuesto,
  MensajeAsistente,
  Producto,
  SolicitudAsistente,
} from '../esquemas';
import { mockRespuestaBanco } from './banco';
import { esperarCancelable } from './index';
import {
  exigirConexion,
  mockCatalogo,
  mockResumenVentasHoy,
  mockStockBajo,
  quitarAcentos,
} from './negocio';

export const ESCENARIO_ASISTENTE = process.env.EXPO_PUBLIC_MOCK_ASISTENTE ?? 'ok';

const ESPERA_MS = { ok: 900, lento: 12_000 } as const;
const VIGENCIA_MS = 30 * 60 * 1000;

/** id_mensaje → respuesta: un Reintentar no genera otra respuesta distinta (igual que el back). */
const respondidas = new Map<string, MensajeAsistente>();
let contadorAcciones = 0;

const pesos = (n: number) => `$${n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;

function nuevaAccion(tipo: AccionAsistente['tipo'], titulo: string, datos: unknown, conVigencia = true): AccionAsistente {
  contadorAcciones += 1;
  return {
    id: `mock-a-${Date.now().toString(16)}-${contadorAcciones}`,
    tipo,
    titulo,
    datos,
    vence_en: conVigencia ? new Date(Date.now() + VIGENCIA_MS).toISOString() : undefined,
  };
}

// ---------- Interpretar "vendí 2 cocas y un pan" ----------
const NUMEROS: Record<string, number> = {
  un: 1, una: 1, uno: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9, diez: 10,
};

/** Palabra clave (sin acentos) → sku del catálogo mock. `null` = producto que no está en el catálogo. */
const PALABRAS_PRODUCTO: [RegExp, string | null, string?][] = [
  [/\b(coca|cocas|refresco|refrescos)\b/, 'REF-COLA-600'],
  [/\bgalletas? maria\b/, 'GALL-MARIA-170'],
  [/\bgalletas?\b/, 'GALL-MARIA-170'],
  [/\bpan(es)?\b/, 'PAN-BLANCO-680'],
  [/\bjabon(es)?\b/, 'JABON-BARRA-150'],
  [/\blech(e|es)\b/, 'LECHE-ENT-1L'],
  [/\bhuevos?\b/, 'HUEVO-12'],
  [/\btortillas?\b/, 'TORT-1KG'],
  [/\bfrijol(es)?\b/, 'FRIJOL-900'],
  [/\barroz\b/, 'ARROZ-1KG'],
  [/\baceites?\b/, 'ACEITE-1L'],
  [/\bazucar\b/, 'AZUCAR-1KG'],
  [/\baguas?\b/, 'AGUA-1L'],
  [/\bpapas?\b/, 'PAPAS-45'],
  [/\batun(es)?\b/, 'ATUN-140'],
  // Ejemplo de producto fuera del catálogo: obliga a "Revisar y editar" (sin precio).
  [/\bchicles?\b/, null, 'Chicles'],
];

function productosEnTexto(texto: string, catalogo: Producto[]): ItemPropuesto[] {
  const items: ItemPropuesto[] = [];
  for (const fragmento of quitarAcentos(texto).split(/,| y | e |\+/)) {
    for (const [patron, sku, nombreLibre] of PALABRAS_PRODUCTO) {
      if (!patron.test(fragmento)) continue;
      const numero = fragmento.match(/(\d+|\bun\b|\buna\b|\buno\b|\bdos\b|\btres\b|\bcuatro\b|\bcinco\b|\bseis\b|\bsiete\b|\bocho\b|\bnueve\b|\bdiez\b)/);
      const cantidad = numero ? (NUMEROS[numero[1]] ?? Math.max(1, parseInt(numero[1], 10) || 1)) : 1;
      const producto = sku ? catalogo.find((p) => p.sku === sku) : undefined;
      items.push(
        producto
          ? { sku: producto.sku, nombre: producto.nombre, cantidad, precio_unitario: producto.precio_unitario }
          : { sku: null, nombre: nombreLibre ?? 'Producto', cantidad, precio_unitario: null },
      );
      break;
    }
  }
  return items;
}

// ---------- Respuestas de la pestaña ----------
function respuestaPestana(texto: string): MensajeAsistente {
  const t = quitarAcentos(texto);
  const catalogo = mockCatalogo();

  if (/registrar (una )?venta|quiero cobrar|cobrar una venta/.test(t)) {
    return {
      rol: 'caja',
      texto: 'Dime qué vendiste, por ejemplo: “2 refrescos y un pan”. O cóbralo con foto.',
      acciones: [nuevaAccion('abrir_pantalla', 'Cobrar con foto', { pantalla: 'camara_cobro' }, false)],
      sugerencias: ['Vendí 2 cocas y un pan'],
    };
  }

  const items = productosEnTexto(texto, catalogo);
  if (/\b(vendi|vende|cobra|cobre|cobrale|vendimos)\b/.test(t) && items.length > 0) {
    const piezas = items.reduce((s, i) => s + i.cantidad, 0);
    const sinPrecio = items.some((i) => i.precio_unitario === null);
    return {
      rol: 'caja',
      texto: sinPrecio
        ? 'Va. Hay un producto que no tengo en tu catálogo; revísalo antes de cobrar.'
        : 'Va. ¿Lo cobro así?',
      acciones: [
        nuevaAccion('confirmar_venta', `Cobrar venta de ${piezas} ${piezas === 1 ? 'producto' : 'productos'}`, {
          items,
          metodo_pago: 'efectivo',
        }),
      ],
    };
  }

  if (/ayer|semana|mes pasado/.test(t)) {
    return {
      rol: 'cuentas',
      texto: 'Por ahora solo puedo ver las ventas de hoy. Pronto podré compararlas con días anteriores.',
      sugerencias: ['¿Cuánto vendí hoy?'],
    };
  }

  if (/vend|ventas|llevo/.test(t)) {
    const r = mockResumenVentasHoy();
    if (r.numero === 0) {
      return {
        rol: 'cuentas',
        texto: 'Hoy todavía no registras ventas. Cuando cobres, aquí te digo cuánto llevas.',
        acciones: [nuevaAccion('abrir_pantalla', 'Cobrar con foto', { pantalla: 'camara_cobro' }, false)],
        sugerencias: ['Registrar una venta'],
      };
    }
    return {
      rol: 'cuentas',
      texto:
        `Hoy llevas ${pesos(r.total)} en ${r.numero} ${r.numero === 1 ? 'venta' : 'ventas'}.` +
        (r.masVendido ? ` Lo que más salió fue ${r.masVendido.nombre} (${r.masVendido.piezas} pz).` : ''),
      acciones: [nuevaAccion('abrir_pantalla', 'Ver ventas de hoy', { pantalla: 'historial' }, false)],
      sugerencias: ['¿Qué se me está acabando?', 'Ventas de ayer'],
    };
  }

  if (/acab|stock|falta|queda|inventario|surtir/.test(t)) {
    const bajos = mockStockBajo();
    return {
      rol: 'bodega',
      texto:
        bajos.length === 0
          ? 'Por ahora tienes suficiente de todo.'
          : `Se te está acabando:\n${bajos.map((p) => `• ${p.nombre}: quedan ${p.existencia} pz`).join('\n')}`,
      acciones: [nuevaAccion('abrir_pantalla', 'Ver inventario', { pantalla: 'inventario' }, false)],
      sugerencias: ['Llegaron 12 leches', '¿Cuánto vendí hoy?'],
    };
  }

  if (/lleg|surti|me trajo|dar de alta|alta de/.test(t)) {
    const leche = catalogo.find((p) => p.sku === 'LECHE-ENT-1L');
    const producto = items.find((i) => i.sku !== null) ?? (leche ? { sku: leche.sku, nombre: leche.nombre, cantidad: 12, precio_unitario: leche.precio_unitario } : null);
    if (producto) {
      return {
        rol: 'bodega',
        texto: 'Anoto la mercancía que llegó. Revisa que esté bien antes de confirmar.',
        acciones: [
          nuevaAccion('confirmar_alta', `Dar de alta ${producto.cantidad} pz de ${producto.nombre}`, {
            sku: producto.sku,
            nombre: producto.nombre,
            cantidad: producto.cantidad,
            precio_venta: producto.precio_unitario,
            caducidad: '2026-11-28',
          }),
        ],
      };
    }
  }

  if (/transferencia|tarjeta|codi|digital|pago con|cobro digital/.test(t)) {
    return {
      rol: 'tutor',
      texto:
        'Para cobrar con transferencia:\n1. Pídele a tu cliente que abra la app de su banco.\n2. Dale tu número de cuenta (CLABE) o tu código QR.\n3. Espera a que te llegue el aviso de tu banco con el monto correcto.\n4. Ya con el aviso, entrega la mercancía.',
      acciones: [nuevaAccion('abrir_pantalla', 'Practicar un cobro (Simulación)', { pantalla: 'pago' }, false)],
      sugerencias: ['¿Y si no me llega el aviso?'],
    };
  }

  if (/promo|oferta|caduc/.test(t)) {
    return {
      rol: 'promociones',
      texto: 'El yogur natural caduca el viernes. Te propongo esta oferta para venderlo antes.',
      acciones: [
        nuevaAccion('aprobar_promo', 'Promoción: Yogur natural 1 L a $30', {
          promo_id: 'mock-promo-1',
          producto: 'Yogur natural 1 L',
          copy: '¡Aprovecha! Yogur natural 1 L a solo $30 hasta el viernes.',
          precio_promo: 30,
          vigente_hasta: '2026-11-21',
          video_url: null,
          simulacion: true,
        }),
      ],
    };
  }

  if (/ganancia|gane|gasto|gaste/.test(t)) {
    const r = mockResumenVentasHoy();
    return {
      rol: 'cuentas',
      texto: `Hoy llevas ${pesos(r.total)} en ventas. Para calcular tu ganancia necesito tus gastos: toma foto de tus tickets de compra.`,
      acciones: [nuevaAccion('abrir_pantalla', 'Foto de un ticket', { pantalla: 'camara_ticket' }, false)],
    };
  }

  if (/^(hola|buenas|buenos dias|buenas tardes|que tal)/.test(t)) {
    return {
      rol: 'general',
      texto: '¡Hola! Pregúntame por tus ventas, lo que se te acaba o cómo cobrar.',
      sugerencias: ['¿Cuánto vendí hoy?', '¿Qué se me está acabando?'],
    };
  }

  return {
    rol: 'general',
    texto: 'No entendí bien. ¿Quieres cobrar, revisar tu inventario o ver tus ventas?',
    no_resuelto: true,
  };
}

// ---------- Respuestas de la hoja "Pregúntale a Caja" (contexto revision_cobro) ----------
type ContextoCobro = Extract<ContextoAsistente, { pantalla: 'revision_cobro' }>;

function nombreFila(item: ItemContexto) {
  return item.numero_en_foto ? `El producto ${item.numero_en_foto}` : `“${item.nombre}”`;
}

function propuestaParaFalta(item: ItemContexto, catalogo: Producto[]): MensajeAsistente | null {
  const palabra = quitarAcentos(item.nombre).split(/\s+/)[0] ?? '';
  const candidato =
    (item.sku ? catalogo.find((p) => p.sku === item.sku) : undefined) ??
    catalogo.find((p) => palabra.length > 2 && quitarAcentos(p.nombre).includes(palabra));
  if (!candidato) return null;
  return {
    rol: 'caja',
    texto: `${nombreFila(item)} parece ser ${candidato.nombre}; cuesta ${pesos(candidato.precio_unitario)}.`,
    acciones: [
      nuevaAccion('modificar_item', `Cambiar ${item.numero_en_foto ? `el producto ${item.numero_en_foto}` : item.nombre}`, {
        indice: item.indice,
        clave: item.clave,
        nombre_actual: item.nombre,
        cambios: { sku: candidato.sku, nombre: candidato.nombre, precio_unitario: candidato.precio_unitario },
      }),
    ],
  };
}

function respuestaCaja(texto: string, contexto: ContextoCobro): MensajeAsistente {
  const t = quitarAcentos(texto);
  const catalogo = mockCatalogo();
  const falta = contexto.items.find((i) => i.nivel === 'falta');

  if (/alcanza|stock|existencia|quedan|hay suficiente/.test(t)) {
    const lineas = contexto.items
      .filter((i) => i.sku)
      .map((i) => {
        const p = catalogo.find((c) => c.sku === i.sku);
        if (!p) return null;
        return p.existencia >= i.cantidad
          ? `• ${p.nombre}: sí alcanza (hay ${p.existencia})`
          : `• ${p.nombre}: NO alcanza, solo hay ${p.existencia}`;
      })
      .filter((l): l is string => l !== null);
    return {
      rol: 'bodega',
      texto: lineas.length > 0 ? `Revisé tu bodega:\n${lineas.join('\n')}` : 'No tengo productos del catálogo en esta venta para revisar.',
    };
  }

  if (/cuesta|precio|reconoc|cual es|que producto|no se que|identific/.test(t)) {
    if (falta) {
      const propuesta = propuestaParaFalta(falta, catalogo);
      if (propuesta) return propuesta;
    } else if (/cuesta|precio/.test(t)) {
      return {
        rol: 'caja',
        texto: `Estos son los precios de tu venta:\n${contexto.items
          .map((i) => `• ${i.nombre}: ${i.precio_unitario === null ? 'sin precio' : pesos(i.precio_unitario)}`)
          .join('\n')}`,
      };
    } else {
      return { rol: 'caja', texto: 'Todos los productos de esta venta ya están identificados. Puedes cobrar.' };
    }
  }

  return {
    rol: 'caja',
    texto: 'No encontré ese producto en tu catálogo.',
    no_resuelto: true,
  };
}

/** MOCK de POST /asistente/mensaje. Respeta Detener (signal), el tiempo límite y la conexión. */
export async function mockRespuestaAsistente(
  solicitud: SolicitudAsistente,
  opciones: OpcionesPedido = {},
): Promise<MensajeAsistente> {
  await exigirConexion();
  const espera = ESCENARIO_ASISTENTE === 'lento' ? ESPERA_MS.lento : ESPERA_MS.ok;
  await esperarCancelable(espera, opciones.signal, opciones.tiempoMs);
  if (ESCENARIO_ASISTENTE === 'falla') throw new ErrorApi('servidor');

  const previa = respondidas.get(solicitud.id_mensaje);
  if (previa) return previa;
  const respuesta =
    solicitud.contexto?.pantalla === 'revision_cobro'
      ? respuestaCaja(solicitud.texto, solicitud.contexto)
      : (mockRespuestaBanco(solicitud.texto) ?? respuestaPestana(solicitud.texto));
  respondidas.set(solicitud.id_mensaje, respuesta);
  return respuesta;
}

/** SIMULACIÓN — aprobar una promoción: no se publica en redes ni existe el endpoint todavía (Fase 6). */
export async function mockAprobarPromocion(_promoId: string): Promise<void> {
  await exigirConexion();
  await esperarCancelable(ESPERA_MS.ok);
}
