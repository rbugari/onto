from pathlib import Path
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe

ROOT = Path(__file__).parent
FRAMES = ROOT / "viewport_frames"
PREPARED = ROOT / "prepared"
PREPARED.mkdir(exist_ok=True)
WIDTH, HEIGHT = 1280, 720
DURATION = 7

items = [
    ("01_inicio.png", "Inicio: seleccionamos el proyecto y vemos el estado de las tres etapas del piloto."),
    ("02_atlas.png", "Atlas inventaria Fabric y la documentacion, mide la preparacion y deja visibles los gaps."),
    ("03_nexo.png", "Nexo transforma la evidencia en candidatos trazables y permite registrar decisiones humanas."),
    ("04_argos.png", "Argos trabaja exclusivamente sobre la release local aprobada y su paquete de contexto."),
    ("05_argos_respuesta.png", "Una pregunta dentro de la evidencia recibe una respuesta con fuentes y estado answered."),
    ("06_argos_abstencion.png", "Una pregunta fuera del dominio no se inventa: Argos se abstiene y deja trazabilidad."),
]

font_path = Path("C:/Windows/Fonts/segoeui.ttf")
font_bold_path = Path("C:/Windows/Fonts/segoeuib.ttf")
font = ImageFont.truetype(str(font_path), 27)
font_bold = ImageFont.truetype(str(font_bold_path), 30)

for index, (filename, caption) in enumerate(items, start=1):
    source = Image.open(FRAMES / filename).convert("RGB")
    source.thumbnail((WIDTH, HEIGHT - 130), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (16, 24, 32))
    x = (WIDTH - source.width) // 2
    y = (HEIGHT - 130 - source.height) // 2
    canvas.paste(source, (x, y))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, HEIGHT - 130, WIDTH, HEIGHT), fill=(5, 12, 18, 245))
    draw.text((42, HEIGHT - 116), f"ONTO DEMO  |  PASO {index}/{len(items)}", font=font_bold, fill=(104, 210, 190, 255))
    lines = textwrap.wrap(caption, width=88)
    draw.multiline_text((42, HEIGHT - 76), "\n".join(lines), font=font, fill=(245, 247, 250, 255), spacing=4)
    canvas.save(PREPARED / f"{index:02d}.png")

concat = ROOT / "concat.txt"
with concat.open("w", encoding="utf-8") as handle:
    for index in range(1, len(items) + 1):
        handle.write(f"file '{(PREPARED / f'{index:02d}.png').as_posix()}'\n")
        handle.write(f"duration {DURATION}\n")
    handle.write(f"file '{(PREPARED / f'{len(items):02d}.png').as_posix()}'\n")

srt = ROOT / "demo_onto.srt"
with srt.open("w", encoding="utf-8") as handle:
    for index, (_, caption) in enumerate(items):
        start = index * DURATION
        end = start + DURATION
        handle.write(f"{index + 1}\n")
        handle.write(f"00:{start // 60:02d}:{start % 60:02d},000 --> 00:{end // 60:02d}:{end % 60:02d},000\n")
        handle.write(f"{caption}\n\n")

output = ROOT / "demo_onto_flujo_completo_pantalla.mp4"
ffmpeg = get_ffmpeg_exe()
subprocess.run(
    [
        ffmpeg,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat),
        "-vf", "fps=30,format=yuv420p",
        "-c:v", "libx264",
        "-crf", "20",
        "-preset", "medium",
        "-movflags", "+faststart",
        str(output),
    ],
    check=True,
)
print(output)
print(srt)
