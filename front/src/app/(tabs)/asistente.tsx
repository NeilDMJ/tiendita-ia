import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useMutation } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { enviarMensaje } from '@/api/asistente';
import { ErrorApi } from '@/api/cliente';
import type { MensajeAsistente } from '@/api/esquemas';
import { bordes, colores, espacio, radios, tactil, tipografia } from '@/theme';
import { anonimizar } from '@/utils/anonimizar';

type Burbuja =
  | { id: string; autor: 'usuario'; texto: string }
  | { id: string; autor: 'agente'; mensaje: MensajeAsistente }
  | { id: string; autor: 'error'; texto: string };

const BIENVENIDA: Burbuja = {
  id: 'bienvenida',
  autor: 'agente',
  mensaje: {
    rol: 'banco',
    texto:
      'Hola, te guío paso a paso en tu app del banco. Yo no veo tu cuenta ni tu app: tú haces cada paso allá y vuelves aquí si tienes dudas.',
    advertencias: ['Aquí nunca compartas tu NIP, token, CVV ni contraseñas. Yo nunca te los pediré.'],
    respuestas_rapidas: ['Quiero hacer una transferencia en BBVA', 'Quiero pagar un servicio', 'Quiero ver mi saldo'],
  },
};

const AVISO_BLOQUEO: MensajeAsistente = {
  rol: 'banco',
  texto:
    'No envié tu mensaje porque parece traer datos privados (tarjeta, CLABE, NIP o clave). Por tu seguridad, no los escribas aquí. Cuéntame lo que quieres hacer sin esos datos y te guío.',
};

let contador = 0;
const nuevoId = () => `m${++contador}`;

