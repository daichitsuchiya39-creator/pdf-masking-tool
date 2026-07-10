from pathlib import Path
import fitz
from PIL import Image, ImageDraw
import io
import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox

# --windowed/--noconsoleビルドではsys.stdout/stderrがNoneになり、
# print()やライブラリ内部の警告出力がAttributeErrorで落ちる原因になるため、
# 起動直後に必ずダミーの書き込み先を用意しておく。
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# ダブルクリック起動時、作業ディレクトリはexe/.appの置き場所と一致しない
# (macOSの.appは特に"/"などになる)。ユーザーが実行ファイルと同じ場所に
# input/を置く運用を想定しているため、実行ファイルの実際の位置から
# input/output フォルダを解決する。
if getattr(sys, "frozen", False):
    exe_path = Path(sys.executable).resolve()
    if sys.platform == "darwin" and exe_path.parent.name == "MacOS":
        # .../PDFMaskingTool.app/Contents/MacOS/PDFMaskingTool -> .appの置き場所
        BASE_DIR = exe_path.parents[3]
    else:
        BASE_DIR = exe_path.parent
else:
    BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

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
    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    processed = []

    for pdf_file in pdf_files:

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
        processed.append(output_pdf)

        print(f"完了: {output_pdf}")

    return processed


if __name__ == "__main__":
    # ダブルクリック起動時は黒い画面が一切出ないため(--noconsoleビルド)、
    # 処理結果をダイアログで必ず通知する。tk.Tk()自体の初期化失敗も含めて
    # ここで捕まえ、DEBUG_LOGにも記録しておく(ユーザーからの問い合わせ時用)。
    DEBUG_LOG = BASE_DIR / "debug.log"

    try:
        root = tk.Tk()
        root.withdraw()

        if not INPUT_DIR.exists() or not any(INPUT_DIR.glob("*.pdf")):
            messagebox.showwarning(
                "PDFが見つかりません",
                f"{INPUT_DIR.resolve()} にPDFファイルが見つかりませんでした。\n"
                "このツールと同じ場所に input フォルダを作り、PDFを入れてから再実行してください。",
            )
            sys.exit(1)

        try:
            processed = main()
        except Exception:
            messagebox.showerror(
                "エラーが発生しました",
                "マスキング処理中にエラーが発生しました。\n\n" + traceback.format_exc(),
            )
            sys.exit(1)

        if processed:
            names = "\n".join(p.name for p in processed)
            messagebox.showinfo(
                "完了",
                f"{len(processed)} 件のPDFを処理しました。\n"
                f"出力先: {OUTPUT_DIR.resolve()}\n\n{names}",
            )
        else:
            messagebox.showwarning(
                "処理対象なし",
                f"{INPUT_DIR.resolve()} にPDFファイルが見つかりませんでした。",
            )
    except SystemExit:
        raise
    except Exception:
        DEBUG_LOG.write_text(traceback.format_exc(), encoding="utf-8")
        raise