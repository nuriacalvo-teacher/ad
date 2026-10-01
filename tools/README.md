# Narración del anuncio

## El problema

El anuncio se narraba con la voz del propio navegador, y esa voz no es la misma
en cada aparato:

| Dispositivo | Qué voz sale de fábrica | Cómo suena |
|---|---|---|
| Mac con Chrome o Edge | voces de Google / Microsoft | bien |
| Mac con Safari | voz **compacta** de Apple | metálica |
| iPhone / iPad | voz **compacta** de Apple | metálica |
| Android | Google TTS | bien |
| Windows | voces de Microsoft | de correcto a muy bien |
| Linux / Vitalinux | normalmente **ninguna** | no narra |

Para un anuncio que se proyecta en la pizarra digital eso es un problema: suena
distinto en cada aula.

Con la narración grabada suena **igual en todas partes**.

## Primero: elige las voces y óyelas

### Comparar todas las voces

- **En el Mac:** doble clic en `tools/COMPARAR-VOCES.command`.
- **Online:** pestaña **Actions** → *Grabar la narración del anuncio* →
  **Run workflow**, marcando **comparativa**. Descarga *voces-para-escuchar*.

Un MP3 con todas las voces británicas y españolas leyendo la misma frase, cada
una diciendo antes su nombre.

### Escribir tu elección

`tools/voces.txt`:

```
voz_en = en-GB-SoniaNeural
voz_es = es-ES-ElviraNeural
```

Si te equivocas escribiendo un nombre, avisa antes de grabar y lista las
válidas.

### Oír tu elección

Doble clic en `tools/ESCUCHAR-VOCES.command`, u **Run workflow** marcando
**muestra**. Graba las dos primeras escenas de cada idioma. No toca las
páginas.

## Cómo grabar

### Opción A · online, sin instalar nada

Pestaña **Actions** → *Grabar la narración del anuncio* → **Run workflow** →
**Run workflow**, sin marcar nada. Tarda un par de minutos y lo sube él solo.

> Si falla al subir: **Settings → Actions → General → Workflow permissions →
> Read and write permissions**.

### Opción B · en el Mac, con doble clic

**Code** → **Download ZIP**, descomprimir, doble clic en
`tools/GRABAR-AUDIOS.command`. Si macOS lo bloquea: **Ajustes del Sistema →
Privacidad y seguridad → Abrir igualmente**.

### Opción C · desde el terminal

```bash
python3 -m venv .venv-audio
.venv-audio/bin/pip install edge-tts
.venv-audio/bin/python tools/build_ad.py
git add audio && git commit -m "Narración grabada" && git push
```

Para un solo idioma: `--lang en` o `--lang es`.

### En los tres casos

**No hay que tocar `index.html` ni `es.html`.** Las dos páginas buscan
`audio/manifest.json` al arrancar: si está, usan las grabaciones; si no, siguen
usando la voz del navegador, como antes.

Son 20 escenas (10 por idioma), poco más de dos minutos de audio y menos de
1 MB.

## Si cambias el guion

El índice guarda **el texto de cada escena**. Si cambias una frase de `SCENES`
y no vuelves a grabar, esa escena nota que la grabación ya no corresponde y
pasa sola a la voz del navegador, en vez de narrar algo que ya no toca. Las
demás siguen usando su grabación.

Para ponerla al día, vuelve a lanzar la grabación: solo rehace lo que ha
cambiado.

## Nota sobre el karaoke

La versión anterior iluminaba los subtítulos palabra a palabra mientras el
navegador hablaba, usando los avisos `onboundary` del motor de voz. Se ha
quitado: los subtítulos aparecen completos desde el principio de cada escena.
