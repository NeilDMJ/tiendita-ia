import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useRef, type ComponentRef } from 'react';
import {
  AccessibilityInfo,
  findNodeHandle,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import type { NombreIcono } from '@/constants';
import { bordes, colores, espacio, iconos, radios, tactil, tipografia } from '@/theme';

import { Boton } from './boton';

export type TipoAviso = 'error' | 'exito' | 'info' | 'sinConexion' | 'tiempo';

export interface AvisoProps {
  tipo: TipoAviso;
  titulo: string;
  mensaje?: string;
  /** Obligatoria en la práctica para `error` (Nielsen #9: siempre una salida). */
  accion?: { texto: string; onPress: () => void; icono?: NombreIcono };
  accionSecundaria?: { texto: string; onPress: () => void; icono?: NombreIcono };
  modo?: 'tarjeta' | 'franja';
  onCerrar?: () => void;
  /** Mueve el foco del lector al aviso cuando bloquea el flujo. */
  enfocar?: boolean;
  testID?: string;
  style?: StyleProp<ViewStyle>;
}

const TIPOS: Record<TipoAviso, { color: string; icono: NombreIcono; fondo: string; prefijo: string }> = {
  error: { color: colores.peligro, icono: 'alert-circle', fondo: colores.fondo, prefijo: 'Error' },
  exito: { color: colores.exito, icono: 'check-circle', fondo: colores.fondo, prefijo: 'Listo' },
  info: { color: colores.texto, icono: 'information', fondo: colores.superficie, prefijo: 'Aviso' },
  sinConexion: { color: colores.texto, icono: 'wifi-off', fondo: colores.superficie, prefijo: 'Sin conexión' },
  tiempo: { color: colores.texto, icono: 'timer-sand', fondo: colores.superficie, prefijo: 'Aviso' },
};

/** Aviso con icono + título + mensaje + acción de recuperación. El color nunca es el único portador. */
export function Aviso({
  tipo,
  titulo,
  mensaje,
  accion,
  accionSecundaria,
  modo = 'tarjeta',
  onCerrar,
  enfocar,
  testID,
  style,
}: AvisoProps) {
  const t = TIPOS[tipo];
  const ref = useRef<ComponentRef<typeof View>>(null);
  const urgente = tipo === 'error' || tipo === 'sinConexion' || tipo === 'tiempo';

  useEffect(() => {
    if (Platform.OS === 'ios' && urgente) {
      AccessibilityInfo.announceForAccessibility(`${t.prefijo}: ${titulo}. ${mensaje ?? ''}`);
    }
    if (enfocar && ref.current) {
      const nodo = findNodeHandle(ref.current);
      if (nodo) AccessibilityInfo.setAccessibilityFocus(nodo);
    }
  }, [enfocar, mensaje, t.prefijo, titulo, urgente]);

  return (
    <View
      testID={testID}
      style={[
        estilos.base,
        modo === 'franja' ? estilos.franja : estilos.tarjeta,
        { borderColor: t.color, backgroundColor: t.fondo },
        style,
      ]}
      accessibilityRole={urgente ? 'alert' : undefined}
      accessibilityLiveRegion={urgente ? 'assertive' : 'polite'}
    >
      <View style={estilos.fila}>
        <MaterialCommunityIcons
          name={t.icono}
          size={iconos.linea}
          color={t.color}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <View
          ref={ref}
          style={estilos.textos}
          accessible
          accessibilityLabel={`${t.prefijo}: ${titulo}. ${mensaje ?? ''}`}
        >
          <Text style={[estilos.titulo, { color: t.color }]}>{titulo}</Text>
          {mensaje ? <Text style={estilos.mensaje}>{mensaje}</Text> : null}
        </View>
        {onCerrar ? (
          <Pressable
            onPress={onCerrar}
            accessibilityRole="button"
            accessibilityLabel="Cerrar aviso"
            style={({ pressed }) => [estilos.cerrar, pressed && estilos.presionado]}
          >
            <MaterialCommunityIcons name="close" size={iconos.linea} color={colores.texto} />
          </Pressable>
        ) : null}
      </View>
      {accion || accionSecundaria ? (
        <View style={estilos.acciones}>
          {accion ? (
            <Boton
              texto={accion.texto}
              icono={accion.icono}
              onPress={accion.onPress}
              variante={tipo === 'error' ? 'secundario' : 'primario'}
            />
          ) : null}
          {accionSecundaria ? (
            <Boton
              texto={accionSecundaria.texto}
              icono={accionSecundaria.icono}
              onPress={accionSecundaria.onPress}
              variante="texto"
            />
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  base: { padding: espacio.l, gap: espacio.m },
  tarjeta: { borderWidth: bordes.grueso, borderRadius: radios.medio },
  franja: { borderBottomWidth: bordes.grueso, borderRadius: radios.recto },
  fila: { flexDirection: 'row', gap: espacio.m, alignItems: 'flex-start' },
  textos: { flex: 1, gap: espacio.xs },
  titulo: { ...tipografia.subtitulo },
  mensaje: { ...tipografia.cuerpoGrande, color: colores.texto },
  cerrar: {
    width: tactil.minimo,
    height: tactil.minimo,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radios.medio,
  },
  presionado: { backgroundColor: colores.superficie },
  acciones: { gap: tactil.separacion },
});
