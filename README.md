# ChatGPT Split Turn Shade v1.1.0

Chrome標準の **Split View（左右に並べたChatGPTの2画面）** 用拡張です。
最後にメッセージを送信したChatGPT側だけをグレーにし、反対側のグレーは解除します。

| イベント | 左 | 右 |
|---|---|---|
| 起動直後 | 通常 | 通常 |
| 左で送信 | グレー | 通常 |
| 右で送信 | 通常 | グレー |
| 左で再送信 | グレー | 通常 |

グレー表示はクリックを遮りません。灰色画面でもスクロール、コピー、クリック可能です。

## 正式リリースパッケージと自動バージョン管理

最新版は [GitHub Releases](https://github.com/yohi/turnshade/releases/latest) の **Assets** にある `turnshade-vX.Y.Z.zip` をダウンロードしてください。GitHubが自動生成する **Source code (zip)** は拡張本体の配布物ではありません。

- CIの実行環境は `ubuntu-slim`。PushとPull RequestでJavaScript構文と単体テストを検証し、拡張ファイルのみZIP化します。
- Google製の [release-please](https://github.com/googleapis/release-please) が、`master` 上の **Conventional Commits** から次のバージョンを判定し、**Release PR** を作成します。
- 例: `fix: repair shade detection` はpatch (`1.1.0 → 1.1.1`)、`feat: add a shortcut` はminor (`1.1.0 → 1.2.0`)、`feat!: change supported layouts` はmajor (`1.1.0 → 2.0.0`)。
- Release PRには `CHANGELOG.md`、`version.txt`、`.release-please-manifest.json`、`manifest.json` のバージョン更新が含まれます。**普段は手動でバージョンを上げないでください。**
- Release PRを`master`にマージすると、release-pleaseが`vX.Y.Z`タグとGitHub Releaseを生成し、CIでテスト・作成した `turnshade-vX.Y.Z.zip` と `.sha256` をそのReleaseに添付します。
- 既存の `v1.1.0` は起点として維持し、今回のCI移行だけで別バージョンは発行しません。

**運用上の注意:** `GITHUB_TOKEN` がRelease PRを作成できない場合は、GitHubリポジトリの **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests** を有効にしてください。また、`GITHUB_TOKEN` が作成したPRは後続の通常のCIトリガーを発火させないため、リリースPRは内容を確認してからマージしてください。

## インストール・更新方法

1. Chromeのアドレスバーに `chrome://extensions` を入力。
2. 旧版 `ChatGPT Split Turn Shade` v1.0.0 があれば**削除**（またはOFFにする）。
3. ZIPを解凍する。
4. **デベロッパー モード** をON → **パッケージ化されていない拡張機能を読み込む** → 解凍した拡張フォルダー（直下に `manifest.json` がある場所）を選択。
5. Split Viewの**左右両方のChatGPTを再読み込み**する。これは必須です。
6. ChatGPT側で1通送信して確認。

## 反応しない場合の検査手順（30秒）

1. ChatGPTを表示した側を選択し、ツールバーの拡張アイコン（ピン固定推奨）をクリック。
2. ポップアップの **「ペア」** が `認識済み (Chrome標準Split View)` か確認。
   - `未認識` の場合、これはChrome標準Split Viewではない可能性があります。`Chrome Split ID` が `-1` や `なし` である場合、任意の「通常タブ2枚でも連携する」をONにしてみてください。これは**同じChromeウィンドウ内のChatGPTタブがちょうど2枚**の場合のみ使えます。
   - 左右を別ウィンドウにしたものは対象外です。
3. **「拡張のページ監視」** が `読み込み済み` でなければ、左右のChatGPTを再読み込み。
4. **「この画面をグレーにする」** を押す。
   - グレーになればSplit/メッセージ連携の設定は成功。通常の送信でも反応しない場合は、`直近の検出` と `反映結果` を確認してください。
   - グレーにならなければ `ペア` と `ページ監視` を再度確認してください。
5. 状態情報のスクリーンショットを共有してもらえれば、どの段階の失敗か特定できます（会話本文は含みません）。

## 実装とセキュリティ

- Manifest V3 / Chrome 140以降。
- Chrome標準Split Viewでは `tabs.Tab.splitViewId` により同じ分割ペアだけを更新。
- 標準分割が未認識の時の「通常タブ2枚モード」は明示的なONのみ。
- DOM内で送信タイミングの判定に使う文字の特徴量を計算しますが、会話本文は拡張のバックグラウンドに送信・保存しません。
- 保存内容：Split ViewのペアID、タブID、最後の送信タブ、最終更新時刻、フォールバック設定のみ。
- 外部サーバー接続なし。`tabs` 全体の閲覧権限も要求しません（ChatGPTドメインのみホスト権限）。
- 誤検知防止のため、会話を開いた直後の一定時間は送信操作のないDOM変化での自動反転を抑止。

## 制限事項

ChatGPTのWeb画面は安定したDOMインターフェースを保証していないため、UI変更や外部自動化の実装方式によっては検出が失敗する可能性があります。
Chrome標準Split Viewではない画面分割アプリや、**別ウィンドウ**同士の自動ペア判定はサポートしていません。

## テスト

```sh
node --test tests/service-worker.test.cjs
python tests/content-browser-check.py
```

2026-10-15時点：バックグラウンドのモック単体テスト8件PASS、Chromium 144のブラウザDOM模擬テストPASS。実ChatGPTサイトへのログイン済みE2EテストおよびChrome標準Split View上の実機統合テストは未実施です。

参考：
- https://developer.chrome.com/docs/extensions/reference/api/tabs
- https://developer.chrome.com/blog/split-view-api-extensions
