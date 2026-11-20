import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useRef, type ComponentRef, type Ref } from 'react';
import {
  AccessibilityInfo,
  findNodeHandle,
  Platform,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import type { NombreIcono } from '@/constants';
import { bordes, color, espacio, iconos, shape, tactil, type } from '@/theme';

import { Boton, type VarianteBoton } from './boton';
import { Tocable } from './tocable';

export type TipoAviso = 'error' | 'exito' | 'info' | 'sinConexion' | 'tiempo';

type AccionAviso = { texto: string; onPress: () => void; icono?: NombreIcono };

export interface AvisoProps {
  tipo: TipoAviso;
  titulo: string;
  mensaje?: string;
  /** Obligatoria en la práctica para `error` (Nielsen #9: siempre una salida). */
  /** `variante` por defecto: filled (tarjeta) / text (franja). */
  accion?: AccionAviso & { variante?: VarianteBoton };
  accionSecundaria?: AccionAviso;
  /** Ref al botón de la acción secundaria (para devolverle el foco al cerrar un diálogo que abrió). */
  refAccionSecundaria?: Ref<ComponentRef<typeof View>>;
  modo?: 'tarjeta' | 'franja';
  onCerrar?: () => void;
  /** Mueve el foco del lector al aviso cuando bloquea el flujo. */
  enfocar?: boolean;
  testID?: string;
  style?: StyleProp<ViewStyle>;
}

type Apariencia = { contenedor: string; titulo: string; icono: string; texto: string; nombreIcono: NombreIcono; prefijo: string };

/** 00-sistema §9.4: contenedor y contenido por rol (contrastes ≥ 7.24:1). */
const TIPOS: Record<TipoAviso, Apariencia> = {
  error: {
    contenedor: color.errorContainer,
    titulo: color.onErrorContainer,
    icono: color.onErrorContainer,
    texto: color.onErrorContainer,
    nombreIcono: 'alert-circle',
    prefijo: 'Error',
  },
  exito: {
    contenedor: color.successContainer,
    titulo: color.onSuccessContainer,
    icono: color.onSuccessContainer,
    texto: color.onSuccessContainer,
    nombreIcono: 'check-circle',
    prefijo: 'Listo',
  },
  info: {
    contenedor: color.surfaceContainerHigh,
    titulo: color.onSurface,
    icono: color.onSurfaceVariant,
    texto: color.onSurface,
    nombreIcono: 'information',
    prefijo: 'Aviso',
  },
  sinConexion: {
    contenedor: color.surfaceContainerHigh,
    titulo: color.onSurface,
    icono: color.onSurface,
    texto: color.onSurface,
    nombreIcono: 'wifi-off',
    prefijo: 'Sin conexión',
  },
  tiempo: {
    contenedor: color.surfaceContainerHigh,
    titulo: color.onSurface,
    icono: color.onSurface,
    texto: color.onSurface,
    nombreIcono: 'timer-sand',
    prefijo: 'Aviso',
  },
};

/**
 * Banner (`franja`, bajo la top app bar) o card de mensaje (`tarjeta`) M3.
 * Icono + título + mensaje + acción de recuperación: el color nunca es el único portador.
 * Lo transitorio (deshacer, confirmaciones breves) va en `Snackbar`, no aquí.
 */
export function Aviso({
  tipo,
  titulo,
  mensaje,
  accion,
  accionSecundaria,
  refAccionSecundaria,
  modo = 'tarjeta',
  onCerrar,
  enfocar,
  testID,
  style,
}: AvisoProps) {
  const t = TIPOS[tipo];
  const ref = useRef<ComponentRef<typeof View>>(null);
  const urgente = tipo === 'error' || tipo === 'sinConexion' || tipo === 'tiempo';
  const franja = modo === 'franja';
  const etiquetaLector = `${titulo.startsWith(t.prefijo) ? '' : `${t.prefijo}: `}${titulo}. ${mensaje ?? ''}`;

  useEffect(() => {
    if (Platform.OS === 'ios' && urgente) {
      AccessibilityInfo.announceForAccessibility(etiquetaLector);
    }
    if (enfocar && ref.current) {
      const nodo = findNodeHandle(ref.current);
      if (nodo) AccessibilityInfo.setAccessibilityFocus(nodo);
    }
  }, [enfocar, etiquetaLector, urgente]);

  return (
    <View
      testID={testID}
      style={[estilos.base, franja ? estilos.franja : estilos.tarjeta, { backgroundColor: t.contenedor }, style]}
      accessibilityRole={urgente ? 'alert' : undefined}
      accessibilityLiveRegion={urgente ? 'assertive' : 'polite'}
    >
      <View style={estilos.fila}>
        <MaterialCommunityIcons
          name={t.nombreIcono}
          size={iconos.linea}
          color={t.icono}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <View
          ref={ref}
          style={estilos.textos}
          accessible
          accessibilityLabel={etiquetaLector}
        >
          <Text style={[estilos.titulo, { color: t.titulo }]}>{titulo}</Text>
          {mensaje ? <Text style={[estilos.mensaje, { color: t.texto }]}>{mensaje}</Text> : null}
        </View>
        {onCerrar ? (
          <Tocable
            onPress={onCerrar}
            colorContenido={t.texto}
            radio={shape.full}
            accessibilityRole="button"
            accessibilityLabel="Cerrar aviso"
            style={estilos.cerrar}
          >
            <MaterialCommunityIcons
              name="close"
              size={iconos.linea}
              color={t.texto}
              accessibilityElementsHidden
              importantForAccessibility="no"
            />
          </Tocable>
        ) : null}
      </View>
      {accion || accionSecundaria ? (
        <View style={estilos.acciones}>
          {accionSecundaria ? (
            <Boton
              texto={accionSecundaria.texto}
              icono={accionSecundaria.icono}
              onPress={accionSecundaria.onPress}
              ref={refAccionSecundaria}
              variante="text"
              anchoCompleto={false}
            />
          ) : null}
          {accion ? (
            <Boton
              texto={accion.texto}
              icono={accion.icono}
              onPress={accion.onPress}
              variante={accion.variante ?? (franja ? 'text' : 'filled')}
              anchoCompleto={false}
            />
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  base: { gap: espacio.m },
  tarjeta: { borderRadius: shape.medium, padding: espacio.l },
  franja: {
    borderRadius: shape.none,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.m,
    borderBottomWidth: bordes.fino,
    borderBottomColor: color.outlineVariant,
  },
  fila: { flexDirection: 'row', gap: espacio.m, alignItems: 'flex-start' },
  textos: { flex: 1, gap: espacio.xs },
  titulo: { ...type.titleMedium },
  mensaje: { ...type.bodyLargePlus },
  cerrar: {
    width: tactil.minimo,
    height: tactil.minimo,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: shape.full,
    marginTop: -espacio.m,
    marginRight: -espacio.s,
  },
  acciones: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: tactil.separacion,
  },
});
