# TurnShade

Chrome標準の **Split View** で、ChatGPT/Geminiの2画面の「次のターン」を分かりやすくする拡張です。最後に送信した側を **赤枠** で囲み、次に送信する方向を **矢印** で示します。反対側は通常表示のままで、赤枠側でもクリック・スクロール・コピーできます。

| ペア | 状態 |
|---|---|
| ChatGPT × ChatGPT | 既存対応 |
| ChatGPT × Gemini（左右逆も） | 新規追加（実サイト統合試験未実施） |
| Gemini × Gemini | 新規追加（実サイト統合試験未実施） |

メッセージ自体は自動転送しません。GeminiのWeb UIは非公開DOMであり、画面構造変更によって送信判定が動かなくなる可能性があります。

## 赤枠と矢印の表示

- **左側から送信**：左画面に赤枠と「次は右へ →」。右画面は通常表示。
- **右側から送信**：右画面に赤枠と「← 次は左へ」。左画面は通常表示。
- 赤枠はクリックを遮らない透過オーバーレイ上に描画し、画面全体の暗転はしません。
- Chromeの `tabs.Tab.index`（タブストリップ内の順序）から左右を**推定**します。ただしChrome拡張APIは表示ペインの物理的な左右を直接通知しないため、Chromeでペイン位置を入れ替えた場合などに逆になる可能性があります。その場合、拡張ポップアップの **「矢印の左右を反転する」** をONにしてください。この設定は全Split Viewペアに適用されます。
- タブ順が取得できない場合や「通常タブ2枚モード」では、誤った方向を表示しないため **「送信済み · 次は反対側」** と表示します。

## 正式リリースパッケージと自動バージョン管理

