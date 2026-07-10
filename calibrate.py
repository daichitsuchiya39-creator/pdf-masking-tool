from pathlib import Path
import fitz
from PIL import Image, ImageDraw, ImageFont
import io

INPUT_DIR = Path("input")
CALIBRATION_DIR = Path("calibration")

CALIBRATION_DIR.mkdir(exist_ok=True)

ZOOM = 2  # main.pyと合わせる
MINOR_STEP = 50   # 細いグリッド線の間隔(pt)
MAJOR_STEP = 100  # 太いグリッド線+ラベルの間隔(pt)

try:
    FONT = ImageFont.truetype("arial.ttf", 16)
except OSError:
    FONT = ImageFont.load_default()


def draw_grid(img: Image.Image) -> Image.Image:
    """imgは pt座標 * ZOOM のピクセルサイズを持つ前提。pt単位のグリッドを重ねて描画する。"""
    img = img.convert("RGBA")
    w_pt = img.width / ZOOM
    h_pt = img.height / ZOOM

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    x = 0
    while x <= w_pt:
        px = round(x * ZOOM)
        is_major = x % MAJOR_STEP == 0
        color = (255, 0, 0, 160) if is_major else (255, 0, 0, 70)
        odraw.line([(px, 0), (px, img.height)], fill=color, width=2 if is_major else 1)
        x += MINOR_STEP

    y = 0
    while y <= h_pt:
        py = round(y * ZOOM)
        is_major = y % MAJOR_STEP == 0
        color = (255, 0, 0, 160) if is_major else (255, 0, 0, 70)
        odraw.line([(0, py), (img.width, py)], fill=color, width=2 if is_major else 1)
        y += MINOR_STEP

    composited = Image.alpha_composite(img, overlay).convert("RGB")

    tdraw = ImageDraw.Draw(composited)
    x = 0
    while x <= w_pt:
        px = round(x * ZOOM)
        tdraw.text((px + 2, 2), str(int(x)), fill=(0, 0, 255), font=FONT)
        x += MAJOR_STEP

    y = 0
    while y <= h_pt:
        py = round(y * ZOOM)
        tdraw.text((2, py + 2), str(int(y)), fill=(0, 0, 255), font=FONT)
        y += MAJOR_STEP

    return composited


for pdf_file in INPUT_DIR.glob("*.pdf"):

    doc = fitz.open(pdf_file)

    for page_no in range(len(doc)):
        page = doc[page_no]

        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        grid_img = draw_grid(img)

        out_path = CALIBRATION_DIR / f"{pdf_file.stem}_p{page_no}_grid.png"
        grid_img.save(out_path)
        print(f"出力: {out_path} (ページサイズ: {page.rect.width:.0f} x {page.rect.height:.0f} pt)")

print("\n生成された画像をご自身のビューアで開き、赤いグリッド線(青字がpt座標)を目安に、")
print("黒塗りしたい範囲の (x0, y0, x1, y1) を pt単位で読み取ってください。")
print("読み取った数値を教えていただければ main.py の MASKS を更新します。")
