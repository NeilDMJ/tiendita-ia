import { useEffect, useRef, useState, type ComponentRef, type ReactNode } from 'react';
import { FlatList, StyleSheet, Text, View, type NativeScrollEvent, type NativeSyntheticEvent } from 'react-native';
import { useReducedMotion } from 'react-native-reanimated';

import { Boton } from '@/components/boton';
import { ROLES } from '@/constants';
import type { MensajeChat, MensajeDelAsistente } from '@/estado/chat';
import { color, espacio, type } from '@/theme';
import { claveDia, separadorDeDia } from '@/utils/texto-chat';

import { BurbujaMensaje } from './burbuja-mensaje';
import { IndicadorEscribiendo } from './indicador-escribiendo';

type Fila =
  | { tipo: 'dia'; clave: string; texto: string }
  | { tipo: 'msg'; clave: string; mensaje: MensajeChat; cabecera: boolean; ultimo: boolean; separacion: number };

/** Distancia al final con la que se considera que el tendero "está abajo". */
const UMBRAL_FINAL = 80;

function armarFilas(mensajes: MensajeChat[]): Fila[] {
  const filas: Fila[] = [];
  let dia = '';
  mensajes.forEach((m, i) => {
    const d = claveDia(m.creado_en);
    if (d !== dia) {
      dia = d;
      filas.push({ tipo: 'dia', clave: `dia-${d}`, texto: separadorDeDia(m.creado_en) });
    }
    const previo = i > 0 ? mensajes[i - 1] : null;
    const mismoAutor =
      previo !== null &&
      claveDia(previo.creado_en) === d &&
      previo.autor === m.autor &&
      (m.autor === 'tendero' || (previo.autor === 'asistente' && previo.rol === m.rol));
    filas.push({
      tipo: 'msg',
      clave: m.id,
      mensaje: m,
      cabecera: !mismoAutor,
      ultimo: i === mensajes.length - 1,
      separacion: mismoAutor ? espacio.s : espacio.l,
    });
  });
  return filas;
}

export interface ListaMensajesProps {
  mensajes: MensajeChat[];
  esperando: boolean;
  letraGrande: boolean;
  onDetener: () => void;
  onReintentar: (id: string) => void;
  onBorrar: (id: string) => void;
  onCancelarEspera: (id: string) => void;
  /** Tarjetas, botones `abrir_pantalla`, "no resuelto" y sugerencias (si es el último). */
  renderExtras: (mensaje: MensajeDelAsistente, ultimo: boolean) => ReactNode;
  /** `scrollY > 0` → la top app bar pasa a `surfaceContainer`. */
  onDesplazado?: (desplazado: boolean) => void;
}

/**
 * Lista del chat (02-asistente §2.1): FlatList NO invertida (orden de lectura correcto en TalkBack),
 * separadores de día y botón "Mensaje nuevo de {Rol}" si el tendero subió a leer (no se le mueve).
 */
export function ListaMensajes({
  mensajes,
  esperando,
  letraGrande,
  onDetener,
  onReintentar,
  onBorrar,
  onCancelarEspera,
  renderExtras,
  onDesplazado,
}: ListaMensajesProps) {
  const reducido = useReducedMotion();
  const refLista = useRef<ComponentRef<typeof FlatList<Fila>>>(null);
  const cercaDelFinal = useRef(true);
  const conteoPrevio = useRef(mensajes.length);
  const [nuevoDe, setNuevoDe] = useState<string | null>(null);
  const filas = armarFilas(mensajes);

  function bajar(animado: boolean) {
    refLista.current?.scrollToEnd({ animated: animado && !reducido });
  }

  // Mensaje nuevo: si el tendero está abajo (o es suyo) se baja; si está leyendo arriba, aparece el botón.
  useEffect(() => {
    const previo = conteoPrevio.current;
    conteoPrevio.current = mensajes.length;
    if (mensajes.length <= previo) return;
    const ultimo = mensajes[mensajes.length - 1];
    if (ultimo.autor === 'tendero' || cercaDelFinal.current) {
      setTimeout(() => bajar(true), 50);
    } else {
      setNuevoDe(ROLES[ultimo.rol].nombre);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo al cambiar el número de mensajes
  }, [mensajes.length]);

  function alDesplazar(e: NativeSyntheticEvent<NativeScrollEvent>) {
    const { contentOffset, contentSize, layoutMeasurement } = e.nativeEvent;
    const abajo = contentSize.height - contentOffset.y - layoutMeasurement.height < UMBRAL_FINAL;
    cercaDelFinal.current = abajo;
    onDesplazado?.(contentOffset.y > 0);
    if (abajo && nuevoDe) setNuevoDe(null);
  }

  return (
    <View style={estilos.contenedor}>
      <FlatList
        ref={refLista}
        data={filas}
        keyExtractor={(f) => f.clave}
        contentContainerStyle={estilos.contenido}
        keyboardShouldPersistTaps="handled"
        maintainVisibleContentPosition={{ minIndexForVisible: 0 }}
        onScroll={alDesplazar}
        scrollEventThrottle={100}
        onContentSizeChange={() => {
          if (cercaDelFinal.current) bajar(false);
        }}
        renderItem={({ item }) =>
          item.tipo === 'dia' ? (
            <Text style={estilos.dia} accessibilityRole="header">
              {item.texto}
            </Text>
          ) : (
            <View style={[estilos.fila, { marginTop: item.separacion }]}>
              <BurbujaMensaje
                mensaje={item.mensaje}
                cabecera={item.cabecera}
                letraGrande={letraGrande}
                onReintentar={() => onReintentar(item.mensaje.id)}
                onBorrar={() => onBorrar(item.mensaje.id)}
                onCancelarEspera={() => onCancelarEspera(item.mensaje.id)}
              />
              {item.mensaje.autor === 'asistente' ? renderExtras(item.mensaje, item.ultimo && !esperando) : null}
            </View>
          )
        }
        ListFooterComponent={
          esperando ? (
            <View style={estilos.pie}>
              <IndicadorEscribiendo onDetener={onDetener} />
            </View>
          ) : undefined
        }
      />
      {nuevoDe ? (
        <View style={estilos.flotante} pointerEvents="box-none">
          <Boton
            texto={`Mensaje nuevo de ${nuevoDe}`}
            icono="arrow-down"
            variante="tonal"
            anchoCompleto={false}
            onPress={() => {
              setNuevoDe(null);
              bajar(true);
            }}
          />
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: { flex: 1 },
  contenido: { paddingHorizontal: espacio.l, paddingTop: espacio.s, paddingBottom: espacio.xl },
  dia: { ...type.labelLarge, color: color.onSurfaceVariant, textAlign: 'center', marginTop: espacio.l },
  fila: { gap: espacio.s },
  pie: { marginTop: espacio.l },
  flotante: { position: 'absolute', bottom: espacio.s, left: 0, right: 0, alignItems: 'center' },
});
