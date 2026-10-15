<p align="center">
  <img src="docs/assets/logo.png" alt="Slicra" width="280">
</p>

<p align="center">
  <strong>Corta una imagen en muchas: cuadrículas, sprite sheets y formas irregulares, cada una exportada como archivo propio con la máscara que quieras. Local, determinista, sin IA ni nube.</strong>
</p>

<p align="center"><a href="README.md">English</a></p>

---

Slicra **detecta** regiones en una imagen (una cuadrícula de avatares, stickers en una lámina, formas
sobre fondo transparente) y **extrae** cada una como PNG/WebP/JPEG individual. Detectar y enmascarar
son pasos independientes: una celda cuadrada puede exportarse como círculo o estrella, y una estrella
detectada puede exportarse como su rectángulo.

| Vista previa (lo que se va a cortar) | Recortes (PNG transparentes, cualquier forma) |
| --- | --- |
| <img src="docs/assets/demo-grid-preview.png" width="300"> | <img src="docs/assets/demo-cutouts.png" width="520"> |

- **Primero la vista previa.** `slicra preview` dibuja cada región con su índice antes de exportar.
- **Un motor, tres interfaces.** Biblioteca Python, CLI `slicra` y Agent Skill comparten el mismo pipeline.
- **Resultados honestos.** Advertencias, scores heurísticos y fallos explícitos en lugar de adivinar.
  Cero regiones es un error, nunca un éxito.
- **Seguro por defecto.** La imagen fuente solo se lee, no se sobrescribe nada sin `--overwrite`, los
  nombres no pueden salir del directorio de salida y el YAML se lee con `safe_load`. Sin red ni telemetría.

## Instalación

```bash
python -m pip install slicra             # núcleo: grid, grid-auto, manual
python -m pip install "slicra[opencv]"   # añade el detector de contornos (NumPy + OpenCV headless)
```

Aún no está publicado en PyPI. Mientras tanto, instala desde el repositorio:

```bash
git clone https://github.com/DailybotHQ/slicra.git && cd slicra
python -m pip install -e ".[opencv]"
```

Requiere Python 3.11+. Funciona en Linux, macOS y Windows. SVG todavía no está soportado.

## Inicio rápido

```bash
python examples/generate_fixtures.py                       # imágenes sintéticas en examples/input/

# 1. Lámina de 5x5 avatares -> 25 PNG + preview.png + manifest.json
slicra extract examples/input/avatars-grid.png \
  --mode grid --rows 5 --cols 5 --gap-x 12 --gap-y 12 --output output/avatars

# 2. Formas irregulares -> recortes transparentes que conservan la silueta
slicra extract --config examples/configs/irregular-shapes.yaml

# 3. Una carpeta completa de láminas, todos los recortes en una sola carpeta
slicra extract examples/input --mode grid-auto --output output/all --flat
```

## Modos de detección

| Modo | Úsalo para | Cómo funciona |
| --- | --- | --- |
| `grid` | Láminas con geometría conocida y regular | Cajas calculadas con `rows`, `cols`, `margins`, `gap_x`/`gap_y` |
| `grid-auto` | Láminas de avatares o mosaicos con espaciado irregular | Encuentra filas/columnas separadoras del color de fondo; falla si no hay separadores o no coinciden `rows`/`cols` |
| `contours` | Objetos separados sobre fondo liso o transparente | Umbral contra fondo/alfa, morfología opcional, componentes conectados; conserva cada silueta |
| `manual` | Zonas concretas o cuando la detección falla | Rectángulos y polígonos en coordenadas de píxel de origen (YAML/JSON) |
| `auto` | Si no sabes cuál | Prueba `grid-auto` y luego `contours`; registra cuál eligió y por qué |
| `template` | Presets reutilizables | Carga un preset incluido (`slicra templates`) o tu YAML |

`contours` no separa objetos superpuestos ni segmenta fotografías; avisa cuando el fondo no es uniforme.

**Vocabulario:** `gap` es el espacio *entre* celdas (nunca entra en un recorte); `margin` es el borde
alrededor de toda la cuadrícula; `crop_padding` agranda cada recorte después de detectar; `shape_inset`
encoge la máscara dentro de su caja.

## Formas, transparencia y redimensionado

`extraction.shape`: `rectangle`, `ellipse`, `circle` (`circle_fit: contain | center-square`), `star`
(`points`, `inner_ratio`, `outer_ratio`, `rotation`), `polygon` (polígono propio o
`extraction.polygon.points` relativos; nunca se adivina) y `original` (silueta detectada).

PNG y WebP conservan la transparencia. JPEG no tiene canal alfa: se aplana contra `output.background`
(blanco por defecto) y queda una advertencia. `output.resize` admite `contain` (por defecto, sin
deformar), `cover` (rellena y recorta al centro) y `stretch` (tamaño exacto, puede deformar).

## Configuración, CLI y API

Precedencia: **CLI > YAML > valores por defecto**. Ejemplos en [`examples/configs/`](examples/configs)
y referencia completa en [`skills/slicra/references/configuration.md`](skills/slicra/references/configuration.md).

```bash
slicra init --output slicra.yaml
slicra validate --config slicra.yaml
slicra inspect entrada.png --config slicra.yaml        # no escribe archivos
slicra preview entrada.png --config slicra.yaml --output preview.png
slicra extract entrada.png --config slicra.yaml --output ./out
slicra extract ./carpeta --config slicra.yaml --output ./lote [--flat]
```

```python
from slicra import ImageSlicer

slicer = ImageSlicer.from_config("slicra.yaml")
result = slicer.extract("avatars.png", output_dir="avatars")
print(result.region_count, result.manifest_path)
```

Códigos de salida: `0` ok · `2` configuración inválida · `3` detección fallida o cero regiones ·
`4` imagen no legible · `5` conflicto de salida · `6` falta una dependencia opcional.

## Agent Skill

[`skills/slicra/`](skills/slicra) es una [Agent Skill](https://agentskills.io/specification) portable
que enseña a un agente a inspeccionar, previsualizar y extraer con el CLI local. Para Claude Code,
cópiala en `.claude/skills/slicra/` o `~/.claude/skills/slicra/`; para otros agentes,
`npx skills add https://github.com/DailybotHQ/slicra --skill slicra`. Las imágenes nunca salen del equipo.

## Limitaciones

`contours` requiere objetos separables sobre fondo liso o transparente; `grid-auto` requiere
separadores de un color cercano al fondo; los scores son heurísticos, no probabilidades calibradas.
SVG y segmentación con IA no están implementados (el punto de extensión es `slicra.register_detector`).

## Desarrollo y licencia

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) y [AGENTS.md](AGENTS.md). Licencia [MIT](LICENSE).
