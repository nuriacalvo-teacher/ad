#!/bin/bash
#
#  Comparar todas las voces disponibles  ·  para Mac
#
#  Haz DOBLE CLIC en este archivo desde el Finder.
#
#  Graba un MP3 en el que TODAS las voces britanicas e irlandesas disponibles
#  leen la misma frase, cada una diciendo antes su nombre. Sirve para elegir
#  por oido las que narraran el anuncio.
#
#  No cambia nada de la aplicacion.
#

set -u
cd "$(dirname "$0")/.." || exit 1
. "tools/_entorno.sh"

echo "=================================================="
echo "   Comparativa de voces"
echo "=================================================="
echo

preparar_entorno || exit 1

echo
".venv-audio/bin/python" tools/build_ad.py --audition
ESTADO=$?

if [ $ESTADO -ne 0 ]; then
  echo
  echo "No he podido grabar la comparativa. Los mensajes de arriba dicen por que."
  pausa
  exit $ESTADO
fi

echo
if [ -f audio/comparativa-voces.mp3 ]; then
  echo "Abriendo la comparativa..."
  open audio/comparativa-voces.mp3 2>/dev/null || open -R audio/comparativa-voces.mp3 2>/dev/null || true
  echo
  echo "Cuando sepas cuales quieres, abre  tools/voces.txt  y escribe ahi sus"
  echo "nombres. Despues haz doble clic en GRABAR-AUDIOS.command."
fi
pausa
