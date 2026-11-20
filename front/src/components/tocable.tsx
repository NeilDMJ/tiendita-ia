import { useState, type ComponentRef, type ReactNode, type Ref } from 'react';
import {
  Platform,
  Pressable,
  StyleSheet,
  View,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { anilloFoco, conAlfa, estado } from '@/theme';

export type EstadoTocable = { pressed: boolean; enfocado: boolean; hover: boolean };

export interface TocableProps extends Omit<PressableProps, 'style' | 'children' | 'android_ripple'> {
  /** Color del CONTENIDO (texto/icono): la capa de estado M3 se pinta con él. */
  colorContenido: string;
  /** Radio de esquinas para que la capa (iOS/web) y el ripple respeten la forma. */
  radio?: number;
  /** Sin capa ni ripple (deshabilitado). Sigue siendo enfocable. */
  sinCapa?: boolean;
  /** Ripple sin límite (icon buttons circulares). */
  rippleSinLimite?: boolean;
  /** Dibuja el anillo de foco M3 al recibir foco de teclado. Default true. */
  conAnilloFoco?: boolean;
  /** Color del anillo de foco. Default `secondary`; sobre fondos oscuros (`inverseSurface`) usar `inverseOnSurface`. */
  colorAnillo?: string;
  style?: StyleProp<ViewStyle> | ((s: EstadoTocable) => StyleProp<ViewStyle>);
  children?: ReactNode | ((s: EstadoTocable) => ReactNode);
  ref?: Ref<ComponentRef<typeof View>>;
}

const ES_ANDROID = Platform.OS === 'android';

/**
 * Capa de estado M3 común a todo lo tocable (00-sistema §6):
 * - Android: `android_ripple` nativo al 10 % del color del contenido (foreground).
 * - iOS / web: capa absoluta del color del contenido al 10 % (presionado/foco) u 8 % (hover).
 * - Foco: capa + anillo 3 dp `secondary`.
 * Sin escalado ni cambios de opacidad del componente.
 */
export function Tocable({
  colorContenido,
  radio = 0,
  sinCapa = false,
  rippleSinLimite = false,
  conAnilloFoco = true,
  colorAnillo,
  style,
  children,
  onFocus,
  onBlur,
  onHoverIn,
  onHoverOut,
  ref,
  ...resto
}: TocableProps) {
  const [enfocado, setEnfocado] = useState(false);
  const [hover, setHover] = useState(false);

  return (
    <Pressable
      ref={ref}
      {...resto}
      android_ripple={
        sinCapa
          ? undefined
          : { color: conAlfa(colorContenido, estado.pressed), foreground: true, borderless: rippleSinLimite }
      }
      onFocus={(e) => {
        setEnfocado(true);
        onFocus?.(e);
      }}
      onBlur={(e) => {
        setEnfocado(false);
        onBlur?.(e);
      }}
      onHoverIn={(e) => {
        setHover(true);
        onHoverIn?.(e);
      }}
      onHoverOut={(e) => {
        setHover(false);
        onHoverOut?.(e);
      }}
      style={({ pressed }) => {
        const s: EstadoTocable = { pressed, enfocado, hover };
        return [
          ES_ANDROID && !rippleSinLimite && radio > 0 ? { overflow: 'hidden' as const } : null,
          typeof style === 'function' ? style(s) : style,
          enfocado && conAnilloFoco ? anilloFoco : null,
          enfocado && conAnilloFoco && colorAnillo ? { outlineColor: colorAnillo } : null,
        ];
      }}
    >
      {({ pressed }) => {
        const s: EstadoTocable = { pressed, enfocado, hover };
        const opacidad = sinCapa
          ? 0
          : pressed && !ES_ANDROID
            ? estado.pressed
            : enfocado
              ? estado.focus
              : hover
                ? estado.hover
                : 0;
        return (
          <>
            {opacidad > 0 ? (
              <View
                pointerEvents="none"
                style={[
                  StyleSheet.absoluteFill,
                  { backgroundColor: colorContenido, opacity: opacidad, borderRadius: radio },
                ]}
              />
            ) : null}
            {typeof children === 'function' ? children(s) : children}
          </>
        );
      }}
    </Pressable>
  );
}
