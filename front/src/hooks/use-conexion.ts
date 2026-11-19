import NetInfo from '@react-native-community/netinfo';
import { useEffect, useState } from 'react';

/** true = hay conexión, false = sin conexión, null = aún no se sabe. */
export function useConexion() {
  const [conectado, setConectado] = useState<boolean | null>(null);
  useEffect(
    () =>
      NetInfo.addEventListener((estado) => {
        setConectado(estado.isConnected !== false && estado.isInternetReachable !== false);
      }),
    [],
  );
  return conectado;
}
