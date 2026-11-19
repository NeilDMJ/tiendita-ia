import { pedirJson, USAR_MOCKS } from './cliente';
import { MensajeAsistente, type EstadoPantalla } from './esquemas';
import { esperar, mockRespuestaAsistente } from './mocks';

export async function enviarMensaje(texto: string, historial: MensajeAsistente[] = []) {
  if (USAR_MOCKS) return esperar(900).then(() => mockRespuestaAsistente(texto));
  return pedirJson('/asistente/mensaje', MensajeAsistente, { texto, historial });
}

export async function pedirAyudaTutor(estado: EstadoPantalla) {
  if (USAR_MOCKS)
    return esperar(700).then(
      (): MensajeAsistente => ({ rol: 'tutor', texto: 'Escribe la CLABE de 18 números que te dio tu cliente y toca “Continuar”.' }),
    );
  return pedirJson('/asistente/tutor', MensajeAsistente, estado);
}
