import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { DatosConfirmarAlta } from '@/api/esquemas';
import { Boton } from '@/components/boton';
import { Campo } from '@/components/campo';
import { HojaInferior } from '@/components/hoja-inferior';
import { StepperCantidad } from '@/components/stepper-cantidad';
import { color, espacio, iconos, type } from '@/theme';
import { leerMonto } from '@/utils/formato-moneda';

export interface HojaEditarAltaProps {
  visible: boolean;
  datos: DatosConfirmarAlta;
  conectado: boolean;
  onCerrar: () => void;
  /** Solo se llama con datos válidos; el alta se registra hasta aquí (doble control). */
  onConfirmar: (datos: DatosConfirmarAlta) => void;
}

/** 'AAAA-MM-DD' de calendario válido. */
function fechaValida(texto: string) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto);
  if (!m) return false;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return d.getFullYear() === Number(m[1]) && d.getMonth() === Number(m[2]) - 1 && d.getDate() === Number(m[3]);
}

/**
 * "Revisar y editar" de una propuesta `confirmar_alta` (bases: lo que entendió el asistente pasa a un
 * formulario editable antes de guardarse). Mínima mientras llega la revisión de alta de Fase 4.
 * Validación en tiempo real; el botón principal nunca se deshabilita por datos (EXC-4): muestra qué falta.
 */
export function HojaEditarAlta({ visible, datos, conectado, onCerrar, onConfirmar }: HojaEditarAltaProps) {
  const [nombre, setNombre] = useState(datos.nombre);
  const [cantidad, setCantidad] = useState(datos.cantidad);
  const [precio, setPrecio] = useState(datos.precio_venta !== null ? datos.precio_venta.toFixed(2) : '');
  const [caducidad, setCaducidad] = useState(datos.caducidad ?? '');
  const [tocado, setTocado] = useState({ nombre: false, precio: false, caducidad: false });
  const [intento, setIntento] = useState(false);

  const precioNumero = leerMonto(precio);
  const errorNombre = nombre.trim() === '' ? 'Escribe cómo se llama el producto' : null;
  const errorPrecio =
    precio.trim() === ''
      ? 'Escribe el precio de venta. Ej. 28.00'
      : precioNumero === null
        ? 'Escribe solo números. Ej. 28.00'
        : precioNumero === 0
          ? 'El precio no puede ser 0'
          : null;
  const errorCaducidad =
    caducidad.trim() !== '' && !fechaValida(caducidad.trim()) ? 'Usa año-mes-día. Ej. 2026-11-28' : null;
  const hayErrores = errorNombre !== null || errorPrecio !== null || errorCaducidad !== null;

  function confirmar() {
    setIntento(true);
    if (hayErrores || precioNumero === null) return;
    onConfirmar({
      sku: nombre.trim() === datos.nombre ? datos.sku : null,
      nombre: nombre.trim(),
      cantidad,
      precio_venta: precioNumero,
      caducidad: caducidad.trim() === '' ? null : caducidad.trim(),
    });
  }

  return (
    <HojaInferior
      visible={visible}
      titulo="Revisar mercancía"
      onCerrar={onCerrar}
      pie={
        <>
          {!conectado ? (
            <View style={estilos.motivo}>
              <MaterialCommunityIcons
                name="wifi-off"
                size={iconos.linea}
                color={color.onSurfaceVariant}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
              <Text style={estilos.textoMotivo}>Necesita internet</Text>
            </View>
          ) : intento && hayErrores ? (
            <View style={estilos.motivo} accessibilityLiveRegion="polite">
              <MaterialCommunityIcons
                name="alert-circle"
                size={iconos.linea}
                color={color.error}
                accessibilityElementsHidden
                importantForAccessibility="no"
              />
              <Text style={estilos.textoError}>Corrige los campos marcados para confirmar</Text>
            </View>
          ) : null}
          <Boton
            texto="Confirmar alta"
            icono="check"
            tamano="principal"
            deshabilitado={!conectado}
            motivoDeshabilitado="Necesita internet"
            onPress={confirmar}
          />
          <Boton texto="Cancelar" variante="text" onPress={onCerrar} />
        </>
      }
    >
      <Campo
        etiqueta="Producto"
        obligatorio
        valor={nombre}
        onCambiar={setNombre}
        onBlur={() => setTocado((t) => ({ ...t, nombre: true }))}
        error={tocado.nombre || intento ? errorNombre : null}
      />
      <View style={estilos.grupo}>
        <Text style={estilos.etiqueta}>Cantidad que llegó</Text>
        <StepperCantidad valor={cantidad} onCambiar={setCantidad} nombreProducto={nombre || 'producto'} />
      </View>
      <Campo
        etiqueta="Precio de venta"
        obligatorio
        tipo="moneda"
        prefijo="$"
        valor={precio}
        onCambiar={setPrecio}
        onBlur={() => setTocado((t) => ({ ...t, precio: true }))}
        error={tocado.precio || intento ? errorPrecio : null}
      />
      <Campo
        etiqueta="Caducidad (opcional)"
        placeholder="2026-11-28"
        valor={caducidad}
        onCambiar={setCaducidad}
        onBlur={() => setTocado((t) => ({ ...t, caducidad: true }))}
        ayuda="Año-mes-día. Déjalo vacío si no caduca."
        error={tocado.caducidad || intento ? errorCaducidad : null}
      />
    </HojaInferior>
  );
}

const estilos = StyleSheet.create({
  grupo: { gap: espacio.xs },
  etiqueta: { ...type.titleSmall, color: color.onSurface },
  motivo: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs },
  textoMotivo: { ...type.bodyLarge, color: color.onSurfaceVariant, flex: 1 },
  textoError: { ...type.labelLarge, color: color.error, flex: 1 },
});
