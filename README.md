# tufs-daily-article

「今日は何の日？」をフックに関連学術論文を紹介する、大学図書館向け日次自動更新ウィジェットです。
GitHub Actions と GitHub Pages で動作し、**外部サーバー不要・無料**で運用できます。

```
┌─────────────────────────────┐
│  📅 今日は何の日？― 3月4日  │
│  1932年：…が起きた日        │
│                              │
│  📄 論文タイトル（英語）     │
│  著者名 ／ ジャーナル名      │
│                              │
│  [日本語要約テキスト]        │
│                              │
│  [この論文を読む →]          │
├─────────────────────────────┤
│  この論文が読めるデータベース │
│  Taylor & Francis SSH Library│
│  🔒 大学ネットワーク接続必要 │
│  [データベースへアクセス →]  │
└─────────────────────────────┘
```

## 概要

毎朝 0:30（JST）に GitHub Actions が自動実行され、

1. **Wikipedia** から当日の「できごと」をランダムに 1 件取得
2. **Gemini API** で学術英語キーワードに変換
3. **CrossRef API** で契約ジャーナルの論文を検索
4. **Gemini API** で Abstract を日本語 200 字に要約
5. `data/today.json` を更新 → GitHub Pages に自動反映

ウィジェットは `<iframe>` または JS スニペットで大学 HP に埋め込んで使用します。

## 技術スタック

| 種別 | 内容 |
|------|------|
| 言語 | Python 3.11 |
| 主要ライブラリ | `google-genai`, `requests`, `pdfplumber` |
| AI | Gemini 2.5 Flash（Google AI Studio） |
| 外部 API | Wikipedia MediaWiki API / CrossRef REST API / Unpaywall API |
| ホスティング | GitHub Pages（静的） |
| CI/CD | GitHub Actions |

## セットアップ手順

### 1. リポジトリをフォーク

GitHub の「Fork」ボタンでご自分のアカウントにフォークしてください。

### 2. GitHub Pages を有効化

リポジトリの **Settings → Pages → Branch: `main` / フォルダ: `/ (root)`** を選択して Save。

### 3. GitHub Secrets を登録

**Settings → Secrets and variables → Actions → New repository secret** から以下を登録：

| Secret 名 | 内容 |
|-----------|------|
| `GEMINI_API_KEY` | Google AI Studio で発行した API キー |
| `CONTACT_EMAIL` | CrossRef・Unpaywall の polite pool 用メールアドレス |

### 4. `data/databases.json` を自機関向けに編集

