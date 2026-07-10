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

## 使い方マニュアル(一般ユーザー向け)

Pythonの知識がなくても、以下の手順だけで使える。

### 初回セットアップ(レイアウトごとに1回)

1. `MaskPicker`(macOSは`MaskPicker.app`、Windowsは`MaskPicker.exe`)と`PDFMaskingTool`(同様に`.app`/`.exe`)を同じフォルダに置く。
2. そのフォルダの中に`input`という名前のフォルダを作り、黒塗りしたいPDF(同じ帳票フォーマットのもの)を入れる。
3. `MaskPicker`をダブルクリックして起動する。
   - PDFの1ページ目が表示される。
   - 黒塗りしたい範囲をマウスで左ドラッグ → 表示される名前入力欄に項目名(例:「住所」など、値そのものではなく項目名)を入力。
   - 間違えたら、その矩形を右クリックで削除、または「元に戻す」ボタンで直前の1件を取り消せる。
   - 「次のページ」「前のページ」で他のページも同様に範囲を指定する(複数ファイルがある場合は自動的に次のファイルへ進む)。
   - 全ページ終わったら「保存して終了」を押す。同じフォルダに`mask_coords.json`が作成/更新される。
4. `PDFMaskingTool`をダブルクリックして起動する。
   - 完了すると「◯件のPDFを処理しました」というダイアログが出て、同じフォルダの`output`フォルダに黒塗り済みPDFが出力される。
   - `input`にPDFが無い場合や処理中にエラーが起きた場合も、必ずダイアログでその旨が表示される(画面が何も出ないまま終わることはない)。

### 通常運用(2回目以降・同じレイアウトのPDFを処理するだけの場合)

`mask_coords.json`はそのまま使い回せるので、`MaskPicker`での再設定は不要。

1. `input`フォルダの中身を新しいPDFに入れ替える。
2. `PDFMaskingTool`をダブルクリックする。
3. `output`フォルダに黒塗り済みPDFが出力される。

### マスク範囲を修正したいとき

`MaskPicker`をもう一度ダブルクリックすると、直前に保存した矩形(赤)が復元された状態で編集を再開できる。修正して「保存して終了」すれば`mask_coords.json`が上書きされ、次回`PDFMaskingTool`を実行したときから新しい範囲が使われる。

### 初回起動時の注意(macOS/Windows共通)

署名(Apple Developer証明書 / コード署名証明書)を行っていないアプリのため、初回起動時にOSが警告を出すことがある。

- **macOS**: 「開発元を確認できないため開けません」→ Finderで`.app`を**右クリック→「開く」**を選び、確認ダイアログで「開く」を押す。
- **Windows**: 「WindowsによってPCが保護されました」(SmartScreen)→「詳細情報」をクリックし、「実行」を押す。

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

## 実行方法(開発者向け・Pythonから直接実行する場合)

```
python main.py
```

`input/*.pdf` を読み込み、`output/*_masked.pdf` として黒塗り済みPDFを出力する。

## 動作確認状況

| 項目 | 状態 | 確認日 |
|---|---|---|
| macOS (`PDFMaskingTool.app` / `MaskPicker.app`) | ユーザーが実機で動作確認済み | 2026-07-11 |
| Windows (`PDFMaskingTool.exe` / `MaskPicker.exe`) | GitHub Actions上のビルドは成功しているが、**実機での動作確認は未実施** | - |

Windows実機での確認ができ次第、この表を更新すること。

## 作業ログ

| 日付 | 内容 |
|---|---|
| 2026-07-10 | GitHubリポジトリをclone。Windows用`.exe`パッケージング要望を受け、macOSではWindows向けにクロスコンパイルできないためGitHub Actions(windows-latest)上で`pyinstaller --onefile --noconsole`によるビルドを自動化する方針にした。`--noconsole`にすると処理結果が一切見えなくなるため、`main.py`に完了/エラー/PDFなしのtkinterダイアログを追加。 |
| 2026-07-11 | ビルドした`.exe`をユーザーがMac上でダブルクリックし「データが壊れています」と表示される件に対応 → 実際はWindows用バイナリをmacOSで実行しようとしたことによるGatekeeperの誤解を招く表示と判明(ファイル自体は正常)。 |
| 2026-07-11 | macOS用に`PDFMaskingTool.app`をこのMac上でビルド。ダブルクリックしても起動しない不具合が発生し調査。原因は2点: (1) PyInstallerの`--windowed`ビルドでは`sys.stdout`/`sys.stderr`が`None`になり、`print()`や内部警告出力が`AttributeError`となってダイアログ表示前に無言で落ちていた。(2) ダブルクリック起動時は作業ディレクトリがアプリの置き場所と一致しない(特にmacOSの`.app`は`/`になりがち)ため`input`/`output`を見つけられなかった。両方修正し、実PDFで一括処理が最後まで通ることを確認。 |
| 2026-07-11 | マスキング範囲が想定と異なるという報告を受け調査 → `main.py`が`mask_picker.py`の採寸結果(`mask_coords.json`)を全く読み込まず、常にソースコード直書きの固定`MASKS`を使っていたことが判明(旧README記載の「座標を共有してもらい手動でmain.pyを書き換える」という運用のまま、自動連携する設計になっていなかった)。`main.py`が起動時に`mask_coords.json`を読み込み、`input/`内の全PDFに適用するよう修正。全面塗りつぶしのテスト用JSONとピクセルサンプリングで動作を検証。 |
| 2026-07-11 | `mask_picker.py`にも同じ安定性対策(stdout/stderr対策、実行ファイル位置からのパス解決、debug.logへのエラー記録)を適用し、`MaskPicker.app`/`MaskPicker.exe`としてパッケージ化。GitHub Actionsのワークフローを両方の実行ファイルをビルドするよう更新。README/CLAUDE.mdを整備。 |
| 2026-07-11 | ユーザーがmacOS実機で`MaskPicker`→`PDFMaskingTool`の一連の流れを確認し、問題なし。Windows実機での確認はまだ。 |
