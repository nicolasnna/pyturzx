# TurZX 5.2" Display Manager — Linux

Monitor de sistema y gestor visual para la pantalla IPS USB TurZX 5.2" en Linux.
Desarrollado en Python, diseñado específicamente para el modelo `1cbe:0050`.

---

## Contexto del hardware

| Propiedad | Valor |
|---|---|
| Modelo | TurZX 5.2" IPS |
| USB Vendor ID | `1cbe` (Luminary Micro) |
| USB Product ID | `0050` |
| Resolución (portrait) | 720 × 1280 px |
| Conexión | USB directo (no serial/COM) |
| Almacenamiento interno | micro SD montada en `/tmp/sdcard/mmcblk0p1/` |
| Protocolo | Comandos binarios encriptados con DES (`slv3tuzx`) |

La pantalla corre un Linux embebido con su propio filesystem. La comunicación
con la PC se realiza exclusivamente a través del bus USB identificado como
`Bus 001 Device 004: ID 1cbe:0050 Luminary Micro Inc. TURZX1.0`.

---

## Base de código de referencia

El proyecto se basa en el trabajo de ingeniería inversa ya realizado por la comunidad:

- **`mathoudebine/turing-smart-screen-python`** (v3.10.0) — librería principal,
  protocolo USB completo implementado en `library/lcd/lcd_comm_turing_usb.py`.
- **`edopex/turing-smart-screen-python`** — fork con reproductor de video optimizado,
  editor drag & drop, integración MangoHud y aceleración NumPy.

El archivo central del protocolo es `lcd_comm_turing_usb.py`, que implementa:
- Comunicación USB via `pyusb` + `libusb-1.0`
- Encriptación DES de todos los comandos
- Envío de imágenes PNG/JPEG
- Streaming de video H.264 en chunks
- Upload de archivos al filesystem interno de la pantalla
- Comandos de reproducción nativa desde SD

---

## Comandos USB clave (ya documentados)

```python
# IDs de comando del protocolo TurZX USB
CMD_SYNC           = 10    # handshake inicial
CMD_RESTART        = 11    # reiniciar pantalla
CMD_BRIGHTNESS     = 14    # brillo (0-102)
CMD_FRAME_RATE     = 15    # FPS de reproducción
CMD_H264_CHUNK_SIZE = 17   # negociar tamaño de chunk
CMD_OPEN_FILE      = 38    # abrir archivo en SD para escritura
CMD_WRITE_FILE     = 39    # escribir chunk de archivo
CMD_DELETE_FILE    = 40    # borrar archivo de SD
CMD_PLAY_FILE      = 98    # reproducir archivo desde SD (modo 1)
CMD_UPLOAD_PNG     = 102   # enviar imagen PNG por USB
CMD_PLAY_FILE_2    = 110   # reproducir archivo desde SD (modo 2)
CMD_STOP_STREAM    = 111   # detener stream
CMD_STOP_MEDIA     = 112   # detener media
CMD_SYNC_DELAY     = 122   # control de flujo
CMD_PLAY_FILE_3    = 113   # reproducir imagen desde SD
CMD_UPLOAD_JPEG    = 101   # enviar imagen JPEG por USB
CMD_PLAY_H264      = 121   # stream H.264 chunk a chunk
CMD_STREAM_STATUS  = 122   # estado del buffer de stream
CMD_SAVE_SETTINGS  = 125   # guardar configuración en pantalla
CMD_REFRESH_STORAGE = 100  # consultar espacio en SD
```

Rutas del filesystem interno de la pantalla:
```
/tmp/sdcard/mmcblk0p1/video/   ← videos H.264
/tmp/sdcard/mmcblk0p1/img/     ← imágenes PNG
```

---

## Estrategia de renderizado

### Video de fondo
Subir el video **una sola vez** a la micro SD via USB, luego reproducirlo con
`_play_command()`. El chip interno decodifica H.264 a 60 FPS de forma nativa —
**0% de carga USB y 0% de CPU** durante la reproducción.

El video debe estar en formato H.264 (el código ya incluye extracción automática
desde MP4 via `ffmpeg` o parser Python puro como fallback).

### Overlay de estadísticas
Mientras el video corre en hardware, el overlay (CPU, GPU, RAM, etc.) se envía
como imágenes PNG/JPEG por USB con fondo transparente superpuesto sobre el video.
Solo se envían los píxeles que cambiaron entre frames (delta compression via
`ImageChops.difference()`), reduciendo drásticamente el tráfico USB.

### FPS en juegos
Integración con **MangoHud**: un proceso puente (`fps_bridge.py`) lee los logs
CSV que genera MangoHud en `~/mangohud_logs/`, parsea los datos y los escribe
en `/tmp/mangohud_stats.json` cada segundo. El dashboard los consume desde ahí.

---

## Requerimientos del sistema

- **OS**: Linux (CachyOS / Arch base)
- **Python**: 3.11+ recomendado (probado con 3.14.6)
- **Shell**: fish shell
- **GPU**: AMD o NVIDIA (detección automática)
- **MangoHud**: opcional, para FPS en juegos

