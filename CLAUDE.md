# cancan2542 GitHub Profile (8bit RPG style)

`cancan2542/cancan2542` のプロフィールREADME。ドラクエ風RPG画面のSVGを Python で生成し、
GitHub Actions が毎日統計を更新する。

## Layout
- `profile.toml` — 表示内容（名前・職業・テーマ・メッセージ・skills・links）。内容変更はまずここ
  - `theme`: `gb`（緑の液晶風）/ `mono`（白黒4階調）/ `nes`（カラー）
  - `character`: `bear`（アイコン由来のフードのクマ・24px）/ `hero`（フードの勇者・16px）。`sprites.CHARACTERS` に登録
- `scripts/generate.py` — SVG生成本体。`scripts/sprites.py` — ドット絵グリッドとパレット
- `scripts/preview.sh` — preview コンテナ内で動くスクショ生成
- `dist/*.svg` — 生成物（コミット対象）。**手で編集しない**、必ず再生成する
- `README.md` — `<!-- COMMANDS:START -->`〜`END` は generate.py が `links` から自動生成。手で編集しない
- `assets/fonts/DotGothic16-Regular.ttf` — OFLフォント原本（サブセット化して各SVGに埋め込む）
- `.github/workflows/update.yml` — 毎日00:00 UTC + main への関連push で再生成、snake は `output` ブランチへ

## Commands（すべてDocker経由）
- 生成（ダミー統計）: `docker compose run --rm generate`
- 生成（実統計）: `GITHUB_TOKEN=$(gh auth token) docker compose run --rm generate --live`
- プレビュー: `PREVIEW_OUT=$(mktemp -d) docker compose run --rm preview [ms ...]` → `$PREVIEW_OUT/*.png` を Read で確認
- 依存やDockerfile変更後: `docker compose build`
- セキュリティチェック（通常は hook が自動実行）:
  - 生成物: `sh scripts/check_outputs.sh dist README.md`（トークン漏れ・危険なSVG。CIでも実行）
  - 設定ミス: `docker compose run --rm -T trivy config --severity HIGH,CRITICAL /src`

## Rules
- ローカル環境に依存を入れない: `pip install` / venv / `npm install` をホストで実行しない。実行は必ずコンテナで
- プレビュー等の一時ファイルはリポジトリ外（`mktemp -d`）に出す
- SVGを変更したら、コミット前に必ず generate → preview で目視確認する
- 公開前提のリポジトリなので `git push` はユーザーの明示的な指示があるときだけ行う
- ダミー統計（`--offline`）で生成した `dist/status.svg` はコミットしてよい（Actionsが実統計で上書きする）

## Security hook（`.claude/hooks/security-gate.sh`）
- Pre: `docker compose build` → ビルド入力に未コミット差分があれば ask、trivy config で HIGH 以上なら deny／`git commit` → インデックスの中身を check_outputs + trivy secret で検査／`git push` → 送るコミットの差分にトークンが無いか
- Post: `generate` 後に check_outputs、`build` 後に pip-audit（生成イメージの実パッケージ）と trivy image（`docker save` 経由、HIGH 以上・修正版ありのみ）
- deny/block されたら回避せず原因を直す。Docker やネットワークが無いと「skipped」警告になる（通過扱いではない）
- イメージは非root（`USER app`）。生成イメージからは pip を削除済み（実行時に不要で、vendored 依存の脆弱性が出るため）
- trivy はダイジェストで固定（`compose.yaml`）。更新するときは公開から2週間以上経ったリリースを選ぶ

## Gotchas
- READMEの `<img>` 内SVGは外部リソース・JS・リンクが無効。フォントは base64 埋め込み、リンクは README 側の `<a>` で付ける
- headless Chrome の `<img>` スクショでは CSS アニメが進まない。アニメ確認は preview の `header-<ms>.png`（SVGをインライン化して時間をシーク）を使う
- アニメが動かない環境でも読めるよう、各要素の**非アニメ時の基本状態は「表示済み」**にする（タイプライターの覆いは基本状態で退避位置）
- ユーザーのブラウザでデモを開くときは、SVGを data URI で HTML に埋め込む（macOSの権限制限で Chrome から `~/Documents` 配下の `file://` 画像が読めず、画像が壊れて表示される）
- `GITHUB_TOKEN`（Actions既定）では非公開リポの貢献は数えられない。必要なら Secret `PROFILE_TOKEN`（read:user PAT）

詳細なSVG実装ルールは `.claude/rules/svg.md`（`scripts/**` 編集時に自動ロード）。
