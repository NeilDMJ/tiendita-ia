import { MaterialCommunityIcons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { ChipSugerencia } from '@/components/chip-sugerencia';
import { ROLES, SUGERENCIAS_INICIO, TE_CONTESTAN } from '@/constants';
import { color, espacio, iconos, tactil, type } from '@/theme';

/** Cuerpo desplazable del estado vacío de la pestaña (02-asistente §2.4). Los chips van aparte, junto al compositor. */
export function EstadoVacioChat() {
  return (
    <ScrollView contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
      <MaterialCommunityIcons
        name="chat-outline"
        size={iconos.grande}
        color={color.onSurfaceVariant}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <Text style={estilos.titulo} accessibilityRole="header">
        ¿En qué te ayudo hoy?
      </Text>
      <Text style={estilos.texto}>
        Pregunta por tus ventas, lo que se te acaba o cómo cobrar. Antes de guardar o cobrar algo, siempre te pido que
        lo confirmes.
      </Text>
      <Text style={estilos.subtitulo} accessibilityRole="header">
        Te contestan:
      </Text>
      <View>
        {TE_CONTESTAN.map(({ rol, texto }) => (
          <View key={rol} style={estilos.item} accessible accessibilityLabel={`${ROLES[rol].nombre}: ${texto}`}>
            <MaterialCommunityIcons name={ROLES[rol].icono} size={iconos.linea} color={color.onSurfaceVariant} />
            <Text style={estilos.textoItem}>
              {ROLES[rol].nombre} · {texto}
            </Text>
          </View>
        ))}
      </View>
      <View style={estilos.item}>
        <MaterialCommunityIcons
          name="microphone"
          size={iconos.linea}
          color={color.onSurfaceVariant}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.texto}>También puedes dictar con el micrófono de tu teclado.</Text>
      </View>
    </ScrollView>
  );
}

/** "Prueba con:" — chips apilados a ancho completo, anclados arriba del compositor. Tocar = enviar. */
export function SugerenciasIniciales({ onEnviar }: { onEnviar: (texto: string) => void }) {
  return (
    <View style={estilos.chips}>
      <Text style={estilos.subtitulo}>Prueba con:</Text>
      {SUGERENCIAS_INICIO.map((s) => (
        <ChipSugerencia
          key={s.texto}
          texto={s.texto}
          icono={s.icono}
          anchoCompleto
          accessibilityHint="Envía esta pregunta"
          onPress={() => onEnviar(s.texto)}
        />
      ))}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenido: { padding: espacio.l, gap: espacio.m, alignItems: 'stretch' },
  titulo: { ...type.headlineSmall, color: color.onSurface },
  texto: { ...type.bodyLarge, color: color.onSurfaceVariant, flex: 1 },
  subtitulo: { ...type.titleSmall, color: color.onSurface },
  item: { flexDirection: 'row', alignItems: 'center', gap: espacio.l, minHeight: tactil.minimo },
  textoItem: { ...type.bodyLarge, color: color.onSurface, flex: 1 },
  chips: { paddingHorizontal: espacio.l, paddingVertical: espacio.s, gap: tactil.separacion },
});
