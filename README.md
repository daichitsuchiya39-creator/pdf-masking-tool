# PDFマスキングツール

同一レイアウトのPDF(例: 帳票を複数人分出力したもの)を一括で黒塗りマスキングするためのツール群。

## 構成ファイル

| ファイル | 役割 |
|---|---|
| `main.py` | `input/*.pdf` を読み込み、`mask_coords.json` で指定した矩形を黒塗りして `output/*_masked.pdf` に出力する本体スクリプト |
| `mask_picker.py` | GUI(Tkinter)でPDFページ上をマウスドラッグし、黒塗りしたい矩形の座標(pt単位)を採寸するツール。結果は `mask_coords.json` に保存される |
| `calibrate.py` | GUIが使えない環境向けのフォールバック。ページ画像にpt単位の座標グリッドを重ねた画像を `calibration/` に出力し、目視で座標を読み取れるようにする |
| `mask_coords.json` | `mask_picker.py` の採寸結果(ラベル名と矩形座標の数値のみ。個人情報の値は含まない)。`main.py` はこのファイルを毎回読み込んで使う |

## パッケージ版(Python不要)

一般ユーザー向けに、Python環境なしでダブルクリックだけで使える実行ファイルを配布できる。

- Windows: `PDFMaskingTool.exe` / `MaskPicker.exe`(GitHub Actionsが`main.py`/`mask_picker.py`へのpushのたびに自動ビルドし、Actionsタブのartifactからダウンロード可能)
- macOS: `PDFMaskingTool.app` / `MaskPicker.app`(`pyinstaller --windowed --name <名前> <script>.py` でこのMac上でビルド)

使い方は同じで、`MaskPicker`と`PDFMaskingTool`を同じフォルダに置き、その中に`input/`を作ってPDFを入れる。実行ファイルの置き場所を基準に`input/`・`output/`・`mask_coords.json`を解決するため、作業ディレクトリに依存しない。

## 座標系についての注意(重要)

`main.py` はページを `page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))` で `ZOOM`倍(既定2倍)の解像度にラスタライズしてから矩形を黒塗りしている。

- `MASKS` の座標値は **PDFのポイント単位(pt)**、原点は左上、`page.rect` と同じ座標系。
- 実際に `PIL.ImageDraw` で矩形を描く画像は `ZOOM` 倍のピクセルサイズなので、描画直前に必ず `ZOOM` 倍してから使うこと(`main.py` 内の `scaled_rect = tuple(c * ZOOM for c in rect)`)。
- ここのスケール変換を忘れると、黒塗り位置が本来の位置の半分(左上寄り)にズレる、という不具合が過去に発生した。`ZOOM` を変更する場合はこの掛け算部分と整合させる。

## 座標の決め方(新しいレイアウトのPDFを扱うとき)

個人情報の値そのものをAIに見せずに座標を決めるため、以下の運用にしている。

1. `input/` に対象PDFを置く。
2. `python mask_picker.py` を実行する(処理はすべてローカルのGUIウィンドウ内で完結し、外部には送信されない)。
   - 青い破線: `main.py` の現在の `MASKS`(参考表示、保存対象外)
   - 左ドラッグで新しい黒塗り候補の矩形(赤)を描く → ラベル名(例: 「住所」など、項目名であり個人情報の値ではない)を入力
   - 右クリックで矩形削除、「元に戻す」で直前の1件取り消し
   - 「次のページ」「前のページ」でページ送り
   - 「保存して終了」で `mask_coords.json` に書き出す
3. `python main.py` を実行する。`main.py` は起動のたびに `mask_coords.json` を読み込むため、追加の操作なしにそのまま新しい座標が反映される。`output/` の結果を目視確認する。

`mask_coords.json` が無い/壊れている場合は、`main.py` 内の `DEFAULT_MASKS`(フォールバック用の初期値)が使われる。

GUIが使えない環境では、代わりに `python calibrate.py` で `calibration/` にグリッド付き画像を出力し、目視でpt座標を読み取って `mask_coords.json` を手動編集する(採寸精度は落ちるが同じ考え方)。

## 一括マスキングの前提

`main.py` は `input/` 内の**すべての**PDFに対して同一のマスク(`mask_coords.json` に保存されている、最後に採寸したファイルの座標)を適用する(「同一レイアウトのPDFを一括処理する」という設計)。そのため:

- 同じ帳票フォーマットで対象者だけが異なる複数PDFを一気に処理するのに向いている。
- レイアウトが異なるPDF(別の帳票種類など)を混在させると座標がズレるため、フォーマットごとに `mask_picker.py` で座標を採寸し直し、`mask_coords.json` を作り直す必要がある。

## 実行方法

```
python main.py
```

`input/*.pdf` を読み込み、`output/*_masked.pdf` として黒塗り済みPDFを出力する。
