# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

Dashboard de sistema para la pantalla IPS USB **TurZX 5.2"** (`1cbe:0050`). Python + POO, diseñado para aprender patrones de diseño mientras se construye algo funcional.

## Setup

### Regla udev (una sola vez)
```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="1cbe", ATTR{idProduct}=="0050", MODE="0666"' \
  | sudo tee /etc/udev/rules.d/99-turzx.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### Dependencias del sistema
```bash
sudo pacman -S tk libusb ffmpeg
```

### Dependencias Python
```bash
pip install pyusb pycryptodome Pillow opencv-python numpy psutil pynvml pyamdgpuinfo PyQt6 pyyaml
```

## Ejecutar

```bash
python main.py                # dashboard principal
python fps_bridge.py          # proceso separado para FPS (MangoHud)
```

Los servicios systemd van en `~/.config/systemd/user/` (ver `systemd/`).

## Arquitectura

### Flujo principal

`DisplayManager` (orquestador) posee: `EventBus` + `Renderer` + lista de `BaseSensor` + `DisplayDriver`.

1. Sensores leen hardware en loop → publican `SensorReading` en `EventBus`
2. `Renderer` suscrito al bus → compone frames (Pillow) → envía delta PNG al driver
3. `TurZX52Driver` maneja toda la comunicación USB binaria con la pantalla

### Patrones de diseño implementados

| Patrón | Dónde |
|--------|-------|
| Strategy | Drivers intercambiables (`TurZX52Driver`, `MockDriver`) |
| Observer/Pub-Sub | `EventBus` desacopla sensores del renderer |
| Factory | `WidgetFactory.create_from_config()` crea widgets desde YAML |
| Template Method | `BaseSensor.read()` define flujo; subclases implementan `_read_raw()` |
| Dependency Injection | `DisplayManager` recibe driver, no lo instancia |
| Protocol (duck typing) | `DisplayDriver`, `Sensor`, `Renderable`, `GpuBackend` son `typing.Protocol` |

### Rendering

- **Video de fondo**: subir H.264 a la SD interna UNA vez → `play_media()` → 0% CPU/USB durante reproducción
- **Overlay stats**: PNG por USB, solo el rectángulo que cambió (`ImageChops.difference()`) — delta compression
- **Resolución**: siempre 720×1280 px (portrait), con `DISPLAY_REVERSE: true`

### FPS bridge

`fps_bridge.py` es un proceso independiente. Lee logs CSV de `~/mangohud_logs/`, escribe `/tmp/mangohud_stats.json`. `FpsSensor` solo lee ese JSON — los procesos nunca se tocan directamente.

## Notas críticas de implementación

- **No reimplementar el protocolo USB**: envolver `LcdCommTuringUSB` de `mathoudebine/turing-smart-screen-python` (`library/lcd/lcd_comm_turing_usb.py`) en la arquitectura POO descrita.
- **Clave DES del protocolo**: `slv3tuzx` — ya implementada en `encrypt_command_packet()` del repo de referencia.
- **Video**: convertir a H.264 Annex-B antes de subir. Usar `ffmpeg` si disponible; fallback al parser Python del repo de referencia.
- **GPU**: `pyamdgpuinfo` para AMD, `pynvml` para NVIDIA. `sensors/gpu/__init__.py` tiene `detect_gpu_backend()` que elige automáticamente.
- **Dataclasses para datos, clases para comportamiento**: `SensorReading` es dataclass, `CpuSensor` es clase con métodos.
- **Protocols sobre ABC** cuando sea posible — más flexible para duck typing.
- **Event bus síncrono al principio** — si se necesita async después, el desacoplamiento lo hace trivial.
- **Tests diferidos** — foco en funcionalidad por hito; agregar tests después del MVP.

## Hitos de implementación (en orden)

1. Conexión USB + handshake + brillo (`drivers/`)
2. Envío de imagen PNG y streaming H.264 (`utils/video.py`, `utils/delta.py`)
3. Upload/reproducción desde micro SD interna
4. Sensores + event bus + widgets + renderer + temas YAML (`core/`, `sensors/`, `widgets/`, `themes/`)
5. GUI PyQt6 con editor drag & drop (`gui/`)
6. Integración MangoHud + servicios systemd

Cada hito debe ser ejecutable de forma independiente con un script de prueba.