→ 「[契約 DB マスタのカスタマイズ](#契約-db-マスタのカスタマイズ)」 を参照

### 5. ISSN マスタを初期生成

**Actions → Update ISSN Master → Run workflow** を手動実行してください。
`data/issn-master.json` に契約ジャーナルの ISSN 一覧が保存されます。

### 6. 動作確認

**Actions → Daily Article Update → Run workflow** を手動実行して
`data/today.json` が更新されることを確認してください。

## 環境変数

`.env.example` を参考に `.env` を作成してください（`.env` はコミットしないこと）。

| 変数名 | 説明 |
|--------|------|
| `GEMINI_API_KEY` | Google AI Studio の API キー |
| `CONTACT_EMAIL` | API polite pool 用のメールアドレス（大学ドメイン推奨） |
| `ROR_ID` | 教員著作論文フォールバック用の機関 ROR ID（変更任意） |

ROR ID は [ror.org](https://ror.org) で機関名を検索して確認してください。
（例：`https://ror.org/03f4q9q08`）

## デプロイ方法

| ワークフロー | スケジュール | 説明 |
|-------------|-------------|------|
| `daily.yml` | 毎日 JST 0:30 | `today.json` を更新し GitHub Pages に反映 |
| `update-titles.yml` | 毎月 1 日 JST 1:00 | 契約ジャーナル ISSN マスタを更新 |

どちらも **Actions タブ → Run workflow** で手動実行できます。

## ウィジェットの埋め込み方法

GitHub Pages の URL は `https://{username}.github.io/tufs-daily-article/` です。

### iframe による埋め込み（推奨）

```html
<iframe
  src="https://{username}.github.io/tufs-daily-article/widget/"
  width="420"
  height="600"
  frameborder="0"
  style="border:none;">
</iframe>
```

### JS スニペットによる埋め込み

```html
<div id="daily-article-widget"></div>
<script src="https://{username}.github.io/tufs-daily-article/widget/widget.js"></script>
```

推奨表示サイズ：幅 320〜420px、高さ 550〜650px（コンテンツ量により変動）

### 過去記事の閲覧

`https://{username}.github.io/tufs-daily-article/widget/archive.html` で日付別の過去記事を閲覧できます。

## 契約 DB マスタのカスタマイズ

`data/databases.json` を編集して自機関の契約 DB に合わせてください。

```json
[
  {
    "id": "your-db-id",
    "name": "データベース表示名",
    "description": "ウィジェットに表示する説明文（1〜2文）",
    "url": "https://your-database-url.com/",
    "doi_domain": "publisher-domain.com",
    "access_note": "大学ネットワークまたはVPN接続が必要",
    "ip_restricted": true,
    "fields": ["分野1", "分野2"]
  }
]
```

**`doi_domain`** は CrossRef が返す DOI の URL から判定に使います。
例：DOI が `https://doi.org/10.1080/xxxxx` なら `tandfonline.com`

**ISSN の調べ方**：

- Taylor & Francis SSH：[タイトルリスト PDF](https://files.taylorandfrancis.com/ssh-title-list.pdf) 参照
- JSTOR：`data/databases.json` の `id` を `jstor` にすれば KBART から自動取得
- その他 DB：[CrossRef の ISSN 検索](https://www.crossref.org/titleList/) または各 DB の管理画面

## T&F タイトルリスト URL の更新方法

T&F SSH の PDF URL が変わった場合：

1. `scripts/update_issn_master.py` の `TF_PDF_URL` を新しい URL に変更
2. コミット・プッシュ後、Actions から `Update ISSN Master` を手動実行

> PDF を直接配布せず HTML ページ経由になった場合は、`update_issn_master.py` の
> `download_pdf()` をスクレイピングに変更する必要があります。

## フォールバックの動作説明

検索結果が 0 件の場合、以下の順序で代替論文を探します：

```
① CrossRef × 契約 ISSN フィルタ（T&F SSH）
   ↓ 0件
② Gemini でキーワードを抽象化して再検索（T&F SSH）
   ↓ 0件
③ 同キーワードで JSTOR ISSN フィルタに切り替えて再検索
   ↓ 0件
④ 教員著作論文フォールバック（ROR ID → affiliation 文字列の順）
   ↓ すべて失敗
前日の today.json をそのまま維持（GitHub Actions は exit 0 で終了）
```

`today.json` の `flow` フィールドで実際に使われたフローを確認できます。

**他機関で導入する場合の必須変更**：
`.github/workflows/daily.yml` の `ROR_ID` を自機関の ROR ID に変更してください。

## 利用上の注意・免責事項

- **アクセス制限**：表示される論文は大学の契約状況によりアクセスできない場合があります。必要に応じて `access_note` を更新してください。
- **Gemini 生成コンテンツ**：日本語要約は AI が生成するものであり、内容の正確性を保証しません。
- **論文情報の正確性**：書誌情報はすべて CrossRef API から取得した実データを使用しています。Gemini に論文タイトル・著者・DOI を生成させる処理は含まれていません。
- **API 利用規約**：各 API の利用規約を遵守してください。
  - [Wikimedia API 利用規約](https://www.mediawiki.org/wiki/API:Main_page#Terms_and_conditions)
  - [CrossRef Polite Pool ポリシー](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/)
  - [Unpaywall API 利用規約](https://unpaywall.org/products/api)
  - [Google AI Studio 利用規約](https://ai.google.dev/terms)

## Gemini API の費用について

Google AI Studio の無料枠内で運用する想定です。

| モデル | 無料枠（目安） |
|--------|--------------|
| `gemini-2.5-flash` | 1 日 500 リクエストまで（2025 年時点） |
| `gemini-2.0-flash` | フォールバック用（429 時に自動切り替え） |

1 日 1 回の実行では Gemini API 呼び出しは最大 3〜4 回（キーワード生成・言い換え・日本語要約）のため、
通常は無料枠に収まります。

> 2025 年 12 月以降、無料枠の制限が強化される予定です。
> 最新情報は [Google AI Studio の料金ページ](https://ai.google.dev/pricing) をご確認ください。

## アクセス計測

GitHub リポジトリの **Insights → Traffic** でページビュー・ユニークビジターの概算を確認できます。

より詳細な計測が必要な場合は `widget/index.html` のコメントを外して
[GoatCounter](https://www.goatcounter.com/)（無料・プライバシーフレンドリー）を有効にしてください。

## ライセンス

[MIT License](LICENSE)

Copyright (c) 2026 ohnuno

## コントリビューション

Issue・Pull Request を歓迎します。

- バグ報告・機能提案：GitHub Issues
- 他機関への導入事例の共有も歓迎します

---

> このプロジェクトはある大学図書館が開発・公開するオープンソースソフトウェアです。
