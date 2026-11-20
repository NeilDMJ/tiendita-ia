import type { Producto } from '@/api/esquemas';
import type { NombreIcono } from '@/constants';

export interface ResumenMetricasVentas {
  totalVendido: number;
  totalVentas: number;
  ticketPromedio: number;
  totalEfectivo: number;
  totalDigital: number;
  ventasPendientes: number;
  minutosAhorrados: number;
}

export interface AtajoCamaraItem {
  id: string;
  icono: NombreIcono;
  titulo: string;
  detalle: string;
  ruta: string;
  etiquetaAccesible: string;
}

export interface ProductoAlertaStock extends Producto {
  bajo: boolean;
  agotado: boolean;
}

export interface CorteCajaProps {
  metricas: ResumenMetricasVentas;
  onVerHistorial: () => void;
}
