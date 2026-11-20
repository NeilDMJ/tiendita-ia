import NetInfo from '@react-native-community/netinfo';
import { useEffect, useState } from 'react';

/** true = hay conexión, false = sin conexión, null = aún no se sabe. */
export function useConexion() {
  const [conectado, setConectado] = useState<boolean | null>(null);
  useEffect(
    () =>
      NetInfo.addEventListener((estado) => {
        // Solo isConnected: isInternetReachable da falsos negativos (prueba contra un servidor externo
        // que puede estar bloqueado o lento) aunque el back sí responda. Si de verdad no hay salida,
        // la petición falla y cliente.ts lo reporta como 'sin_conexion'.
        setConectado(estado.isConnected !== false);
      }),
    [],
  );
  return conectado;
}
