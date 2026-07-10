from pathlib import Path
import fitz
from PIL import Image, ImageDraw
import io

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")

OUTPUT_DIR.mkdir(exist_ok=True)

ZOOM = 2  # get_pixmapの拡大率。MASKSはPDFポイント単位のため描画時にこの倍率を掛ける

# A4横・同様レイアウト前提
# mask_picker.py で GUI 上から採寸した座標(pt単位)
MASKS = {
    0: [  # 1ページ目
        (71, 74, 109, 85),      # 職員番号
        (318, 73, 453, 92),     # 住所
        (204, 93, 304, 112),    # 生年月日
        (37, 141, 786, 480),    # 任免事項
    ],
    1: [  # 2ページ目
        (47, 39, 82, 49),       # 職員番号
        (104, 77, 728, 558),    # 手当
    ],
    2: [  # 3ページ目
        (85, 76, 695, 557),     # 社会保険等
    ]
}

def main():
    for pdf_file in INPUT_DIR.glob("*.pdf"):

        doc = fitz.open(pdf_file)
        out_doc = fitz.open()

        for page_no in range(len(doc)):

            page = doc[page_no]

            pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
            img = Image.open(io.BytesIO(pix.tobytes("png")))

            draw = ImageDraw.Draw(img)

            if page_no in MASKS:
                for rect in MASKS[page_no]:
                    scaled_rect = tuple(c * ZOOM for c in rect)
                    draw.rectangle(scaled_rect, fill="black")

            buf = io.BytesIO()
            img.save(buf, format="PNG")

            new_page = out_doc.new_page(
                width=page.rect.width,
                height=page.rect.height
            )

            new_page.insert_image(
                new_page.rect,
                stream=buf.getvalue()
            )

        output_pdf = OUTPUT_DIR / f"{pdf_file.stem}_masked.pdf"

        out_doc.save(output_pdf)

        print(f"完了: {output_pdf}")


if __name__ == "__main__":
    main()