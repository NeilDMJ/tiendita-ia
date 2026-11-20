import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { NombreIcono } from '@/constants';
import {
  bordes,
  color,
  espacio,
  esquemaActivo,
  iconos,
  preferenciaApariencia,
  shape,
  tactil,
  type,
  type PreferenciaApariencia,
} from '@/theme';
import { aplicarApariencia } from '@/utils/apariencia';

import { Boton } from './boton';
import { HojaInferior } from './hoja-inferior';
import { Tocable } from './tocable';

const OPCIONES: { valor: PreferenciaApariencia; titulo: string; detalle: string; icono: NombreIcono }[] = [
  { valor: 'sistema', titulo: 'Igual que el teléfono', detalle: 'Cambia solo según tu configuración', icono: 'cellphone' },
  { valor: 'claro', titulo: 'Claro', detalle: 'Fondo blanco, ideal con mucha luz', icono: 'white-balance-sunny' },
  { valor: 'oscuro', titulo: 'Oscuro', detalle: 'Fondo oscuro, cansa menos la vista', icono: 'weather-night' },
];

/**
 * Botón de icono (48) que abre la hoja "Apariencia": Igual que el teléfono / Claro / Oscuro.
 * Aplicar reinicia la app (ver `utils/apariencia.ts`), y se avisa antes de hacerlo.
 */
export function SelectorApariencia() {
  const [abierta, setAbierta] = useState(false);
  const [elegida, setElegida] = useState<PreferenciaApariencia>(preferenciaApariencia);
  const [aplicando, setAplicando] = useState(false);
  const sinCambios = elegida === preferenciaApariencia;

  return (
    <>
      <Tocable
        onPress={() => {
          setElegida(preferenciaApariencia);
          setAbierta(true);
        }}
        colorContenido={color.onSurfaceVariant}
        radio={shape.full}
        accessibilityRole="button"
        accessibilityLabel="Apariencia"
        accessibilityHint="Abre las opciones de modo claro y oscuro"
        style={estilos.boton}
      >
        <MaterialCommunityIcons
          name="theme-light-dark"
          size={iconos.linea}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
      </Tocable>

      <HojaInferior
        visible={abierta}
        titulo="Apariencia"
        icono="theme-light-dark"
        onCerrar={() => setAbierta(false)}
        pie={
          <Boton
            texto="Aplicar y reiniciar"
            icono="restart"
            tamano="principal"
            cargando={aplicando}
            textoCargando="Reiniciando…"
            deshabilitado={sinCambios}
            motivoDeshabilitado="Elige una opción distinta a la actual"
            onPress={() => {
              setAplicando(true);
              void aplicarApariencia(elegida);
            }}
          />
        }
      >
        <View accessibilityRole="radiogroup" style={estilos.grupo}>
          {OPCIONES.map((o) => {
            const activa = o.valor === elegida;
            return (
              <Tocable
                key={o.valor}
                onPress={() => setElegida(o.valor)}
                colorContenido={activa ? color.onPrimaryContainer : color.onSurface}
                radio={shape.medium}
                accessibilityRole="radio"
                accessibilityState={{ checked: activa }}
                accessibilityLabel={`${o.titulo}. ${o.detalle}`}
                style={[estilos.opcion, activa ? estilos.opcionActiva : null]}
              >
                <MaterialCommunityIcons
                  name={activa ? 'radiobox-marked' : 'radiobox-blank'}
                  size={iconos.linea}
                  color={activa ? color.onPrimaryContainer : color.onSurfaceVariant}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <MaterialCommunityIcons
                  name={o.icono}
                  size={iconos.linea}
                  color={activa ? color.onPrimaryContainer : color.onSurfaceVariant}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
                <View style={estilos.textos}>
                  <Text style={[estilos.titulo, { color: activa ? color.onPrimaryContainer : color.onSurface }]}>
                    {o.titulo}
                  </Text>
                  <Text style={[estilos.detalle, { color: activa ? color.onPrimaryContainer : color.onSurfaceVariant }]}>
                    {o.detalle}
                  </Text>
                </View>
              </Tocable>
            );
          })}
        </View>
        <Text style={estilos.nota}>
          Ahora se ve en modo {esquemaActivo}. Para aplicar el cambio la app se reinicia; tus ventas y conversaciones
          guardadas no se pierden.
        </Text>
      </HojaInferior>
    </>
  );
}

const estilos = StyleSheet.create({
  boton: { width: tactil.minimo, height: tactil.minimo, alignItems: 'center', justifyContent: 'center' },
  grupo: { gap: espacio.s },
  opcion: {
    minHeight: tactil.principal,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
    padding: espacio.m,
    borderRadius: shape.medium,
    borderWidth: bordes.fino,
    borderColor: color.outlineVariant,
    backgroundColor: color.surfaceContainerLowest,
  },
  opcionActiva: { backgroundColor: color.primaryContainer, borderColor: color.primaryContainer },
  textos: { flex: 1 },
  titulo: { ...type.titleSmall },
  detalle: { ...type.bodyLarge },
  nota: { ...type.bodyLarge, color: color.onSurfaceVariant, marginTop: espacio.l },
});
