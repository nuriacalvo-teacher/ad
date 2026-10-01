#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_ad.py · graba la narracion del anuncio, en ingles y en castellano.

Por que existe
--------------
El anuncio se narraba con la voz del propio navegador, y esa voz no es la
misma en cada aparato: en Safari y en iPhone suena metalica, y en Linux muchas
veces no hay ninguna instalada. Este script graba las diez escenas de cada
idioma una sola vez, con voces neuronales, y a partir de ahi el video suena
igual en cualquier sitio donde se proyecte.

Uso
---
    pip install edge-tts
    python3 tools/build_ad.py

Deja los ficheros en audio/ junto con audio/manifest.json. Las dos paginas
detectan ese manifest solas: si esta, usan las grabaciones; si no, siguen
usando la voz del navegador.

El manifest guarda el texto de cada escena. Si cambias el guion y no vuelves a
grabar, esa escena se da cuenta de que la grabacion ya no corresponde y pasa
sola a la voz del navegador, en vez de narrar algo que ya no toca.

Opciones utiles
---------------
    --lang en            graba solo un idioma
    --force              regraba aunque ya exista
    --demo               una muestra corta, para oir las voces
    --audition           comparativa con todas las voces del idioma
    --list-voices        lista las voces disponibles
"""

import argparse
import asyncio
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AUDIO_DIR = os.path.join(ROOT, "audio")
VOICES_FILE = os.path.join(HERE, "voces.txt")

# Un fichero por idioma, con su voz.
PAGES = {
    "en": {"file": "index.html", "voice": "en-GB-SoniaNeural", "locales": ["en-GB", "en-IE"]},
    "es": {"file": "es.html",    "voice": "es-ES-ElviraNeural", "locales": ["es-ES"]},
}
RATE = "+0%"


def load_voice_config():
    """Lee tools/voces.txt para cambiar las voces sin tocar el codigo."""
    if not os.path.exists(VOICES_FILE):
        return
    for line in io.open(VOICES_FILE, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().lower()
        if key.startswith("voz_") and val.strip():
            lang = key[4:]
            if lang in PAGES:
                PAGES[lang]["voice"] = val.strip()


# ---------------------------------------------------------------------------
# 1 · leer el guion de cada pagina
# ---------------------------------------------------------------------------
class JsLiteral(object):
    """Lector minimo de literales JavaScript: objetos con clave sin comillas,
    cadenas, numeros, true/false/null, comentarios y comas sobrantes."""

    def __init__(self, text):
        self.s = text
        self.i = 0

    def error(self, msg):
        line = self.s.count("\n", 0, self.i) + 1
        raise ValueError("%s (linea %d)" % (msg, line))

    def skip(self):
        while self.i < len(self.s):
            c = self.s[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif self.s.startswith("/*", self.i):
                end = self.s.find("*/", self.i + 2)
                self.i = len(self.s) if end < 0 else end + 2
            elif self.s.startswith("//", self.i):
                end = self.s.find("\n", self.i)
                self.i = len(self.s) if end < 0 else end + 1
            else:
                return

    def value(self):
        self.skip()
        if self.i >= len(self.s):
            self.error("fin de fichero inesperado")
        c = self.s[self.i]
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c in "\"'":
            return self.string()
        if self.s.startswith("true", self.i):
            self.i += 4
            return True
        if self.s.startswith("false", self.i):
            self.i += 5
            return False
        if self.s.startswith("null", self.i):
            self.i += 4
            return None
        m = re.match(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", self.s[self.i:])
        if not m:
            self.error("valor no reconocido: %r" % self.s[self.i:self.i + 20])
        self.i += m.end()
        txt = m.group(0)
        return float(txt) if ("." in txt or "e" in txt or "E" in txt) else int(txt)

    def string(self):
        quote = self.s[self.i]
        self.i += 1
        out = []
        while True:
            if self.i >= len(self.s):
                self.error("cadena sin cerrar")
            c = self.s[self.i]
            if c == "\\":
                nxt = self.s[self.i + 1]
                self.i += 2
                if nxt == "u":
                    out.append(chr(int(self.s[self.i:self.i + 4], 16)))
                    self.i += 4
                else:
                    out.append({"n": "\n", "t": "\t", "r": "\r", "b": "\b",
                                "f": "\f", "0": "\0"}.get(nxt, nxt))
            elif c == quote:
                self.i += 1
                return "".join(out)
            else:
                out.append(c)
                self.i += 1

    def arr(self):
        self.i += 1                      # [
        out = []
        while True:
            self.skip()
            if self.s[self.i] == "]":
                self.i += 1
                return out
            out.append(self.value())
            self.skip()
            if self.s[self.i] == ",":
                self.i += 1
            elif self.s[self.i] != "]":
                self.error("se esperaba , o ]")

    def obj(self):
        self.i += 1                      # {
        out = {}
        while True:
            self.skip()
            if self.s[self.i] == "}":
                self.i += 1
                return out
            if self.s[self.i] in "\"'":
                key = self.string()
            else:
                m = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", self.s[self.i:])
                if not m:
                    self.error("clave no reconocida")
                key = m.group(0)
                self.i += m.end()
            self.skip()
            if self.s[self.i] != ":":
                self.error("se esperaba : tras la clave %r" % key)
            self.i += 1
            out[key] = self.value()
            self.skip()
            if self.s[self.i] == ",":
                self.i += 1
            elif self.s[self.i] != "}":
                self.error("se esperaba , o }")



def scenes_of(lang):
    path = os.path.join(ROOT, PAGES[lang]["file"])
    src = io.open(path, encoding="utf-8").read()
    marca = "var SCENES = ["
    start = src.find(marca)
    if start < 0:
        raise SystemExit("No encuentro 'var SCENES = [' en %s" % PAGES[lang]["file"])
    reader = JsLiteral(src)
    reader.i = start + len("var SCENES = ")
    return [sc["say"] for sc in reader.arr()]


# ---------------------------------------------------------------------------
# 2 · MP3 sin dependencias externas: duracion y silencio
# ---------------------------------------------------------------------------
BITRATES_V1 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
BITRATES_V2 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}


def mp3_frames(data):
    """Recorre las tramas MPEG Layer III. Devuelve (offset, tamano, muestras,
    frecuencia). Se salta ID3 y cualquier basura entre tramas."""
    i = 0
    if data[:3] == b"ID3":
        size = 0
        for b in data[6:10]:
            size = (size << 7) | (b & 0x7F)
        i = 10 + size
    n = len(data)
    while i + 4 <= n:
        if data[i] != 0xFF or (data[i + 1] & 0xE0) != 0xE0:
            i += 1
            continue
        version = (data[i + 1] >> 3) & 0x03      # 3=MPEG1 2=MPEG2 0=MPEG2.5
        layer = (data[i + 1] >> 1) & 0x03        # 1 = Layer III
        if version == 1 or layer != 1:
            i += 1
            continue
        br_index = (data[i + 2] >> 4) & 0x0F
        sr_index = (data[i + 2] >> 2) & 0x03
        padding = (data[i + 2] >> 1) & 0x01
        if br_index in (0, 15) or sr_index == 3:
            i += 1
            continue
        rate = RATES[version][sr_index]
        bitrate = (BITRATES_V1 if version == 3 else BITRATES_V2)[br_index] * 1000
        samples = 1152 if version == 3 else 576
        size = (samples // 8) * bitrate // rate + padding
        if size < 4 or i + size > n:
            break
        yield i, size, samples, rate
        i += size


def mp3_info(data):
    """(duracion en segundos, frecuencia de muestreo)."""
    total, rate = 0, 24000
    for _, _, samples, sr in mp3_frames(data):
        total += samples
        rate = sr
    return (total / float(rate) if rate else 0.0), rate


def silence_mp3(seconds, rate=24000):
    """Tramas MPEG-2 Layer III mono vacias: se decodifican como silencio y se
    pueden pegar delante o detras de cualquier MP3 de la misma frecuencia."""
    sr_index = {22050: 0, 24000: 1, 16000: 2}.get(rate)
    if sr_index is None:                          # frecuencia rara: sin silencio
        return b""
    bitrate = 32000
    frame_len = (576 // 8) * bitrate // rate      # 96 bytes a 24 kHz
    header = bytes([
        0xFF,
        0b11110011,                               # MPEG2 · Layer III · sin CRC
        (4 << 4) | (sr_index << 2),               # 32 kbps · frecuencia · sin padding
        0b11000000,                               # mono
    ])
    frame = header + b"\x00" * (frame_len - 4)
    count = int(round(seconds / (576.0 / rate)))
    return frame * max(0, count)



# ---------------------------------------------------------------------------
# 3 · sintesis
# ---------------------------------------------------------------------------
async def synth(text, voice):
    import edge_tts
    chunks = []
    communicate = edge_tts.Communicate(text, voice, rate=RATE)
    async for item in communicate.stream():
        if item["type"] == "audio":
            chunks.append(item["data"])
    if not chunks:
        raise RuntimeError("edge-tts no devolvio audio para la voz %s" % voice)
    return b"".join(chunks)


async def build_lang(lang, force, existing):
    """Un MP3 por escena. Se guarda tambien el texto, para que la pagina pueda
    comprobar que la grabacion corresponde al guion que tiene delante."""
    voice = PAGES[lang]["voice"]
    says = scenes_of(lang)
    previas = {s.get("t"): s for s in (existing or {}).get("scenes", []) if s.get("t")}
    print("\n%s · %d escenas · voz %s" % (lang.upper(), len(says), voice))
    out = []
    for i, say in enumerate(says):
        nombre = "%s-%d.mp3" % (lang, i)
        destino = os.path.join(AUDIO_DIR, nombre)
        antigua = previas.get(say)
        if (not force and antigua and antigua.get("f") == nombre
                and os.path.exists(destino)):
            print("  [%2d/%2d] (ya estaba)  %.1f s" % (i + 1, len(says), antigua["d"]))
            out.append(antigua)
            continue
        print("  [%2d/%2d] %-58s" % (i + 1, len(says), say[:58]), end="", flush=True)
        audio = await synth(say, voice)
        with open(destino, "wb") as fh:
            fh.write(audio)
        dur = round(mp3_info(audio)[0], 2)
        print("  ->  %.1f s" % dur)
        out.append({"f": nombre, "d": dur, "t": say})
    return {"voice": voice, "scenes": out}


async def build_demo(langs):
    if not os.path.isdir(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)
    piezas, rate = [], 24000
    for lang in langs:
        voice = PAGES[lang]["voice"]
        says = scenes_of(lang)[:2]
        print("\n%s · voz %s" % (lang.upper(), voice))
        for say in says:
            print("  %s" % say[:70])
            audio = await synth(say, voice)
            rate = mp3_info(audio)[1]
            if piezas:
                piezas.append(silence_mp3(0.8, rate))
            piezas.append(audio)
    out = os.path.join(AUDIO_DIR, "muestra-voces.mp3")
    with open(out, "wb") as fh:
        fh.write(b"".join(piezas))
    print("\nMuestra lista: %s  (%d segundos)" % (out, round(mp3_info(b"".join(piezas))[0])))
    print("Escuchala. Si te convencen, graba el anuncio entero; si no, cambia")
    print("las voces en tools/voces.txt. Este fichero no afecta a las paginas.")
    return 0


async def build_audition(locales):
    import edge_tts
    voices = [v for v in await edge_tts.list_voices()
              if any(v["Locale"].startswith(loc) for loc in locales)]
    voices.sort(key=lambda v: (v["Locale"], v["Gender"], v["ShortName"]))
    if not voices:
        print("No he encontrado voces para: %s" % ", ".join(locales), file=sys.stderr)
        return 1
    if not os.path.isdir(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)
    es = any(l.startswith("es") for l in locales)
    frase = ("English Apps. Aprender ingles puede ser tan emocionante como tu juego favorito."
             if es else
             "English Apps. What if learning English felt as exciting as your favourite game?")
    print("Grabando una comparativa con %d voces...\n" % len(voices))
    piezas, elapsed, rate = [], 0.0, 24000
    for v in voices:
        short = v["ShortName"]
        label = short.split("-")[-1].replace("Neural", "")
        print("  %d:%02d  %-32s %s" % (elapsed // 60, elapsed % 60, short, v["Gender"]))
        try:
            audio = await synth("%s. %s" % (label, frase), short)
        except Exception as exc:                        # noqa: BLE001
            print("        (fallo: %s)" % exc)
            continue
        seconds, rate = mp3_info(audio)
        if piezas:
            gap = silence_mp3(0.9, rate)
            piezas.append(gap)
            elapsed += mp3_info(gap)[0]
        piezas.append(audio)
        elapsed += seconds
    out = os.path.join(AUDIO_DIR, "comparativa-voces.mp3")
    with open(out, "wb") as fh:
        fh.write(b"".join(piezas))
    print("\nComparativa lista: %s  (%d min %02d s)" % (out, elapsed // 60, elapsed % 60))
    print("\nApunta la que mas te guste y escribela en tools/voces.txt.")
    return 0


async def check_voices(names):
    import edge_tts
    try:
        catalog = {v["ShortName"] for v in await edge_tts.list_voices()}
    except Exception:                                   # noqa: BLE001
        return True
    mal = sorted(n for n in names if n not in catalog)
    if not mal:
        return True
    print("\nEstas voces de tools/voces.txt no existen:\n", file=sys.stderr)
    for n in mal:
        print("    %s" % n, file=sys.stderr)
    print("\nDisponibles para ingles britanico y castellano de Espana:\n", file=sys.stderr)
    for n in sorted(v for v in catalog if v.startswith(("en-GB", "en-IE", "es-ES"))):
        print("    %s" % n, file=sys.stderr)
    return False


async def main_async(args):
    load_voice_config()
    langs = [args.lang] if args.lang else list(PAGES)

    if args.list_voices:
        import edge_tts
        quiere = [l for lang in langs for l in PAGES[lang]["locales"]]
        for v in await edge_tts.list_voices():
            if v["Locale"].startswith(tuple(quiere)):
                print("%-32s %-8s %s" % (v["ShortName"], v["Gender"], v["Locale"]))
        return 0

    if args.audition:
        return await build_audition([l for lang in langs for l in PAGES[lang]["locales"]])
    if not await check_voices([PAGES[l]["voice"] for l in langs]):
        return 1
    if args.demo:
        return await build_demo(langs)

    if not os.path.isdir(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)
    manifest_path = os.path.join(AUDIO_DIR, "manifest.json")
    data = {"version": 1, "langs": {}}
    if os.path.exists(manifest_path):
        try:
            data = json.load(io.open(manifest_path, encoding="utf-8"))
            data.setdefault("langs", {})
        except ValueError:
            data = {"version": 1, "langs": {}}

    for lang in langs:
        data["langs"][lang] = await build_lang(lang, args.force, data["langs"].get(lang))

    with io.open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print("")
    for lang, l in sorted(data["langs"].items()):
        tot = sum(s["d"] for s in l["scenes"])
        print("%s · %d escenas · %d min %02d s · voz %s" %
              (lang.upper(), len(l["scenes"]), tot // 60, tot % 60, l["voice"]))
    print("\nManifest: %s" % manifest_path)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Graba la narracion del anuncio con edge-tts.")
    ap.add_argument("--lang", choices=sorted(PAGES), help="graba solo este idioma")
    ap.add_argument("--force", action="store_true", help="regraba aunque ya exista")
    ap.add_argument("--demo", action="store_true", help="graba solo una muestra corta")
    ap.add_argument("--audition", action="store_true", help="comparativa con todas las voces")
    ap.add_argument("--list-voices", action="store_true", help="lista las voces disponibles")
    args = ap.parse_args()
    try:
        import edge_tts                                # noqa: F401
    except ImportError:
        print("Falta edge-tts. Instalalo con:  pip install edge-tts", file=sys.stderr)
        return 1
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
