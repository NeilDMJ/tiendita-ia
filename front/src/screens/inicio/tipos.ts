import type { Producto } from '@/api/esquemas';

export interface ProductoMasVendido {
  clave: string;
  nombre: string;
  cantidad: number;
  totalGenerado: number;
}

export interface ResumenMetricasVentas {
  totalVendido: number;
  totalVentas: number;
  ticketPromedio: number;
  totalEfectivo: number;
  totalDigital: number;
  ventasPendientes: number;
  minutosAhorrados: number;
  topProductos: ProductoMasVendido[];
}

export interface ProductoAlertaStock extends Producto {
  bajo: boolean;
  agotado: boolean;
}

export interface CorteCajaProps {
  metricas: ResumenMetricasVentas;
  onVerHistorial: () => void;
}