export default function Asistente() {
  const [burbujas, setBurbujas] = useState<Burbuja[]>([BIENVENIDA]);
  const [texto, setTexto] = useState('');
  const lista = useRef<FlatList<Burbuja>>(null);
  const insets = useSafeAreaInsets();

  const agregar = (b: Burbuja) => {
    setBurbujas((prev) => [...prev, b]);
    setTimeout(() => lista.current?.scrollToEnd({ animated: true }), 50);
  };

  const envio = useMutation({
    mutationFn: (enviar: string) =>
      enviarMensaje(
        enviar,
        burbujas.flatMap((b) => (b.autor === 'agente' ? [b.mensaje] : [])),
      ),
    onSuccess: (mensaje) => agregar({ id: nuevoId(), autor: 'agente', mensaje }),
    onError: (e) =>
      agregar({
        id: nuevoId(),
        autor: 'error',
        texto: e instanceof ErrorApi ? e.mensaje : 'No se pudo enviar. Intenta de nuevo.',
      }),
  });

  const enviar = (original: string) => {
    const limpio = original.trim();
    if (!limpio || envio.isPending) return;
    setTexto('');
    agregar({ id: nuevoId(), autor: 'usuario', texto: limpio });

    // Privacidad: lo que sale del teléfono va anonimizado; si trae datos sensibles, no sale.
    const { texto: seguro, bloquear } = anonimizar(limpio);
    if (bloquear) {
      agregar({ id: nuevoId(), autor: 'agente', mensaje: AVISO_BLOQUEO });
      return;
    }
    envio.mutate(seguro);
  };

  return (
    <KeyboardAvoidingView
      style={estilos.contenedor}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={insets.top}
    >
      <Text style={[estilos.titulo, { paddingTop: insets.top + espacio.l }]} accessibilityRole="header">
        Guía del banco
      </Text>

      <FlatList
        ref={lista}
        data={burbujas}
        keyExtractor={(b) => b.id}
        contentContainerStyle={estilos.lista}
        renderItem={({ item }) => <ItemBurbuja burbuja={item} alElegir={enviar} />}
        ListFooterComponent={
          envio.isPending ? (
            <Text style={estilos.escribiendo} accessibilityLiveRegion="polite">
              Escribiendo…
            </Text>
          ) : undefined
        }
      />

      <View style={[estilos.barra, { paddingBottom: Math.max(insets.bottom, espacio.s) }]}>
        <TextInput
          style={estilos.campo}
          value={texto}
          onChangeText={setTexto}
          placeholder="Escribe qué quieres hacer"
          placeholderTextColor={colores.textoSecundario}
          accessibilityLabel="Mensaje"
          returnKeyType="send"
          onSubmitEditing={() => enviar(texto)}
          editable={!envio.isPending}
        />
        <Pressable
          style={({ pressed }) => [estilos.enviar, pressed && estilos.enviarPresionado]}
          onPress={() => enviar(texto)}
          disabled={envio.isPending || !texto.trim()}
          accessibilityRole="button"
          accessibilityLabel="Enviar"
        >
          <MaterialCommunityIcons name="send" size={22} color={colores.sobreAcento} />
          <Text style={estilos.enviarTexto}>Enviar</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

function ItemBurbuja({ burbuja, alElegir }: { burbuja: Burbuja; alElegir: (t: string) => void }) {
  if (burbuja.autor === 'usuario') {
    return (
      <View style={[estilos.burbuja, estilos.burbujaUsuario]}>
        <Text style={estilos.textoUsuario}>{burbuja.texto}</Text>
      </View>
    );
  }
  if (burbuja.autor === 'error') {
    return (
      <View style={[estilos.burbuja, estilos.burbujaError]} accessibilityRole="alert">
        <MaterialCommunityIcons name="alert-circle-outline" size={22} color={colores.peligro} />
        <Text style={estilos.textoError}>{burbuja.texto}</Text>
      </View>
    );
  }

  const m = burbuja.mensaje;
  return (
    <View style={{ gap: espacio.s }}>
      <View style={[estilos.burbuja, estilos.burbujaAgente]}>
        <Text style={estilos.textoAgente}>{m.texto}</Text>

        {m.guia_verificada === false && (
          <Text style={estilos.sinVerificar}>Guía general sin verificar: tu app puede verse distinta.</Text>
        )}

        {m.pasos?.map((p) => (
          <View key={p.n} style={estilos.paso}>
            <Text style={estilos.pasoNumero}>{p.n}</Text>
            <View style={{ flex: 1 }}>
              {p.pantalla ? <Text style={estilos.pasoPantalla}>{p.pantalla}</Text> : null}
              <Text style={estilos.textoAgente}>{p.texto}</Text>
            </View>
          </View>
        ))}

        {m.advertencias?.map((a) => (
          <View key={a} style={estilos.advertencia}>
            <MaterialCommunityIcons name="shield-alert-outline" size={22} color={colores.texto} />
            <Text style={[estilos.textoAgente, { flex: 1 }]}>{a}</Text>
          </View>
        ))}
      </View>

      {m.respuestas_rapidas?.length ? (
        <View style={estilos.rapidas}>
          {m.respuestas_rapidas.map((r) => (
            <Pressable
              key={r}
              style={({ pressed }) => [estilos.rapida, pressed && estilos.rapidaPresionada]}
              onPress={() => alElegir(r)}
              accessibilityRole="button"
            >
              <Text style={estilos.rapidaTexto}>{r}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const estilos = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: colores.fondo },
  titulo: { ...tipografia.titulo, color: colores.texto, paddingHorizontal: espacio.l, paddingBottom: espacio.s },
  lista: { padding: espacio.l, gap: espacio.m },
  escribiendo: { ...tipografia.cuerpo, color: colores.textoSecundario },

  burbuja: { padding: espacio.m, borderRadius: radios.medio, gap: espacio.s, maxWidth: '92%' },
  burbujaUsuario: { alignSelf: 'flex-end', backgroundColor: colores.acento },
  textoUsuario: { ...tipografia.cuerpo, color: colores.sobreAcento },
  burbujaAgente: {
    alignSelf: 'flex-start',
    backgroundColor: colores.superficie,
    borderWidth: bordes.fino,
    borderColor: colores.borde,
  },
  textoAgente: { ...tipografia.cuerpo, color: colores.texto },
  burbujaError: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: bordes.grueso,
    borderColor: colores.peligro,
  },
  textoError: { ...tipografia.cuerpo, color: colores.peligro, flexShrink: 1 },
  sinVerificar: { ...tipografia.etiqueta, color: colores.texto },

  paso: { flexDirection: 'row', gap: espacio.m, alignItems: 'flex-start' },
  pasoNumero: {
    ...tipografia.etiqueta,
    minWidth: 28,
    textAlign: 'center',
    color: colores.sobreAcento,
    backgroundColor: colores.acento,
    borderRadius: radios.chico,
    paddingVertical: 2,
  },
  pasoPantalla: { ...tipografia.etiqueta, color: colores.textoSecundario },
  advertencia: {
    flexDirection: 'row',
    gap: espacio.s,
    alignItems: 'flex-start',
    borderTopWidth: bordes.fino,
    borderTopColor: colores.borde,
    paddingTop: espacio.s,
  },

  rapidas: { flexDirection: 'row', flexWrap: 'wrap', gap: tactil.separacion },
  rapida: {
    minHeight: tactil.minimo,
    justifyContent: 'center',
    paddingHorizontal: espacio.l,
    borderWidth: bordes.grueso,
    borderColor: colores.acento,
    borderRadius: radios.medio,
    backgroundColor: colores.fondo,
  },
  rapidaPresionada: { backgroundColor: colores.superficie },
  rapidaTexto: { ...tipografia.etiqueta, color: colores.acento },

  barra: {
    flexDirection: 'row',
    gap: espacio.s,
    padding: espacio.s,
    borderTopWidth: bordes.grueso,
    borderTopColor: colores.borde,
    backgroundColor: colores.fondo,
  },
  campo: {
    flex: 1,
    minHeight: tactil.minimo,
    ...tipografia.cuerpo,
    color: colores.texto,
    borderWidth: bordes.grueso,
    borderColor: colores.borde,
    borderRadius: radios.medio,
    paddingHorizontal: espacio.m,
  },
  enviar: {
    minHeight: tactil.minimo,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs,
    paddingHorizontal: espacio.l,
    borderRadius: radios.medio,
    backgroundColor: colores.acento,
  },
  enviarPresionado: { backgroundColor: '#0847C2' },
  enviarTexto: { ...tipografia.etiqueta, color: colores.sobreAcento },
});
