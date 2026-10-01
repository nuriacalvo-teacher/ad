# Carpeta de audio

Aquí va la narración grabada del anuncio.

Se genera desde la pestaña **Actions** → *Grabar la narración del anuncio* →
**Run workflow**, o con doble clic en `tools/GRABAR-AUDIOS.command`.

Contenido después de generarla:

- `en-0.mp3` … `en-9.mp3` — las diez escenas en inglés (`index.html`).
- `es-0.mp3` … `es-9.mp3` — las diez escenas en castellano (`es.html`).
- `manifest.json` — índice con la voz, la duración y el texto de cada escena.

Las páginas buscan `manifest.json` al arrancar. **Si esta carpeta está vacía no
pasa nada**: se usa la voz del navegador, como antes.

Ver `tools/README.md` para los detalles.
