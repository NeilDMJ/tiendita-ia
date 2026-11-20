import { useEffect, useState } from 'react';
import { Keyboard, Platform } from 'react-native';

/** true mientras el teclado está abierto (iOS: al empezar a abrir; Android: al terminar). */
export function useTecladoVisible() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const ios = Platform.OS === 'ios';
    const a = Keyboard.addListener(ios ? 'keyboardWillShow' : 'keyboardDidShow', () => setVisible(true));
    const b = Keyboard.addListener(ios ? 'keyboardWillHide' : 'keyboardDidHide', () => setVisible(false));
    return () => {
      a.remove();
      b.remove();
    };
  }, []);
  return visible;
}
