import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Linking, StyleSheet, Text, View } from 'react-native';

import { parsearDatosAccion, RUTAS_DESTINO } from '@/api/acciones-asistente';
import type { PantallaDestino } from '@/api/esquemas';
import { Boton } from '@/components/boton';
import { SOPORTE_WHATSAPP, type NombreIcono } from '@/constants';
import type { AccionChat } from '@/estado/chat';
import { bordes, color, espacio, iconos, shape, tactil, type } from '@/theme';

const POR_DEFECTO: { texto: string; icono: NombreIcono; destino: PantallaDestino }[] = [
  { texto: 'Cobrar con foto', icono: 'camera', destino: 'camara_cobro' },
  { texto: 'Ver inventario', icono: 'package-variant-closed', destino: 'inventario' },
  { texto: 'Ver ventas de hoy', icono: 'receipt', destino: 'historial' },
];

/**
 * "No pude resolverlo" (02-asistente §2.6): card outlined (borde `outline`, EXC-10: agrupa controles),
 * no roja (no es error del tendero) + salidas directas. Usa las `abrir_pantalla` del back si llegaron.
 */
export function AlternativasNoResuelto({
  acciones,
  onAbrir,
}: {
  acciones?: AccionChat[];
  onAbrir: (destino: PantallaDestino) => void;
}) {
  const delBack = (acciones ?? [])
    .map((a) => {
      const p = parsearDatosAccion(a);
      return p?.tipo === 'abrir_pantalla' ? { texto: a.titulo, icono: 'arrow-right' as NombreIcono, destino: p.datos.pantalla } : null;
    })
    .filter((x): x is NonNullable<typeof x> => x !== null && RUTAS_DESTINO[x.destino] !== null)
    .slice(0, 3);
  const opciones = delBack.length > 0 ? delBack : POR_DEFECTO;

  return (
    <View style={estilos.card}>
      <View style={estilos.titulo}>
        <MaterialCommunityIcons
          name="help-circle"
          size={iconos.linea}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.textoTitulo} accessibilityRole="header">
          No pude resolverlo.
        </Text>
      </View>
      <Text style={estilos.texto}>Puedes hacerlo tú directo:</Text>
      <View style={estilos.botones}>
        {opciones.map((o) => (
          <Boton key={o.destino} texto={o.texto} icono={o.icono} variante="tonal" onPress={() => onAbrir(o.destino)} />
        ))}
        {SOPORTE_WHATSAPP ? (
          <Boton
            texto="Escribir a soporte"
            icono="whatsapp"
            variante="text"
            accessibilityHint="Abre WhatsApp"
            onPress={() => {
              Linking.openURL(`https://wa.me/${SOPORTE_WHATSAPP.replace(/\D/g, '')}`).catch(() => undefined);
            }}
          />
        ) : null}
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  card: {
    borderWidth: bordes.fino,
    borderColor: color.outline,
    borderRadius: shape.medium,
    backgroundColor: color.surface,
    padding: espacio.l,
    gap: espacio.m,
  },
  titulo: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  textoTitulo: { ...type.titleMedium, color: color.onSurface, flex: 1 },
  texto: { ...type.bodyLarge, color: color.onSurfaceVariant },
  botones: { gap: tactil.separacion },
});
