import { useConexion } from '@/hooks/use-conexion';

import { Aviso } from './aviso';

/**
 * Banner persistente cuando no hay internet (Nielsen #1 y #9). Icono + texto, no solo color.
 * `Aviso` modo franja tipo `sinConexion` (surfaceContainerHigh): no es un error del usuario.
 */
export function AvisoConexion() {
  const conectado = useConexion();
  if (conectado !== false) return null;
  return (
    <Aviso
      tipo="sinConexion"
      modo="franja"
      titulo="Sin conexión"
      mensaje="Lo que registres se guarda y se enviará al reconectarte."
    />
  );
}
