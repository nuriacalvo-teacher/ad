# Preparacion comun de los dos ficheros .command de esta carpeta.
# No se ejecuta suelto: lo cargan GRABAR-AUDIOS.command y ESCUCHAR-VOCES.command.

pausa() { echo; read -n 1 -s -r -p "Pulsa cualquier tecla para cerrar esta ventana."; echo; }

preparar_entorno() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "No encuentro Python 3 en este Mac."
    echo
    echo "Se instala solo, una vez: abre la aplicacion Terminal, escribe"
    echo
    echo "    python3"
    echo
    echo "y pulsa Enter. Saldra una ventana ofreciendote instalar las"
    echo "herramientas de desarrollo: acepta, espera a que termine y vuelve"
    echo "a hacer doble clic en este archivo."
    pausa
    return 1
  fi

  VENV=".venv-audio"
  if [ ! -d "$VENV" ]; then
    echo "Preparando las herramientas (esto solo pasa la primera vez)..."
    if ! python3 -m venv "$VENV"; then
      echo "No he podido preparar el entorno de Python."
      pausa
      return 1
    fi
  fi

  echo "Comprobando el generador de voz..."
  if ! "$VENV/bin/python" -m pip install --quiet --upgrade pip edge-tts; then
    echo
    echo "No he podido instalar el generador de voz."
    echo "Suele ser falta de conexion a internet. Comprueba la wifi y reintenta."
    pausa
    return 1
  fi
  return 0
}
