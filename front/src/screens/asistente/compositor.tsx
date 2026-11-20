import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState, type ComponentRef, type RefObject } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Boton } from '@/components/boton';
import { Campo } from '@/components/campo';
import { CHAT, type NombreIcono } from '@/constants';
import { bordes, color, espacio, iconos, tactil, type } from '@/theme';

export interface CompositorProps {
  valor: string;
  onCambiar: (v: string) => void;
  /** Recibe el texto ya validado (sin espacios sobrantes). */
  onEnviar: (texto: string) => void;
  onDetener: () => void;
  /** Esperando respuesta: Enviar se cambia por Detener (el botón nunca queda "muerto", EXC-4). */
  esperando: boolean;
  letraGrande: boolean;
  placeholder?: string;
  /** Texto de apoyo bajo el campo (p. ej. "Sin internet: se enviará al volver"). */
  ayuda?: { texto: string; icono: NombreIcono } | null;
  refCampo: RefObject<ComponentRef<typeof TextInput> | null>;
  /** `barra` = fija al pie de la pestaña (fondo y divisor propios); `plano` = dentro del pie de una hoja. */
  variante?: 'barra' | 'plano';
  /** Safe area inferior cuando no hay barra de navegación debajo (teclado cerrado sin tabs). */
  conSafeArea?: boolean;
}

/**
 * Compositor del chat (02-asistente §2.5): `Campo` outlined multilínea SIN etiqueta visible (EXC-11)
 * + `Boton` filled 56 solo icono ("Enviar" queda como etiqueta del lector). Enter = salto de línea; solo se envía con el botón.
 * Campo vacío: no se deshabilita el botón; muestra "Escribe tu pregunta primero" y enfoca el campo.
 */
export function Compositor({
  valor,
  onCambiar,
  onEnviar,
  onDetener,
  esperando,
  letraGrande,
  placeholder = 'Escribe tu pregunta…',
  ayuda,
  refCampo,
  variante = 'barra',
  conSafeArea = false,
}: CompositorProps) {
  const insets = useSafeAreaInsets();
  const [error, setError] = useState<string | null>(null);
  const largo = valor.length;

  function enviar() {
    const limpio = valor.trim();
    if (limpio === '') {
      setError('Escribe tu pregunta primero');
      refCampo.current?.focus();
      return;
    }
    setError(null);
    onEnviar(limpio);
  }

  const boton = esperando ? (
    <Boton
      texto="Detener"
      icono="stop"
      variante="tonal"
      tamano="principal"
      soloIcono
      style={letraGrande ? estilos.alFinal : undefined}
      accessibilityHint="Cancela la respuesta que está en camino"
      onPress={onDetener}
    />
  ) : (
    <Boton
      texto="Enviar"
      icono="send"
      tamano="principal"
      soloIcono
      style={letraGrande ? estilos.alFinal : undefined}
      onPress={enviar}
    />
  );

  return (
    <View
      style={[
        variante === 'barra' ? estilos.barra : estilos.plano,
        conSafeArea && { paddingBottom: espacio.s + insets.bottom },
      ]}
    >
      <View style={letraGrande ? estilos.columna : estilos.fila}>
        <Campo
          ref={refCampo}
          etiqueta="Tu pregunta"
          etiquetaOculta
          ocultarMensajes
          valor={valor}
          onCambiar={(v) => {
            if (error) setError(null);
            onCambiar(v);
          }}
          placeholder={placeholder}
          multilinea
          maxLineas={letraGrande ? 3 : 5}
          maxLength={CHAT.maxCaracteres}
          error={error}
          ayuda={ayuda?.texto}
          style={letraGrande ? undefined : estilos.campo}
        />
        {boton}
      </View>

      {error ? (
        <View style={estilos.mensaje} accessibilityLiveRegion="polite">
          <MaterialCommunityIcons
            name="alert-circle"
            size={iconos.linea}
            color={color.error}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.error}>{error}</Text>
        </View>
      ) : ayuda ? (
        <View style={estilos.mensaje}>
          <MaterialCommunityIcons
            name={ayuda.icono}
            size={iconos.linea}
            color={color.onSurfaceVariant}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.ayuda}>{ayuda.texto}</Text>
        </View>
      ) : null}
      {largo >= CHAT.avisoCaracteres ? (
        <Text style={estilos.contador} accessibilityLiveRegion="polite">
          {largo} de {CHAT.maxCaracteres}
        </Text>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  barra: {
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.s,
    gap: espacio.xs,
    backgroundColor: color.surfaceContainer,
    borderTopWidth: bordes.fino,
    borderTopColor: color.outlineVariant,
  },
  plano: { gap: espacio.xs },
  fila: { flexDirection: 'row', alignItems: 'flex-end', gap: tactil.separacion },
  columna: { gap: tactil.separacion },
  alFinal: { alignSelf: 'flex-end' },
  campo: { flex: 1 },
  mensaje: { flexDirection: 'row', gap: espacio.xs, alignItems: 'flex-start' },
  error: { ...type.labelLarge, color: color.error, flex: 1 },
  ayuda: { ...type.bodyLarge, color: color.onSurfaceVariant, flex: 1 },
  contador: { ...type.bodyLarge, color: color.onSurfaceVariant, textAlign: 'right' },
});
