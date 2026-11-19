import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState, type ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { anilloFoco, bordes, colores, espacio, iconos, radios, tactil, tipografia } from '@/theme';

export interface HojaInferiorProps {
  visible: boolean;
  titulo: string;
  onCerrar: () => void;
  children: ReactNode;
  /** Contenido fijo al pie (p. ej. botón principal). */
  pie?: ReactNode;
  /** Oculta el botón Cerrar (diálogos que obligan a elegir). */
  sinCerrar?: boolean;
}

/**
 * Hoja inferior plana: fondo opaco, borde superior 2px, sin velo semitransparente
 * y sin animación (cumple movimiento reducido). El resto de la pantalla queda visible pero inerte.
 */
export function HojaInferior({ visible, titulo, onCerrar, children, pie, sinCerrar }: HojaInferiorProps) {
  const [focoCerrar, setFocoCerrar] = useState(false);
  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={onCerrar} statusBarTranslucent>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={estilos.raiz}>
        <Pressable
          style={estilos.fuera}
          onPress={sinCerrar ? undefined : onCerrar}
          accessible={false}
          importantForAccessibility="no"
        />
        <SafeAreaView edges={['bottom']} style={estilos.hoja} accessibilityViewIsModal>
          <View style={estilos.cabecera}>
            <Text style={estilos.titulo} accessibilityRole="header">
              {titulo}
            </Text>
            {sinCerrar ? null : (
              <Pressable
                onPress={onCerrar}
                onFocus={() => setFocoCerrar(true)}
                onBlur={() => setFocoCerrar(false)}
                accessibilityRole="button"
                accessibilityLabel="Cerrar"
                style={({ pressed }) => [estilos.cerrar, pressed && estilos.presionado, focoCerrar && anilloFoco]}
              >
                <MaterialCommunityIcons name="close" size={iconos.linea} color={colores.texto} />
                <Text style={estilos.textoCerrar}>Cerrar</Text>
              </Pressable>
            )}
          </View>
          <ScrollView
            style={estilos.cuerpo}
            contentContainerStyle={estilos.contenido}
            keyboardShouldPersistTaps="handled"
          >
            {children}
          </ScrollView>
          {pie ? <View style={estilos.pie}>{pie}</View> : null}
        </SafeAreaView>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const estilos = StyleSheet.create({
  raiz: { flex: 1, justifyContent: 'flex-end' },
  fuera: { flex: 1, backgroundColor: 'transparent' },
  hoja: {
    maxHeight: '90%',
    backgroundColor: colores.fondo,
    borderTopWidth: bordes.grueso,
    borderTopColor: colores.texto,
    borderRadius: radios.recto,
  },
  cabecera: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    paddingLeft: espacio.l,
    paddingRight: espacio.s,
    paddingTop: espacio.s,
  },
  titulo: { ...tipografia.subtitulo, color: colores.texto, flex: 1 },
  cerrar: {
    minHeight: tactil.minimo,
    minWidth: tactil.minimo,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
    paddingHorizontal: espacio.s,
    borderRadius: radios.medio,
  },
  presionado: { backgroundColor: colores.superficie },
  textoCerrar: { ...tipografia.etiqueta, color: colores.texto },
  cuerpo: { flexGrow: 0 },
  contenido: { padding: espacio.l, gap: espacio.l },
  pie: {
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.m,
    gap: tactil.separacion,
    borderTopWidth: bordes.fino,
    borderTopColor: colores.divisor,
  },
});
