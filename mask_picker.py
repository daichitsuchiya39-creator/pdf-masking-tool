"""
GUIでPDF上に矩形をマウス描画し、黒塗り座標(pt単位)を取得するツール。

使い方:
    python mask_picker.py

操作:
    - 左ドラッグ: 新しい矩形を描く(離すとラベル名を聞かれます)
    - 右クリック: クリックした位置の矩形を削除
    - 「元に戻す」ボタン: このページの最後の矩形を削除
    - 「前のページ」「次のページ」: ページ切り替え(自動保存される)
    - 「保存して終了」: mask_coords.json に書き出して終了

青い破線は main.py の現在の MASKS(参考表示・保存対象外)。
赤い矩形が新しく描いたもので、保存対象です。
"""

from pathlib import Path
import io
import json
import tkinter as tk
from tkinter import simpledialog, messagebox

import fitz
from PIL import Image, ImageTk

INPUT_DIR = Path("input")
OUTPUT_JSON = Path("mask_coords.json")
ZOOM = 2  # main.pyと合わせる

try:
    from main import MASKS as REFERENCE_MASKS
except Exception:
    REFERENCE_MASKS = {}


class MaskPicker:
    def __init__(self, root):
        self.root = root
        self.root.title("マスク座標ピッカー")

        self.files = sorted(INPUT_DIR.glob("*.pdf"))
        if not self.files:
            messagebox.showerror("エラー", f"{INPUT_DIR} にPDFが見つかりません")
            root.destroy()
            return

        self.file_index = 0
        self.page_index = 0
        self.doc = None

        # {(file_stem, page_no): [{"label": str, "rect": (x0,y0,x1,y1)}]}
        self.results = {}
        if OUTPUT_JSON.exists():
            try:
                raw = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
                for stem, pages in raw.items():
                    for page_no, items in pages.items():
                        self.results[(stem, int(page_no))] = items
            except Exception:
                pass

        self.canvas = tk.Canvas(root, cursor="cross", bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        bar = tk.Frame(root)
        bar.pack(fill=tk.X)
        tk.Button(bar, text="前のページ", command=self.prev_page).pack(side=tk.LEFT)
        tk.Button(bar, text="次のページ", command=self.next_page).pack(side=tk.LEFT)
        tk.Button(bar, text="元に戻す", command=self.undo).pack(side=tk.LEFT)
        tk.Button(bar, text="保存して終了", command=self.save_and_exit).pack(side=tk.RIGHT)
        self.status = tk.Label(bar, text="")
        self.status.pack(side=tk.LEFT, padx=10)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<ButtonPress-3>", self.on_right_click)

        self.start_xy = None
        self.temp_rect_id = None
        self.display_scale = 1.0
        self.tk_img = None

        self.load_page()

    # ---- データアクセス ----

    def current_stem(self):
        return self.files[self.file_index].stem

    def current_key(self):
        return (self.current_stem(), self.page_index)

    def current_rects(self):
        return self.results.setdefault(self.current_key(), [])

    # ---- 描画 ----

    def load_page(self):
        pdf_path = self.files[self.file_index]
        self.doc = fitz.open(pdf_path)
        if self.page_index >= len(self.doc):
            self.page_index = 0

        page = self.doc[self.page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        screen_w = self.root.winfo_screenwidth() * 0.85
        screen_h = self.root.winfo_screenheight() * 0.8
        self.display_scale = min(1.0, screen_w / img.width, screen_h / img.height)
        disp_w = round(img.width * self.display_scale)
        disp_h = round(img.height * self.display_scale)
        img = img.resize((disp_w, disp_h))

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.config(width=disp_w, height=disp_h)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

        # 参考: main.py の現在のMASKS(青い破線、保存対象外)
        for rect in REFERENCE_MASKS.get(self.page_index, []):
            x0, y0, x1, y1 = [c * self.pt_to_canvas() for c in rect]
            self.canvas.create_rectangle(x0, y0, x1, y1, outline="blue", dash=(4, 2), width=1)

        # 保存済みの新しい矩形(赤)
        for item in self.current_rects():
            self.draw_saved_rect(item)

        self.status.config(
            text=f"{pdf_path.name}  ページ {self.page_index + 1}/{len(self.doc)}"
        )

    def pt_to_canvas(self):
        return ZOOM * self.display_scale

    def canvas_to_pt(self, x, y):
        s = self.pt_to_canvas()
        return x / s, y / s

    def draw_saved_rect(self, item):
        x0, y0, x1, y1 = [c * self.pt_to_canvas() for c in item["rect"]]
        rid = self.canvas.create_rectangle(x0, y0, x1, y1, outline="red", width=2)
        tid = self.canvas.create_text(x0 + 3, y0 + 3, anchor=tk.NW, fill="red", text=item["label"])
        item["_canvas_ids"] = (rid, tid)

    # ---- マウス操作 ----

    def on_press(self, event):
        self.start_xy = (event.x, event.y)
        self.temp_rect_id = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="red", width=2
        )

    def on_drag(self, event):
        if self.temp_rect_id is None:
            return
        x0, y0 = self.start_xy
        self.canvas.coords(self.temp_rect_id, x0, y0, event.x, event.y)

    def on_release(self, event):
        if self.temp_rect_id is None:
            return
        x0, y0 = self.start_xy
        x1, y1 = event.x, event.y
        self.canvas.delete(self.temp_rect_id)
        self.temp_rect_id = None

        if abs(x1 - x0) < 3 or abs(y1 - y0) < 3:
            return  # 小さすぎるドラッグは無視

        cx0, cx1 = sorted((x0, x1))
        cy0, cy1 = sorted((y0, y1))
        pt0 = self.canvas_to_pt(cx0, cy0)
        pt1 = self.canvas_to_pt(cx1, cy1)

        label = simpledialog.askstring("ラベル", "この矩形の名前(例: 住所)", parent=self.root)
        if label is None:
            return

        item = {
            "label": label,
            "rect": (round(pt0[0]), round(pt0[1]), round(pt1[0]), round(pt1[1])),
        }
        self.current_rects().append(item)
        self.draw_saved_rect(item)

    def on_right_click(self, event):
        rects = self.current_rects()
        s = self.pt_to_canvas()
        for item in reversed(rects):
            x0, y0, x1, y1 = [c * s for c in item["rect"]]
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                rid, tid = item.get("_canvas_ids", (None, None))
                if rid:
                    self.canvas.delete(rid)
                if tid:
                    self.canvas.delete(tid)
                rects.remove(item)
                break

    # ---- ナビゲーション ----

    def undo(self):
        rects = self.current_rects()
        if not rects:
            return
        item = rects.pop()
        rid, tid = item.get("_canvas_ids", (None, None))
        if rid:
            self.canvas.delete(rid)
        if tid:
            self.canvas.delete(tid)

    def next_page(self):
        if self.page_index < len(self.doc) - 1:
            self.page_index += 1
        elif self.file_index < len(self.files) - 1:
            self.file_index += 1
            self.page_index = 0
        else:
            return
        self.load_page()

    def prev_page(self):
        if self.page_index > 0:
            self.page_index -= 1
        elif self.file_index > 0:
            self.file_index -= 1
            self.doc = fitz.open(self.files[self.file_index])
            self.page_index = len(self.doc) - 1
        else:
            return
        self.load_page()

    def save_and_exit(self):
        out = {}
        for (stem, page_no), items in self.results.items():
            if not items:
                continue
            clean_items = [{"label": it["label"], "rect": list(it["rect"])} for it in items]
            out.setdefault(stem, {})[str(page_no)] = clean_items

        OUTPUT_JSON.write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        messagebox.showinfo("保存完了", f"{OUTPUT_JSON} に保存しました")
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MaskPicker(root)
    root.mainloop()