### Regla udev (obligatoria, se configura una vez)
```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="1cbe", ATTR{idProduct}=="0050", MODE="0666"' \
  | sudo tee /etc/udev/rules.d/99-turzx.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### Dependencias Python
```
pyusb          # comunicación USB
pycryptodome   # encriptación DES del protocolo
Pillow         # procesamiento de imágenes y compositing
opencv-python  # decodificación de video MP4
numpy          # aceleración matricial para compositing
psutil         # CPU, RAM, temperatura
pynvml         # GPU NVIDIA
pyamdgpuinfo   # GPU AMD
PyQt6          # GUI de configuración
pyyaml         # archivos de tema
```

### Dependencias del sistema
```bash
sudo pacman -S tk libusb ffmpeg
```

---

## Funcionalidades a implementar

### 1. Comunicación con la pantalla
- [ ] Wrapper limpio sobre `lcd_comm_turing_usb.py` del repo de referencia
- [ ] Upload de video H.264 a la micro SD interna
- [ ] Reproducción nativa desde SD (`_play_command`)
- [ ] Envío de overlay PNG/JPEG con delta compression
- [ ] Control de brillo, orientación, frame rate

### 2. Sistema de temas
- [ ] Formato de tema en YAML o JSON
- [ ] Soporte para video de fondo (referencia a archivo local que se sube a la SD)
- [ ] Widgets posicionables: texto, barras de progreso, gráficos de línea
- [ ] Fuentes TTF configurables por widget
- [ ] Colores, tamaños y posiciones X/Y por widget
- [ ] Temas predefinidos incluidos

### 3. Monitor de sistema
- [ ] CPU: porcentaje de uso, frecuencia, temperatura
- [ ] GPU: uso, VRAM, temperatura (AMD y NVIDIA)
- [ ] RAM: uso total, libre, porcentaje
- [ ] Disco: uso, libre
- [ ] Red: velocidad de upload/download
- [ ] FPS via MangoHud (cuando hay juego activo)
- [ ] Intervalo de actualización configurable por métrica

### 4. Integración MangoHud (FPS bridge)
- [ ] Proceso `fps_bridge.py` en segundo plano
- [ ] Lee logs CSV de `~/mangohud_logs/`
- [ ] Detecta automáticamente si hay juego activo (archivo actualizado < 3 seg)
- [ ] Escribe stats en `/tmp/mangohud_stats.json`
- [ ] El dashboard consume el JSON — desacopla el bridge del renderer

Configuración requerida en `~/.config/MangoHud/MangoHud.conf`:
```ini
output_folder=~/mangohud_logs
autostart_log=1
log_interval=100
```

### 5. GUI de configuración
- [ ] Construida en PyQt6
- [ ] Panel de control: iniciar/detener servicios con un click
- [ ] Selector de tema activo
- [ ] Editor visual de layout (drag & drop de widgets)
- [ ] Vista previa a escala del layout en el canvas
- [ ] Cambios reflejados en tiempo real en la pantalla física
- [ ] Configuración de red, GPU, intervalos de actualización
- [ ] Exportar/importar temas

### 6. Inicio automático
- [ ] Servicio `systemd --user` para el dashboard principal
- [ ] Servicio `systemd --user` para el fps_bridge
- [ ] Ambos inician silenciosamente al iniciar sesión
- [ ] La pantalla comienza a funcionar al encender la PC

```ini
# ~/.config/systemd/user/turzx-dashboard.service
[Unit]
Description=TurZX Display Dashboard

[Service]
ExecStart=/usr/bin/python3 /opt/turzx-app/main.py
Restart=on-failure
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
```

---

## Estructura del proyecto propuesta

```
turzx-app/
├── main.py                   # punto de entrada del dashboard
├── fps_bridge.py             # puente MangoHud → JSON
├── gui/
│   ├── control_center.py     # panel de control PyQt6
│   └── layout_editor.py      # editor drag & drop
├── core/
│   ├── display.py            # wrapper de comunicación con la pantalla
│   ├── renderer.py           # compositing de frames con delta compression
│   ├── sensors.py            # lectura de hardware (CPU/GPU/RAM/etc.)
│   └── video.py              # gestión de video (upload, reproducción SD)
├── themes/
│   ├── default/
│   │   ├── theme.yaml        # definición del tema
│   │   └── background.mp4    # video de fondo
│   └── minimal/
│       └── theme.yaml
├── assets/
│   └── fonts/                # fuentes TTF
├── config.yaml               # configuración global
├── layout.json               # posiciones guardadas de widgets
├── requirements.txt
└── systemd/
    ├── turzx-dashboard.service
    └── turzx-fps-bridge.service
```

---

## Notas para el agente de desarrollo

- La clase base de comunicación a reutilizar es `LcdCommTuringUSB` de
  `lcd_comm_turing_usb.py`. No reimplementar el protocolo desde cero.
- La clave DES del protocolo es `slv3tuzx` — ya implementada en `encrypt_command_packet()`.
- El video de fondo **debe convertirse a H.264 Annex-B** antes de subirse.
  Usar `ffmpeg` si está disponible, sino el parser Python incluido en el repo de referencia.
- El overlay de stats se envía como PNG con `send_pil_image_auto()`.
- Delta compression: usar `ImageChops.difference()` de Pillow para detectar
  qué región del frame cambió y enviar solo ese rectángulo.
- Para GPU AMD usar `pyamdgpuinfo`, para NVIDIA usar `pynvml`. Detectar
  automáticamente cuál está disponible.
- El fps_bridge y el dashboard deben correr como **procesos separados**,
  comunicándose solo via `/tmp/mangohud_stats.json`.
- Resolución objetivo siempre: **720 × 1280 px** (portrait).
- Orientación actual en uso: `DISPLAY_REVERSE: true` (portrait invertido).
