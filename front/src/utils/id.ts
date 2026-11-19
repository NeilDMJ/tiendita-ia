/** Identificador local suficiente para idempotencia y listas (no criptográfico). */
export function crearIdLocal(): string {
  const azar = () => Math.random().toString(16).slice(2, 10);
  return `${Date.now().toString(16)}-${azar()}-${azar()}`;
}