最新版は [GitHub Releases](https://github.com/yohi/turnshade/releases/latest) の **Assets** にある `turnshade-vX.Y.Z.zip` をダウンロードしてください。CRXが添付済みの場合は下記のLinux向け手動インストールも利用できます。GitHubが自動生成する **Source code (zip)** は拡張本体の配布物ではありません。

- CIの実行環境は `ubuntu-slim`。PushとPull RequestでJavaScript構文と単体テストを検証し、拡張ファイルのみZIP化します。
- Google製の [release-please](https://github.com/googleapis/release-please) が、`master` 上の **Conventional Commits** から次のバージョンを判定し、**Release PR** を作成します。
- 例: `fix: repair shade detection` はpatch (`1.1.0 → 1.1.1`)、`feat: add a shortcut` はminor (`1.1.0 → 1.2.0`)、`feat!: change supported layouts` はmajor (`1.1.0 → 2.0.0`)。
- Release PRには `CHANGELOG.md`、`version.txt`、`.release-please-manifest.json`、`manifest.json` のバージョン更新が含まれます。**普段は手動でバージョンを上げないでください。**
- Release PRを`master`にマージすると、release-pleaseが`vX.Y.Z`タグとGitHub Releaseを生成し、CIでテスト・作成した `turnshade-vX.Y.Z.zip` と `.sha256` をそのReleaseに添付します。
- 既存の `v1.1.0` は起点として維持し、今回のCI移行だけで別バージョンは発行しません。

**運用上の注意:** `GITHUB_TOKEN` がRelease PRを作成できない場合は、GitHubリポジトリの **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests** を有効にしてください。また、`GITHUB_TOKEN` が作成したPRは後続の通常のCIトリガーを発火させないため、リリースPRは内容を確認してからマージしてください。

## Linux向け署名済みCRX（Web Store公開なし・手動配布）

**この機能はCRX署名鍵の登録後に利用できます。** 現在のReleaseにCRXがあるとは限りません。従来のZIP配布は継続します。初期導入では自動更新は提供しません。

### Ownerによる一度きりの鍵準備

1. RSA秘密鍵を安全な管理環境で**一度だけ**生成し、復旧できる安全な保管先（例：暗号化されたパスワードマネージャー）へバックアップしてください。毎回生成すると拡張IDが変わり、上書き更新できません。
2. GitHubのリポジトリ **Settings → Secrets and variables → Actions** に、リポジトリSecret `TURNSHADE_CRX_PRIVATE_KEY_PEM` を登録してください（PEM全文）。**Secretの値やファイルをIssue・PR・ログ・リポジトリに掲載しないでください。**
3. 必要なら **Settings → Environments → crx-signing** で人間による環境承認を設定できます。

鍵ファイルをローカルに保管し続けたくない場合は、バックアップ先を用意したうえで、GitHub CLIの標準入力から秘密鍵を登録できます。秘密鍵を作る操作そのものはOwnerが実施し、ChatGPTやGitHub Actionsが勝手に発行しません。**バックアップなしでGitHub Secretだけに保存する運用は推奨しません**（Secretの値は後から読み出せません）。

### 既存ReleaseへのCRX添付

1. GitHub Actionsで **Sign CRX for published Release (manual)** を選択する。
2. **Run workflow** → ブランチ`master` → 既存の公開済みタグ（例：`v1.4.0`）を入力する。
3. ワークフローはRelease既存ZIPと`.sha256`を取得・照合し、ZIP内の拡張ファイルを許可リスト検証してから、秘密鍵でCRX3を生成します。
4. 成功時に、そのReleaseのAssetsへ `turnshade-vX.Y.Z.crx` と `.crx.sha256` を**追加**します。既存CRXは自動上書きしません。キーが未登録またはパッケージ検証に失敗した場合は公開しません。

PRのCIは**一時テスト鍵**でCRX3の生成だけを検証し、そのCRXは公開しません。本番署名は`master`からの手動実行とGitHub Secretが必要です。Release作成イベントに基づく自動CRX署名・更新配信は未実装です。

### Ubuntu / Google Chromeでの手動インストール

1. Release AssetsからCRXと`.crx.sha256`を取得し、同じディレクトリで`sha256sum -c turnshade-vX.Y.Z.crx.sha256`を実行する。
2. Chromeで`chrome://extensions`を開き、ダウンロードしたCRXを拡張機能画面へドラッグ＆ドロップして、**Chromeが許可する場合のみ**インストールを承認する。
3. Chromeの拡張一覧にTurnShadeがインストールされ、動作することを確認してから、ダウンロードしたCRXを削除する。Chrome内部にインストール済みのファイルは残りますが、別途展開したソースフォルダーは不要です。

**制約:** Linux版ChromeではWeb Store外の手動インストールが公式にサポートされますが、導入方法はChromeのバージョン・ポリシーにより制限されることがあります。ドラッグ＆ドロップで拒否された場合、セキュリティ制限を回避しないでください。Linuxの外部拡張設定（`external_crx`）はCRXファイルを所定の場所に保持する方式なので、「元ファイルを残さない」希望には合いません。別途、管理されたセルフホスト配布を設計する必要があります。Windows/macOSへのWeb Store外手動インストールを保証しません。

**注意:** 既存のパッケージ化されていないTurnShadeと、初めて署名したCRXでは拡張IDが異なる場合があります。インストール前に旧拡張をOFFにし、重複動作を避けてください。設定は拡張IDが変わると自動では引き継がれません。

参考：
- https://developer.chrome.com/docs/extensions/how-to/distribute
- https://developer.chrome.com/docs/extensions/how-to/distribute/host-on-linux
- https://developer.chrome.com/docs/extensions/mv3/external_extensions

## インストール・更新方法

1. Chromeのアドレスバーに `chrome://extensions` を入力。
2. 旧版 `ChatGPT Split Turn Shade` v1.0.0 があれば**削除**（またはOFFにする）。
3. ZIPを解凍する。
4. **デベロッパー モード** をON → **パッケージ化されていない拡張機能を読み込む** → 解凍した拡張フォルダー（直下に `manifest.json` がある場所）を選択。
5. Split Viewの**左右両方のチャット画面を再読み込み**する。これは必須です。
6. いずれかのチャット側で1通送信して確認。

## 反応しない場合の検査手順（30秒）

1. ChatGPTまたはGeminiを表示した側を選択し、ツールバーの拡張アイコン（ピン固定推奨）をクリック。
2. ポップアップの **「ペア」** が `認識済み (Chrome標準Split View)` か確認。
   - `未認識` の場合、これはChrome標準Split Viewではない可能性があります。`Chrome Split ID` が `-1` や `なし` である場合、任意の「通常タブ2枚でも連携する」をONにしてみてください。これは**同じChromeウィンドウ内のChatGPTタブがちょうど2枚**の場合のみ使えます。
   - 左右を別ウィンドウにしたものは対象外です。
3. **「拡張のページ監視」** が `読み込み済み` でなければ、左右のチャット画面を再読み込み。
4. **「この画面を赤枠にする」** を押す。
   - 赤枠になればSplit/メッセージ連携の設定は成功。通常の送信でも反応しない場合は、`直近の検出` と `反映結果` を確認してください。
   - 赤枠にならなければ `ペア` と `ページ監視` を再度確認してください。
5. 状態情報のスクリーンショットを共有してもらえれば、どの段階の失敗か特定できます（会話本文は含みません）。

## 実装とセキュリティ

- Manifest V3 / Chrome 140以降。
- Chrome標準Split Viewでは `tabs.Tab.splitViewId` により同じ分割ペアだけを更新。方向はタブの `index` を使って推定し、ポップアップから左右を反転可能。
- 標準分割が未認識の時の「通常タブ2枚モード」は明示的なONのみ。
- DOM内で送信タイミングの判定に使う文字の特徴量を計算しますが、会話本文は拡張のバックグラウンドに送信・保存しません。
- 保存内容：Split ViewのペアID、タブID、最後の送信タブ、最終更新時刻、タブ順から推定した方向、フォールバック設定、矢印反転設定のみ。
- 外部サーバー接続なし。`tabs` 全体の閲覧権限も要求しません（ChatGPT/Geminiドメインのみホスト権限）。
- 誤検知防止のため、会話を開いた直後の一定時間は送信操作のないDOM変化での自動反転を抑止。

## 制限事項

ChatGPT/GeminiのWeb画面は安定したDOMインターフェースを保証していないため、UI変更や外部自動化の実装方式によっては検出が失敗する可能性があります。
Chrome標準Split Viewではない画面分割アプリや、**別ウィンドウ**同士の自動ペア判定はサポートしていません。

## テスト

```sh
node --test tests/service-worker.test.cjs
python tests/content-browser-check.py
```

CIではService Workerの単体テストとJavaScript構文チェックを実行します。ChatGPT/GeminiのブラウザDOM模擬テストは個別実行用です（CI未統合）。ログイン済み実サイトでのE2EおよびChrome標準Split Viewの実機統合テストは未実施です。

参考：
- https://developer.chrome.com/docs/extensions/reference/api/tabs
- https://developer.chrome.com/blog/split-view-api-extensions

## Gemini対応の実装・検証範囲

- 対象URLは `https://chatgpt.com/*`、`https://chat.openai.com/*`、`https://gemini.google.com/*` のみです。Chrome Split ViewのペアIDが同一の2タブならプロバイダー混在も認識します。
- Geminiの送信判定は `user-query`、`rich-textarea .ql-editor`、`.send-button` などのDOM候補を使用します。Geminiの回答（`model-response`）をユーザー送信として数えないようにします。
- プライバシー：会話テキスト・Cookie・認証トークンを送信／保存しません。正規のホスト名とHTTPSだけを受け付けます。
- 自動テスト：`node --test tests/service-worker.test.cjs` （送信切替・矢印反転・タブ移動・ペア分離）、`python tests/content-browser-check.py` （ChatGPT合成DOM）、`python tests/gemini-browser-check.py` （Gemini合成DOM）。
- **未実施**：ログイン済みGemini実サイトでの送信判定、およびChrome標準Split Viewを使用した実機E2Eテスト。UI変更時には送信セレクターの調整が必要な場合があります。
