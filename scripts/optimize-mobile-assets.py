import base64
import io
import re
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = ROOT / "index.html"
OUTPUT_DIRECTORY = ROOT / "assets" / "images"

IMAGES = [
    {"file": "henrique-figurinha.webp", "width": 900, "quality": 82, "alt": "Figurinha do Henrique", "priority": True},
    {"file": "album-primeiros-treinos.webp", "width": 800, "quality": 78, "alt": "Henrique em seus primeiros treinos"},
    {"file": "album-pronto-para-entrar-em-campo.webp", "width": 800, "quality": 78, "alt": "Henrique pronto para entrar em campo"},
    {"file": "album-velocidade-e-alegria.webp", "width": 800, "quality": 78, "alt": "Henrique demonstrando velocidade e alegria"},
    {"file": "album-explorando-novos-campos.webp", "width": 800, "quality": 78, "alt": "Henrique explorando novos campos"},
    {"file": "album-todo-sorriso-merece-torcida.webp", "width": 800, "quality": 78, "alt": "Henrique sorrindo em frente à fonte"},
    {"file": "album-time-completo.webp", "width": 800, "quality": 78, "alt": "Henrique com sua família"},
    {"file": "brasao-cbf.webp", "width": 240, "quality": 88, "alt": "Brasão da CBF"},
    {"file": "qr-code-presenca.png", "png": True, "alt": "QR Code de presença"},
]

IMAGE_PATTERN = re.compile(
    r'<img\b[^>]*?src="data:image/(?P<type>[^;]+);base64,(?P<data>[^"]+)"[^>]*>',
    re.IGNORECASE,
)


def add_attribute(tag: str, name: str, value: str) -> str:
    pattern = re.compile(rf"\s{re.escape(name)}=(?:\"[^\"]*\"|'[^']*')", re.IGNORECASE)
    replacement = f' {name}="{value}"'
    if pattern.search(tag):
        return pattern.sub(replacement, tag, count=1)
    return tag[:-1] + replacement + ">"


def optimize_image(source: bytes, config: dict) -> tuple[int, int]:
    destination = OUTPUT_DIRECTORY / config["file"]
    if config.get("png"):
        destination.write_bytes(source)
        with Image.open(io.BytesIO(source)) as image:
            return image.size

    with Image.open(io.BytesIO(source)) as original:
        image = ImageOps.exif_transpose(original)
        if image.width > config["width"]:
            ratio = config["width"] / image.width
            image = image.resize(
                (config["width"], max(1, round(image.height * ratio))),
                Image.Resampling.LANCZOS,
            )
        image.save(
            destination,
            format="WEBP",
            quality=config["quality"],
            method=6,
        )
        return image.size


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    html = HTML_PATH.read_text(encoding="utf-8")
    embedded = list(IMAGE_PATTERN.finditer(html))
    if not embedded:
        print("O HTML já não possui imagens incorporadas.")
        return
    if len(embedded) != len(IMAGES):
        raise RuntimeError(f"Esperadas {len(IMAGES)} imagens incorporadas, encontradas {len(embedded)}.")

    replacements = []
    for match, config in zip(embedded, IMAGES):
        source = base64.b64decode(match.group("data"))
        width, height = optimize_image(source, config)
        tag = re.sub(
            r'src="data:image/[^;]+;base64,[^"]+"',
            f'src="assets/images/{config["file"]}"',
            match.group(0),
            count=1,
            flags=re.IGNORECASE,
        )
        tag = add_attribute(tag, "alt", config["alt"])
        tag = add_attribute(tag, "width", str(width))
        tag = add_attribute(tag, "height", str(height))
        tag = add_attribute(tag, "decoding", "async")
        if config.get("priority"):
            tag = add_attribute(tag, "fetchpriority", "high")
        else:
            tag = add_attribute(tag, "loading", "lazy")
        replacements.append((match.start(), match.end(), tag))

    for start, end, tag in reversed(replacements):
        html = html[:start] + tag + html[end:]

    preload = '<link rel="preload" as="image" href="assets/images/henrique-figurinha.webp" type="image/webp" fetchpriority="high">'
    if preload not in html:
        description = '<meta name="description" content="Convocação oficial para o aniversário de 2 anos do Henrique.">'
        html = html.replace(description, description + "\n" + preload, 1)

    HTML_PATH.write_text(html, encoding="utf-8", newline="\n")
    print(f"Extraídas e otimizadas {len(IMAGES)} imagens.")


if __name__ == "__main__":
    main()
