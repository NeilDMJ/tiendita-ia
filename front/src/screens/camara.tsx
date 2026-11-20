import { MaterialCommunityIcons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { esErrorApi } from '@/api/cliente';
import type { ModoCamara } from '@/api/esquemas';
import { analizarAlta, analizarCobro, analizarTicket } from '@/api/vision';
import { Aviso } from '@/components/aviso';
import { BarraPasos } from '@/components/barra-pasos';
import { Boton } from '@/components/boton';
import { Encabezado } from '@/components/encabezado';
import { HojaInferior } from '@/components/hoja-inferior';
import { Tocable } from '@/components/tocable';
import { TIEMPOS_ANALISIS, type NombreIcono } from '@/constants';
import { useCarrito } from '@/estado/carrito';
import { useAccesibilidad } from '@/hooks/use-accesibilidad';
import { useConexion } from '@/hooks/use-conexion';
import { bordes, camara as tonosCamara, color, espacio, iconos, medidas, shape, tactil, type } from '@/theme';
import { comprimirImagen } from '@/utils/imagen';

type Fase = 'camara' | 'analizando' | 'error';
type Etapa = 'preparando' | 'enviando' | 'reconociendo';
type TipoFallo = 'ilegible' | 'vacio' | 'sinConexion' | 'tiempo';

const TITULOS: Record<ModoCamara, string> = {
  cobro: 'Cobrar con foto',
  alta: 'Agregar mercancía',
  ticket: 'Foto de ticket',
};

const INSTRUCCIONES: Record<ModoCamara, string> = {
  cobro: 'Que se vean todos los productos dentro del cuadro',
  alta: 'Pon el producto de frente dentro del cuadro',
  ticket: 'Que el ticket completo quede dentro del cuadro',
};

const CONSEJOS = [
  'Consejo: separa los productos y evita reflejos de la luz.',
  'Consejo: pon los productos de frente, con la etiqueta hacia la cámara.',
  'Consejo: si hay poca luz, activa "Luz" abajo a la derecha.',
];

const ETAPAS: { clave: Etapa | 'lista'; texto: string }[] = [
  { clave: 'lista', texto: 'Foto lista' },
  { clave: 'enviando', texto: 'Enviando foto' },
  { clave: 'reconociendo', texto: 'Reconociendo productos' },
];

const FALLOS: Record<TipoFallo, { titulo: string; mensaje: string; tipo: 'error' | 'sinConexion' | 'tiempo' }> = {
  ilegible: {
    tipo: 'error',
    titulo: 'No pudimos leer la foto',
    mensaje: 'Acércate un poco, que haya buena luz y evita reflejos en los empaques.',
  },
  vacio: {
    tipo: 'error',
    titulo: 'No encontramos productos en la foto',
    mensaje: 'Revisa que los productos estén dentro del cuadro y separados entre sí.',
  },
  sinConexion: {
    tipo: 'sinConexion',
    titulo: 'Sin internet no podemos revisar la foto',
    mensaje: 'Puedes cobrar buscando los productos. La venta se guarda y se enviará al reconectarte.',
  },
  tiempo: {
    tipo: 'tiempo',
    titulo: 'Esto tardó demasiado',
    mensaje: 'El servicio está lento ahora. Tu foto sigue aquí.',
  },
};

function esModo(m: unknown): m is ModoCamara {
  return m === 'cobro' || m === 'alta' || m === 'ticket';
}

/** Botón text con icono sobre las barras `inverseSurface` (Cerrar / Ayuda). */
function BotonBarra({
  icono,
  texto,
  onPress,
  etiqueta,
}: {
  icono: NombreIcono;
  texto: string;
  onPress: () => void;
  etiqueta?: string;
}) {
  return (
    <Tocable
      onPress={onPress}
      colorContenido={color.inverseOnSurface}
      colorAnillo={color.inverseOnSurface}
      radio={shape.full}
      accessibilityRole="button"
      accessibilityLabel={etiqueta ?? texto}
      style={estilos.botonBarra}
    >
      <MaterialCommunityIcons
        name={icono}
        size={iconos.linea}
        color={color.inverseOnSurface}
        accessibilityElementsHidden
        importantForAccessibility="no"
      />
      <Text style={estilos.textoBarra}>{texto}</Text>
    </Tocable>
  );
}

/** Icon button tonal 56 + etiqueta debajo (Galería / Luz). Seleccionado = `primary` + texto que cambia. */
function BotonIconoCamara({
  icono,
  texto,
  onPress,
  etiqueta,
  seleccionado,
}: {
  icono: NombreIcono;
  texto: string;
  onPress: () => void;
  etiqueta?: string;
  seleccionado?: boolean;
}) {
  const contenido = seleccionado ? color.onPrimary : color.onPrimaryContainer;
  return (
    <View style={estilos.columnaBoton}>
      <Tocable
        onPress={onPress}
        colorContenido={contenido}
        colorAnillo={color.inverseOnSurface}
        radio={shape.full}
        accessibilityRole="button"
        accessibilityLabel={etiqueta ?? texto}
        accessibilityState={seleccionado === undefined ? undefined : { selected: seleccionado }}
        style={[estilos.botonIcono, seleccionado ? estilos.botonIconoSeleccionado : null]}
      >
        <MaterialCommunityIcons
          name={icono}
          size={iconos.linea}
          color={contenido}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
      </Tocable>
      <Text style={estilos.textoOscuro} importantForAccessibility="no" accessibilityElementsHidden>
        {texto}
      </Text>
    </View>
  );
}

export function PantallaCamara({ modo: modoParam }: { modo?: string }) {
  const modo: ModoCamara = esModo(modoParam) ? modoParam : 'cobro';
  const [permiso, pedirPermiso] = useCameraPermissions();
  const { iniciarCronometro, cargarDeFoto } = useCarrito();
  const conectado = useConexion();
  const { reducirMovimiento } = useAccesibilidad();

  const camara = useRef<CameraView>(null);
  const control = useRef<AbortController | null>(null);
  const temporizadores = useRef<ReturnType<typeof setTimeout>[]>([]);

  const [fase, setFase] = useState<Fase>('camara');
  const [etapa, setEtapa] = useState<Etapa>('preparando');
  const [tardando, setTardando] = useState(false);
  const [fallo, setFallo] = useState<TipoFallo | null>(null);
  const [foto, setFoto] = useState<string | null>(null);
  const [luz, setLuz] = useState(false);
  const [lista, setLista] = useState(false);
  const [tomando, setTomando] = useState(false);
  const [errorCamara, setErrorCamara] = useState(false);
  const [claveCamara, setClaveCamara] = useState(0);
  const [errorGaleria, setErrorGaleria] = useState(false);
  const [ayuda, setAyuda] = useState(false);
  const [consejo] = useState(() => CONSEJOS[Math.floor(Math.random() * CONSEJOS.length)]);

  useEffect(() => {
    if (modo === 'cobro') iniciarCronometro();
    // solo al abrir la cámara
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(
    () => () => {
      control.current?.abort();
      temporizadores.current.forEach(clearTimeout);
    },
    [],
  );

  function limpiarTemporizadores() {
    temporizadores.current.forEach(clearTimeout);
    temporizadores.current = [];
  }

  function anunciar(texto: string) {
    AccessibilityInfo.announceForAccessibility(texto);
  }

  async function enviar(uri: string) {
    setFase('analizando');
    setFallo(null);
    setTardando(false);
    if (conectado === false) {
      setFallo('sinConexion');
      setFase('error');
      return;
    }
    setEtapa('enviando');
    anunciar('Enviando foto');
    limpiarTemporizadores();
    temporizadores.current.push(
      setTimeout(() => {
        setEtapa('reconociendo');
        anunciar('Reconociendo productos');
      }, TIEMPOS_ANALISIS.reconociendoMs),
      setTimeout(() => {
        setTardando(true);
        anunciar('Está tardando más de lo normal. Puedes seguir esperando.');
      }, TIEMPOS_ANALISIS.avisoTardandoMs),
    );
    const nuevo = new AbortController();
    control.current = nuevo;
    const opciones = { signal: nuevo.signal, tiempoMs: TIEMPOS_ANALISIS.limiteMs };

    try {
      if (modo === 'cobro') {
        const respuesta = await analizarCobro(uri, opciones);
        if (respuesta.items.length === 0) {
          setFallo('vacio');
          setFase('error');
          return;
        }
        cargarDeFoto(respuesta, uri);
        router.replace('/revision/cobro');
      } else if (modo === 'alta') {
        await analizarAlta(uri, opciones);
        router.replace('/revision/alta');
      } else {
        await analizarTicket(uri, opciones);
        router.replace('/revision/ticket');
      }
    } catch (e) {
      if (esErrorApi(e) && e.tipo === 'cancelado') return;
      const tipo = esErrorApi(e) ? e.tipo : 'servidor';
      const f: TipoFallo =
        tipo === 'sin_conexion'
          ? 'sinConexion'
          : tipo === 'imagen_no_procesable' || tipo === 'respuesta_invalida'
            ? 'ilegible'
            : 'tiempo';
      setFallo(f);
      setFase('error');
    } finally {
      limpiarTemporizadores();
    }
  }

  async function procesar(uriOriginal: string) {
    setFase('analizando');
    setEtapa('preparando');
    anunciar('Preparando foto');
    try {
      const comprimida = await comprimirImagen(uriOriginal);
      setFoto(comprimida);
      await enviar(comprimida);
    } catch {
      setFoto(uriOriginal);
      setFallo('ilegible');
      setFase('error');
    }
  }

  async function tomarFoto() {
    if (!camara.current || !lista || tomando) return;
    setTomando(true);
    try {
      const captura = await camara.current.takePictureAsync({ quality: 1 });
      await procesar(captura.uri);
    } catch {
      setErrorCamara(true);
    } finally {
      setTomando(false);
    }
  }

  async function elegirDeGaleria() {
    setErrorGaleria(false);
    try {
      const resultado = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 1 });
      if (resultado.canceled || !resultado.assets[0]) return;
      await procesar(resultado.assets[0].uri);
    } catch {
      setErrorGaleria(true);
    }
  }

  function cancelarAnalisis() {
    control.current?.abort();
    limpiarTemporizadores();
    setFase('camara');
  }

  function tomarOtra() {
    setFallo(null);
    setFoto(null);
    setFase('camara');
  }

  const cobrarBuscando = () => router.replace('/revision/cobro?agregar=1');
  const cerrar = () => (router.canGoBack() ? router.back() : router.replace('/cobrar'));

  // ---------- Analizando / error ----------
  if (fase !== 'camara') {
    const f = fallo ? FALLOS[fallo] : null;
    const indiceEtapa = etapa === 'preparando' ? 0 : etapa === 'enviando' ? 1 : 2;
    return (
      <SafeAreaView edges={['bottom']} style={estilos.pantallaClara}>
        <Encabezado
          titulo={fase === 'analizando' ? 'Analizando foto…' : 'No se pudo revisar'}
          tipoAtras="cerrar"
          onAtras={fase === 'analizando' ? cancelarAnalisis : cerrar}
        />
        <ScrollView
          contentContainerStyle={estilos.contenidoAnalisis}
          accessibilityState={{ busy: fase === 'analizando' }}
        >
          <BarraPasos pasos={['Foto', 'Revisar', 'Listo']} actual={0} />
          {foto ? (
            <Image
              source={{ uri: foto }}
              style={estilos.miniatura}
              contentFit="contain"
              accessibilityLabel="Foto que tomaste"
            />
          ) : null}

          {fase === 'analizando' ? (
            <View style={estilos.bloqueAnalisis} accessibilityLiveRegion="polite">
              {reducirMovimiento ? (
                <MaterialCommunityIcons
                  name="timer-sand"
                  size={iconos.grande}
                  color={color.primary}
                  accessibilityElementsHidden
                  importantForAccessibility="no"
                />
              ) : (
                <ActivityIndicator size="large" color={color.primary} />
              )}
              <Text style={estilos.subtitulo}>
                {etapa === 'preparando' ? 'Preparando la foto…' : 'Buscando los productos…'}
              </Text>
              {ETAPAS.map((e, i) => {
                const hecha = i < indiceEtapa || (i === 0 && etapa !== 'preparando');
                const actual = !hecha && i === indiceEtapa;
                return (
                  <View key={e.clave} style={estilos.filaEtapa}>
                    {actual && !reducirMovimiento ? (
                      <ActivityIndicator size="small" color={color.primary} />
                    ) : (
                      <MaterialCommunityIcons
                        name={hecha ? 'check-circle' : actual ? 'progress-clock' : 'circle-outline'}
                        size={iconos.linea}
                        color={hecha ? color.success : actual ? color.primary : color.onSurfaceVariant}
                        accessibilityElementsHidden
                        importantForAccessibility="no"
                      />
                    )}
                    <Text style={[estilos.cuerpo, !hecha && !actual && estilos.textoPendiente]}>
                      {e.texto}
                      {hecha ? ' (listo)' : actual ? ' (en curso)' : ' (pendiente)'}
                    </Text>
                  </View>
                );
              })}
              {tardando ? (
                <Aviso tipo="info" titulo="Está tardando más de lo normal." mensaje="Puedes seguir esperando." />
              ) : null}
            </View>
          ) : f ? (
            <Aviso tipo={f.tipo} titulo={f.titulo} mensaje={f.mensaje} enfocar />
          ) : null}
        </ScrollView>

        <View style={estilos.barraAcciones}>
          {fase === 'analizando' ? (
            <Boton texto="Tomar otra foto" icono="camera" variante="outlined" onPress={() => {
              cancelarAnalisis();
              tomarOtra();
            }} />
          ) : fallo === 'ilegible' ? (
            <>
              <Boton texto="Tomar otra foto" icono="camera" tamano="principal" onPress={tomarOtra} />
              <Boton texto="Elegir de galería" icono="image-multiple" variante="outlined" onPress={elegirDeGaleria} />
              {modo === 'cobro' ? (
                <Boton texto="Cobrar buscando producto" icono="magnify" variante="text" onPress={cobrarBuscando} />
              ) : null}
            </>
          ) : fallo === 'vacio' ? (
            <>
              <Boton texto="Tomar otra foto" icono="camera" tamano="principal" onPress={tomarOtra} />
              {modo === 'cobro' ? (
                <Boton texto="Agregar productos a mano" icono="plus" variante="outlined" onPress={cobrarBuscando} />
              ) : null}
            </>
          ) : fallo === 'sinConexion' ? (
            <>
              {modo === 'cobro' ? (
                <Boton texto="Cobrar buscando producto" icono="magnify" tamano="principal" onPress={cobrarBuscando} />
              ) : null}
              <Boton
                texto="Reintentar"
                icono="refresh"
                variante="outlined"
                onPress={() => (foto ? enviar(foto) : tomarOtra())}
              />
            </>
          ) : (
            <>
              <Boton
                texto="Reintentar con la misma foto"
                icono="refresh"
                tamano="principal"
                onPress={() => (foto ? enviar(foto) : tomarOtra())}
              />
              <Boton texto="Tomar otra foto" icono="camera" variante="outlined" onPress={tomarOtra} />
              {modo === 'cobro' ? (
                <Boton texto="Cobrar buscando producto" icono="magnify" variante="text" onPress={cobrarBuscando} />
              ) : null}
            </>
          )}
        </View>
      </SafeAreaView>
    );
  }

  // ---------- Permiso ----------
  if (!permiso) {
    return (
      <View style={[estilos.pantallaClara, estilos.centrado]}>
        <ActivityIndicator size="large" color={color.primary} accessibilityLabel="Preparando la cámara" />
      </View>
    );
  }

  if (!permiso.granted) {
    const sinDecidir = permiso.status === 'undetermined';
    const permanente = !sinDecidir && !permiso.canAskAgain;
    return (
      <SafeAreaView edges={['bottom']} style={estilos.pantallaClara}>
        <Encabezado titulo={TITULOS[modo]} tipoAtras="cerrar" onAtras={cerrar} />
        <ScrollView contentContainerStyle={estilos.contenidoPermiso}>
          <MaterialCommunityIcons
            name="camera"
            size={iconos.grande}
            color={color.onSurfaceVariant}
            accessibilityElementsHidden
            importantForAccessibility="no"
          />
          <Text style={estilos.titulo} accessibilityRole="header">
            {sinDecidir ? 'Necesitamos tu cámara' : 'La cámara está apagada para esta app'}
          </Text>
          <Text style={estilos.cuerpo}>
            {permanente
              ? 'Actívala en Ajustes > Permisos > Cámara.'
              : 'La usamos solo para ver los productos que vas a cobrar. No guardamos fotos de personas.'}
          </Text>
          {errorGaleria ? (
            <Aviso
              tipo="error"
              titulo="No tenemos permiso para ver tus fotos."
              accion={{ texto: 'Abrir ajustes', icono: 'cog', onPress: () => Linking.openSettings() }}
            />
          ) : null}
        </ScrollView>
        <View style={estilos.barraAcciones}>
          {permanente ? (
            <Boton texto="Abrir ajustes" icono="cog" tamano="principal" onPress={() => Linking.openSettings()} />
          ) : (
            <Boton
              texto={sinDecidir ? 'Permitir cámara' : 'Volver a intentar'}
              icono="camera"
              tamano="principal"
              onPress={pedirPermiso}
            />
          )}
          <Boton
            texto="Usar una foto de la galería"
            icono="image-multiple"
            variante="outlined"
            onPress={elegirDeGaleria}
          />
          {permanente && modo === 'cobro' ? (
            <Boton texto="Cobrar buscando producto" icono="magnify" variante="text" onPress={cobrarBuscando} />
          ) : null}
        </View>
      </SafeAreaView>
    );
  }

  // ---------- Vista de cámara ----------
  return (
    <SafeAreaView edges={['bottom']} style={estilos.pantallaOscura}>
      <View style={estilos.barraSuperior}>
        <BotonBarra icono="close" texto="Cerrar" onPress={cerrar} />
        <Text style={estilos.tituloOscuro} accessibilityRole="header">
          {TITULOS[modo]}
        </Text>
        <BotonBarra icono="help-circle" texto="Ayuda" onPress={() => setAyuda(true)} />
      </View>

      <View style={estilos.vista}>
        {errorCamara ? (
          <View style={estilos.errorCamara}>
            <Aviso
              tipo="error"
              titulo="No se pudo abrir la cámara."
              accion={{
                texto: 'Reintentar',
                icono: 'refresh',
                onPress: () => {
                  setErrorCamara(false);
                  setLista(false);
                  setClaveCamara((k) => k + 1);
                },
              }}
              accionSecundaria={{ texto: 'Usar foto de la galería', onPress: elegirDeGaleria }}
            />
          </View>
        ) : (
          <>
            <CameraView
              key={claveCamara}
              ref={camara}
              style={StyleSheet.absoluteFill}
              facing="back"
              enableTorch={luz}
              onCameraReady={() => setLista(true)}
              onMountError={() => setErrorCamara(true)}
              accessibilityLabel="Vista de la cámara"
            />
            <View style={estilos.guiaExterior} pointerEvents="none">
              <View style={estilos.guiaInterior}>
                <View style={estilos.cajaInstruccion}>
                  <Text style={estilos.instruccion}>{INSTRUCCIONES[modo]}</Text>
                </View>
              </View>
            </View>
          </>
        )}
      </View>

      {errorGaleria ? (
        <Aviso
          tipo="error"
          modo="franja"
          titulo="No tenemos permiso para ver tus fotos."
          accion={{ texto: 'Abrir ajustes', icono: 'cog', onPress: () => Linking.openSettings() }}
          onCerrar={() => setErrorGaleria(false)}
        />
      ) : null}

      <View style={estilos.franjaConsejo}>
        <MaterialCommunityIcons
          name="lightbulb-outline"
          size={iconos.linea}
          color={color.inverseOnSurface}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
        <Text style={estilos.textoConsejo}>{consejo}</Text>
      </View>

      <View style={estilos.barraInferior}>
        <BotonIconoCamara
          icono="image-multiple"
          texto="Galería"
          etiqueta="Elegir foto de la galería"
          onPress={elegirDeGaleria}
        />
        <View style={estilos.columnaDisparador}>
          <Tocable
            onPress={tomarFoto}
            disabled={!lista || tomando}
            colorContenido={color.inverseSurface}
            colorAnillo={color.inversePrimary}
            radio={shape.full}
            sinCapa={!lista || tomando}
            accessibilityRole="button"
            accessibilityLabel={tomando ? 'Tomando foto' : 'Tomar foto'}
            accessibilityState={{ disabled: !lista || tomando, busy: tomando }}
            style={[estilos.disparador, tomando && estilos.disparadorTomando]}
          >
            {tomando ? <ActivityIndicator color={color.primary} /> : null}
          </Tocable>
          <Text style={estilos.textoOscuro}>
            {tomando ? 'Tomando foto…' : lista ? 'Tomar foto' : 'Abriendo cámara…'}
          </Text>
        </View>
        <BotonIconoCamara
          icono={luz ? 'flashlight' : 'flashlight-off'}
          texto={luz ? 'Luz: Sí' : 'Luz: No'}
          etiqueta={luz ? 'Luz encendida. Toca para apagar' : 'Luz apagada. Toca para encender'}
          seleccionado={luz}
          onPress={() => setLuz((l) => !l)}
        />
      </View>

      <HojaInferior visible={ayuda} titulo="Cómo tomar una buena foto" onCerrar={() => setAyuda(false)}>
        <View style={estilos.filaEtapa}>
          <MaterialCommunityIcons name="check-circle" size={iconos.linea} color={color.success} />
          <Text style={estilos.cuerpo}>Bien: productos separados, de frente y con la etiqueta visible.</Text>
        </View>
        <View style={estilos.filaEtapa}>
          <MaterialCommunityIcons name="close-circle" size={iconos.linea} color={color.error} />
          <Text style={estilos.cuerpo}>Mal: productos amontonados o uno encima de otro.</Text>
        </View>
        <View style={estilos.filaEtapa}>
          <MaterialCommunityIcons name="close-circle" size={iconos.linea} color={color.error} />
          <Text style={estilos.cuerpo}>Mal: reflejos de luz sobre los empaques. Mueve un poco el teléfono.</Text>
        </View>
      </HojaInferior>
    </SafeAreaView>
  );
}

const estilos = StyleSheet.create({
  pantallaClara: { flex: 1, backgroundColor: color.surface },
  pantallaOscura: { flex: 1, backgroundColor: color.inverseSurface },
  centrado: { alignItems: 'center', justifyContent: 'center' },
  contenidoAnalisis: { paddingBottom: espacio.xl, gap: espacio.l },
  contenidoPermiso: { padding: espacio.l, gap: espacio.l, alignItems: 'flex-start' },
  miniatura: {
    height: medidas.miniaturaFoto,
    marginHorizontal: espacio.l,
    borderRadius: shape.large,
    overflow: 'hidden',
    backgroundColor: color.surfaceContainerHighest,
  },
  bloqueAnalisis: { paddingHorizontal: espacio.l, gap: espacio.m, alignItems: 'flex-start' },
  filaEtapa: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  titulo: { ...type.headlineSmall, color: color.onSurface },
  subtitulo: { ...type.titleLarge, color: color.onSurface },
  cuerpo: { ...type.bodyLargePlus, color: color.onSurface, flexShrink: 1 },
  textoPendiente: { color: color.onSurfaceVariant },
  barraAcciones: {
    padding: espacio.l,
    gap: tactil.separacion,
    borderTopWidth: bordes.fino,
    borderTopColor: color.outlineVariant,
    backgroundColor: color.surface,
  },
  barraSuperior: {
    minHeight: medidas.barraSuperior,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
    paddingHorizontal: espacio.xs,
    backgroundColor: color.inverseSurface,
  },
  tituloOscuro: { ...type.titleLarge, color: color.inverseOnSurface, flex: 1, textAlign: 'center' },
  botonBarra: {
    minWidth: tactil.minimo,
    minHeight: tactil.minimo,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: espacio.s,
    paddingHorizontal: espacio.m,
    borderRadius: shape.full,
  },
  textoBarra: { ...type.labelLarge, color: color.inverseOnSurface },
  columnaBoton: { alignItems: 'center', gap: espacio.xs, minWidth: tactil.principal + espacio.xl },
  botonIcono: {
    width: tactil.principal,
    height: tactil.principal,
    borderRadius: shape.full,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: color.primaryContainer,
  },
  botonIconoSeleccionado: { backgroundColor: color.primary },
  textoOscuro: { ...type.labelLarge, color: color.inverseOnSurface, textAlign: 'center' },
  vista: {
    flex: 1,
    overflow: 'hidden',
    backgroundColor: color.inverseSurface,
    borderRadius: shape.large,
    marginHorizontal: espacio.s,
  },
  errorCamara: { flex: 1, justifyContent: 'center', padding: espacio.l, backgroundColor: color.surface },
  // guía de encuadre: doble trazo claro + oscuro (≥ 3:1 contra cualquier imagen)
  guiaExterior: {
    position: 'absolute',
    top: espacio.xl,
    bottom: espacio.xl,
    left: espacio.xl,
    right: espacio.xl,
    borderWidth: bordes.grueso,
    borderColor: tonosCamara.oscuro,
  },
  guiaInterior: {
    flex: 1,
    borderWidth: bordes.grueso,
    borderColor: tonosCamara.claro,
    alignItems: 'center',
    justifyContent: 'center',
    padding: espacio.l,
  },
  cajaInstruccion: {
    backgroundColor: color.inverseSurface,
    paddingHorizontal: espacio.m,
    paddingVertical: espacio.s,
    borderRadius: shape.small,
  },
  instruccion: { ...type.titleMedium, color: color.inverseOnSurface, textAlign: 'center' },
  franjaConsejo: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: espacio.s,
    paddingHorizontal: espacio.l,
    paddingVertical: espacio.s,
    backgroundColor: color.inverseSurface,
  },
  textoConsejo: { ...type.bodyLarge, color: color.inverseOnSurface, flex: 1 },
  barraInferior: {
    minHeight: medidas.barraCamaraInferior,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: espacio.s,
    paddingVertical: espacio.m,
    backgroundColor: color.inverseSurface,
  },
  columnaDisparador: { alignItems: 'center', gap: espacio.xs },
  // disparador (excepción documentada en 01-cobrar §2.2; no es componente M3)
  disparador: {
    width: tactil.disparador,
    height: tactil.disparador,
    borderRadius: shape.full,
    backgroundColor: tonosCamara.claro,
    borderWidth: medidas.bordeDisparador,
    borderColor: tonosCamara.oscuro,
    alignItems: 'center',
    justifyContent: 'center',
    // anillo claro exterior para que el borde oscuro se vea sobre la barra
    outlineColor: tonosCamara.claro,
    outlineWidth: bordes.grueso,
    outlineStyle: 'solid',
  },
  disparadorTomando: { borderColor: color.primary },
});
