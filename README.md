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

最新版は [GitHub Releases](https://github.com/yohi/turnshade/releases/latest) の **Assets** にある `turnshade-vX.Y.Z.zip` をダウンロードしてください。初期設定・公開が完了した後は、上記のGitHub Pagesによる署名済みCRX自動更新も利用できます。GitHubが自動生成する **Source code (zip)** は拡張本体の配布物ではありません。

- CIの実行環境は `ubuntu-slim`。PushとPull RequestでJavaScript構文と単体テストを検証し、拡張ファイルのみZIP化します。
- Google製の [release-please](https://github.com/googleapis/release-please) が、`master` 上の **Conventional Commits** から次のバージョンを判定し、**Release PR** を作成します。
- 例: `fix: repair shade detection` はpatch (`1.1.0 → 1.1.1`)、`feat: add a shortcut` はminor (`1.1.0 → 1.2.0`)、`feat!: change supported layouts` はmajor (`1.1.0 → 2.0.0`)。
- Release PRには `CHANGELOG.md`、`version.txt`、`.release-please-manifest.json`、`manifest.json` のバージョン更新が含まれます。**普段は手動でバージョンを上げないでください。**
- Release PRを`master`にマージすると、release-pleaseが`vX.Y.Z`タグとGitHub Releaseを生成し、CIでテスト・作成した `turnshade-vX.Y.Z.zip` と `.sha256` をそのReleaseに添付します。
- 既存の `v1.1.0` は起点として維持し、今回のCI移行だけで別バージョンは発行しません。

**運用上の注意:** `GITHUB_TOKEN` がRelease PRを作成できない場合は、GitHubリポジトリの **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests** を有効にしてください。また、`GITHUB_TOKEN` が作成したPRは後続の通常のCIトリガーを発火させないため、リリースPRは内容を確認してからマージしてください。

## ワンライナーでインストール（Ubuntu / Google Chrome）

**配布サイトへの `install.sh` 公開後**は、GitHub Pagesから次のコマンド1行でTurnShadeを登録できます。

```sh
curl -fsSL https://yohi.github.io/turnshade/install.sh | sh

# Chrome Beta の全Profileに登録
curl -fsSL https://yohi.github.io/turnshade/install.sh | sh -s -- --channel beta

# Chrome Dev（google-chrome-unstable）の全Profileに登録
curl -fsSL https://yohi.github.io/turnshade/install.sh | sh -s -- --channel dev
```

- Chrome Web Store不要、ZIP/CRXダウンロード不要、ソースの展開フォルダー不要。
- `--channel stable|beta|dev` に対応（省略時 `stable`）。Chrome公式のチャネル別インストール先 `/opt/google/chrome/extensions/`、`/opt/google/chrome-beta/extensions/`、`/opt/google/chrome-unstable/extensions/` に `<拡張ID>.json` を登録します。`/usr/share/google-chrome/extensions/` はチャネル間で共有されるため、新規には書き込まず、既存登録の検証のみ行います。既存設定が異なる場合、共有先との重複、シンボリックリンクを検出した場合は停止します。システムへの書き込み時だけ `sudo` を使います。Chromium/Snap/Canaryは未対応です。
- 既に同じ内容で登録済みなら変更せず正常終了。異なる登録内容、シンボリックリンク、想定外の拡張ID・CRX配信URLの場合は停止し、設定を上書きしません。
- インストール後はChromeを完全終了・再起動し、`chrome://extensions`でTurnShadeを確認します。自動更新は既存のGitHub Pages経由です。

**Profileについて：** 上記の登録はChromeの**チャネル全体**に適用されます。同一チャネル内の `Default`、`Profile 1` などを指定してインストールすることはできません。特定のProfileだけでTurnShadeを使いたい場合は、各Profileの `chrome://extensions` で有効/無効を管理してください。Profileの `Preferences` や `Secure Preferences` をスクリプトで書き換えることはしません。

ChromeのProfileの場所は `chrome://version` の `Profile Path` で確認できます。通常のLinuxユーザーデータディレクトリはStable=`~/.config/google-chrome`、Beta=`~/.config/google-chrome-beta`、Dev=`~/.config/google-chrome-unstable` ですが、`--user-data-dir` 等で変更可能です。これらは**ブラウザのプロファイルデータ格納先**であり、TurnShadeの登録用JSONの配置先ではありません。

- **`curl | sh`はインターネットから取得したスクリプトを直接実行します。** 実行前にソースを確認するなら、下記の方法を推奨します。

```sh
curl -fsSLo turnshade-install.sh https://yohi.github.io/turnshade/install.sh
less turnshade-install.sh
sh turnshade-install.sh
rm turnshade-install.sh
```

重要：このインストーラーは、**PRがマージされただけでは公開されません**。初回に限りGitHub Actionsの `Publish installer to existing signed Release site` を`master`から手動実行し、最新の正式リリース（例：`v1.5.0`）を指定してください。既存の署名済みCRXを変更・再署名せずに、同じCRXと更新XML、`install.sh`を1回のGitHub Pagesデプロイで公開します。今後の新しいReleaseでもインストーラーは自動で含まれます。公開前に `curl -fsSL https://yohi.github.io/turnshade/install.sh` がスクリプトを返すことを必ず確認してください。

## GitHub連携の自動配布（Linux版Chrome・Web Store非公開）

TurnShadeはGitHub Releasesに署名済みCRXを保存し、GitHub Pagesに更新マニフェストと**同じCRXをまとめて公開**します。ChromeはGitHub Pagesから最新版を取得でき、ユーザーがCloneやZIP展開フォルダーを維持する必要はありません。Chrome管理の拡張データと小さなLinux登録JSONは残ります。

**予定するURL（初期設定・初回公開が完了するまでは利用できません）：**

- 更新XML: https://yohi.github.io/turnshade/updates.xml
- 配信用CRX: https://yohi.github.io/turnshade/turnshade-vX.Y.Z.crx
- 永続アーカイブ: https://github.com/yohi/turnshade/releases

### Ownerの初期設定（公開前）

1. 署名用RSA秘密鍵を**一度だけ**生成し、Bitwarden等の安全な場所に暗号化バックアップする。今後も同じ鍵が必須です。秘密鍵をリポジトリ・Issue・PR・ログ・CI成果物に登録しない。
2. 生成した鍵をもとに32文字の拡張IDを計算する。作成済み秘密鍵が signing.pem にあり、作業ツリーに scripts/build_update_site.py がある場合の例：

       python3 - <<'PY'
       from pathlib import Path
       from scripts.build_update_site import extension_id_from_key
       print(extension_id_from_key(Path("signing.pem"))[0])
       PY

3. リポジトリの **Settings → Secrets and variables → Actions** へ次を登録する。
   - Repository secret **TURNSHADE_CRX_PRIVATE_KEY_PEM**: 秘密鍵PEM全文
   - Repository variable **TURNSHADE_EXTENSION_ID**: 上で得た32文字の拡張ID
   - Repository variable **TURNSHADE_CRX_PUBLISH_ENABLED**: 初期は false（未設定でもよい）
4. **Settings → Pages → Build and deployment → Source: GitHub Actions** を選択。必要に応じて Environment **crx-signing** に手動承認を設ける。
5. GitHub Actions の **Publish signed CRX and Chrome update site** から、master と**新方式の update_url が入った最新の正式Release**を指定して初回公開する。v1.4.0は update_url を含まないため公開不可。新方式のRelease発行後に実施する。
6. XMLが取得できて appid が期待IDと一致し、配信CRXの応答ヘッダー（Content-Type / X-Content-Type-Options）とLinux Chromeの導入・更新が正常なことを確認する。**GitHub Pagesを使った実機自動更新はまだ未検証**。
7. 検証後、Repository variable **TURNSHADE_CRX_PUBLISH_ENABLED=true** に変更する。以後は新Release作成をトリガーに、既存テスト済みZIPからCRXを署名し、Releaseに保存したうえでPagesへXMLとCRXを公開する。PRマージだけでReleaseが発行されなければ配布は動かない。

CIでは使い捨て鍵でCRX3生成とXML構築をスモークテストし、正式な鍵は使いません。実配布では拡張ID・公開鍵・ZIPハッシュ・バージョンを検証し、不一致なら停止します。

### Ubuntu Chromeでの初回導入（CRXファイルのダウンロード不要）

公開XMLの appid に示される**実際の拡張ID**を設定し、Linuxの公式 external_update_url 方式を使います。下記のファイルは小さな設定JSONであり、拡張の展開フォルダーではありません。

    EXTENSION_ID='実際の32文字の拡張IDに置き換える'
    [[ "$EXTENSION_ID" =~ ^[a-p]{32}$ ]] || { echo 'Invalid extension ID' >&2; exit 1; }
    sudo install -d -m 755 /opt/google/chrome/extensions
    printf '{"external_update_url":"https://yohi.github.io/turnshade/updates.xml"}\n' \
      | sudo tee "/opt/google/chrome/extensions/${EXTENSION_ID}.json" >/dev/null
    sudo chmod 644 "/opt/google/chrome/extensions/${EXTENSION_ID}.json"

Google Chromeを再起動して chrome://extensions にTurnShadeが現れることを確認します。旧「パッケージ化されていないTurnShade」はOFFにして重複動作を防いでください。署名版では拡張IDが変わり、設定が自動移行しない場合があります。

### 更新・運用上の制約

- Chromeは数時間おきに更新XMLを参照し、新バージョンがあれば**同じ秘密鍵で署名されたCRX**に更新します。chrome://extensions の「拡張機能を更新」でも確認できます。
- Pages配布はXMLとCRXの**単一デプロイ**です。過去の署名済みCRXはReleasesに残ります。配信不具合に備え、旧バージョンの利用環境を直ちに削除しないでください。
- PagesがChromeの要求するHTTPヘッダーに対応しない場合は、Content-Typeを制御可能な別のホスティング先が必要です。公開後の実機試験をGateとします。
- Linux用の外部拡張登録方式はWeb Store不要ですが、Windows/macOSで同じ仕組みを使えるとは限りません。

参考：
- https://developer.chrome.com/docs/extensions/how-to/distribute/host-on-linux
- https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

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
