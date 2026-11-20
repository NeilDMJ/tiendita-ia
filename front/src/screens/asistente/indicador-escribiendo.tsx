import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useReducedMotion } from 'react-native-reanimated';

import { Boton } from '@/components/boton';
import { CHAT } from '@/constants';
import { color, espacio, medidas, shape, tactil, type } from '@/theme';

import { CabeceraRol } from './burbuja-mensaje';

const PASO_PUNTOS_MS = 400;
const OPACIDAD_TENUE = 0.38;
const PUNTOS = [0, 1, 2];
const ES_ENJAMBRE = process.env.EXPO_PUBLIC_ASISTENTE_ENJAMBRE === '1';
const ETAPAS_THINKING = [
  'Supervisor analizando tu consulta…',
  'Especialista consultando datos en vivo…',
  'Consolidando respuesta del enjambre…',
];

/**
 * "Escribiendo…" (02-asistente §2.3): el texto siempre está (no depende de la animación).
 * Con el enjambre activo muestra etapas progresivas de Thinking mientras llegan los agentes.
 * A los 8 s: permite [Detener].
 */
export function IndicadorEscribiendo({ onDetener }: { onDetener: () => void }) {
  const reducido = useReducedMotion();
  const [paso, setPaso] = useState(0);
  const [etapa, setEtapa] = useState(0);
  const [tardando, setTardando] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setTardando(true), CHAT.avisoTardandoMs);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (!ES_ENJAMBRE) return;
    const t1 = setTimeout(() => setEtapa(1), 1800);
    const t2 = setTimeout(() => setEtapa(2), 5000);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  useEffect(() => {
    if (reducido) return;
    const t = setInterval(() => setPaso((p) => (p + 1) % PUNTOS.length), PASO_PUNTOS_MS);
    return () => clearInterval(t);
  }, [reducido]);

  const etiqueta = ES_ENJAMBRE
    ? tardando
      ? 'El enjambre sigue procesando…'
      : ETAPAS_THINKING[etapa]
    : tardando
      ? 'Está tardando más de lo normal…'
      : 'Escribiendo…';

  return (
    <View style={estilos.bloque}>
      <CabeceraRol rol="general" />
      <View style={estilos.burbuja} accessible accessibilityLabel={etiqueta}>
        <View style={estilos.puntos}>
          {PUNTOS.map((i) => (
            <View key={i} style={[estilos.punto, !reducido && i !== paso && { opacity: OPACIDAD_TENUE }]} />
          ))}
        </View>
        <Text style={estilos.texto}>{etiqueta}</Text>
      </View>
      {tardando ? <Boton texto="Detener" icono="stop" variante="text" anchoCompleto={false} onPress={onDetener} /> : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  bloque: { alignSelf: 'flex-start', gap: espacio.xs, marginRight: tactil.minimo },
  burbuja: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: espacio.m,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.m,
    borderRadius: shape.large,
    borderTopLeftRadius: shape.extraSmall,
    backgroundColor: color.surfaceContainerHigh,
  },
  puntos: { flexDirection: 'row', gap: espacio.xs },
  punto: {
    width: medidas.puntoEscribiendo,
    height: medidas.puntoEscribiendo,
    borderRadius: shape.full,
    backgroundColor: color.onSurfaceVariant,
  },
  texto: { ...type.bodyLarge, color: color.onSurfaceVariant, flexShrink: 1 },
});
