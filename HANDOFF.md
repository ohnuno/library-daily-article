# HANDOFF.md — tufs-daily-article

Claude Codeへの実装引き継ぎ資料。
このファイルを読んだうえで実装を開始すること。

---

## プロジェクト概要

大学が契約する電子コンテンツ（学術論文・ジャーナル）の利用促進を目的とした、
日次自動更新ウィジェットシステム。

「今日は何の日？」をフックに関連論文を紹介し、
収録データベースへの認知・アクセスを促す。
大学ホームページに埋め込んで使用する。

**想定利用機関：** 東京外国語大学図書館  
**GitHubリポジトリ名：** `tufs-daily-article`  
**公開方法：** GitHub Pages（静的ホスティング）

---

## システム構成

```
[GitHub Actions] ← 毎日JST 0:30に実行
      |
      ├─ 1. Wikipedia API → 今日の出来事を取得・キーワード抽出
      |
      ├─ 2. Gemini API → キーワードを学術的英語検索語に変換
      |
      ├─ 3. CrossRef API → 論文検索（ISSNフィルタあり）
      |
      ├─ 4. Unpaywall API → OA版PDF確認（Abstract補完用）
      |
      ├─ 5. Gemini API → AbstractをGeminiで日本語要約生成
      |
      ├─ 6. data/today.json を更新・コミット
      |
      └─ 7. GitHub Pages に自動デプロイ

[埋め込みウィジェット] ← 大学HPのiframe / JSスニペットから参照
      |
      └─ data/today.json を読み込んで表示
```

### 月次バッチ（別途）

```
[GitHub Actions] ← 毎月1日に実行
      |
      └─ T&F SSH タイトルリストPDFを自動ダウンロード
            → ISSNマスタ（data/issn-master.json）を更新
```

---

## ディレクトリ構成（目標）

```
tufs-daily-article/
├── .github/
│   └── workflows/
│       ├── daily.yml          # 日次バッチ
│       └── update-titles.yml  # 月次タイトルリスト更新
├── data/
│   ├── today.json             # 日次生成コンテンツ（自動更新）
│   ├── issn-master.json       # 契約DBのISSNマスタ（自動更新）
│   └── databases.json         # DBメタ情報（手動管理）
├── scripts/
│   ├── fetch_daily.py         # 日次バッチ本体
│   └── update_issn_master.py  # タイトルリスト更新スクリプト
├── widget/
│   ├── index.html             # ウィジェット本体
│   ├── style.css              # スタイル
│   └── widget.js              # JSスニペット（埋め込み用）
├── .env.example               # 環境変数テンプレート
├── requirements.txt           # Pythonパッケージ
└── README.md                  # 公開用README（後述の仕様で作成）
```

---

## 環境変数

### GitHub Secretsに登録するもの

| 変数名 | 内容 |
|--------|------|
| `GEMINI_API_KEY` | Google AI StudioのAPIキー |
| `CONTACT_EMAIL` | CrossRef・Unpaywallのpolite pool用メールアドレス |

### `.env.example`（リポジトリに含めること）

```env
# Gemini API（Google AI Studio で発行）
GEMINI_API_KEY=your_gemini_api_key_here

# CrossRef・Unpaywall 連絡先メールアドレス（APIキーではない）
CONTACT_EMAIL=library@example.ac.jp

# 機関 ROR ID（他機関導入時は差し替え）
ROR_ID=https://ror.org/03f4q9q08
```

> **注意：** `.env`は`.gitignore`に追加し、絶対にコミットしないこと。

---

## 使用API一覧

### Wikipedia MediaWiki API
- **用途：** 今日の出来事テキストの取得
- **認証：** 不要
- **費用：** 無料
- **エンドポイント例：**
  ```
  https://ja.wikipedia.org/w/api.php?action=query&prop=revisions&rvprop=content&titles=3月4日&format=json
  ```
- **取得対象：** `== できごと ==` セクションのテキスト
- **注意：** Wikimediaの利用規約に従いUser-Agentヘッダーを設定すること

### Gemini API（Google AI Studio）
- **用途①：** Wikipediaテキストから学術的英語キーワードの生成
- **用途②：** 論文AbstractのGeminiによる日本語要約生成
- **認証：** APIキー（GitHub Secret: `GEMINI_API_KEY`）
- **使用モデル：** `gemini-2.5-flash`（無料枠内で運用）
- **費用：** 1日1〜数回の実行であれば無料枠内に収まる見込み
- **無料枠の目安：** 1日20〜500リクエスト（モデルにより異なる。2025年12月以降制限強化）
- **ハルシネーション対策：** 個別論文タイトル・著者名・DOIはGeminiに生成させない

### CrossRef REST API
- **用途：** ISSNフィルタを用いた論文検索・書誌情報・Abstract取得
- **認証：** 不要（`mailto`パラメータでpolite pool利用）
- **費用：** 無料
- **エンドポイント例：**
  ```
  https://api.crossref.org/works?query=linguistics&filter=issn:0047-4045&mailto=library@example.ac.jp
  ```
- **検索フィールド：** タイトル・著者・Abstract（全文検索ではない）
- **注意：** AbstractはCrossRefに登録されている場合のみ取得可能

### Unpaywall API
- **用途：** DOIからOA版PDFのURL取得（Abstract補完用）
- **認証：** 不要（`email`パラメータ必須）
- **費用：** 無料（1日10万件まで）
- **エンドポイント例：**
  ```
  https://api.unpaywall.org/v2/{DOI}?email=library@example.ac.jp
  ```

### ROR API
- **用途：** 教員著作論文フォールバック時の機関識別
- **認証：** 不要
- **費用：** 無料（CC0）
- **東京外国語大学ROR ID：** `https://ror.org/03f4q9q08`
  - ※実装前にROR（ror.org）で確認すること

---

## データ仕様

### `data/databases.json`（手動管理）

契約DBのメタ情報。DOIドメインでどのDBかを判別するために使用。

```json
[
  {
    "id": "taylor-francis-ssh",
    "name": "Taylor & Francis SSH Library",
    "description": "社会科学・人文科学分野の1,400誌以上を収録するジャーナルパッケージ。1997年以降のバックファイルにアクセス可能。",
    "url": "https://www.tandfonline.com/",
    "doi_domain": "tandfonline.com",
    "access_note": "大学ネットワークまたはVPN接続が必要",
    "ip_restricted": true,
    "fields": ["社会科学", "人文科学", "教育", "経済", "言語学", "地理", "法学", "心理学", "社会学"]
  },
  {
    "id": "jstor",
    "name": "JSTOR",
    "description": "人文・社会科学を中心とした学術雑誌・図書のアーカイブデータベース。",
    "url": "https://www.jstor.org/",
    "doi_domain": "jstor.org",
    "access_note": "大学ネットワークまたはVPN接続が必要",
    "ip_restricted": true,
    "fields": ["人文科学", "社会科学", "歴史", "文学", "哲学"]
  }
]
```

### `data/issn-master.json`（自動更新）

T&F SSHおよびJSTORの契約タイトルISSN一覧。月次バッチで自動生成。

```json
{
  "updated_at": "2026-03-01",
  "sources": {
    "taylor-francis-ssh": {
      "title_list_url": "https://files.taylorandfrancis.com/ssh-title-list.pdf",
      "issns": ["0047-4045", "1360-0869", "..."]
    },
    "jstor": {
      "title_list_url": "https://www.jstor.org/...",
      "issns": ["0002-9602", "..."]
    }
  }
}
```

### `data/today.json`（日次自動生成）

```json
{
  "date": "2026-03-04",
  "generated_at": "2026-03-04T00:30:00+09:00",
  "flow": "primary",
  "today_topic": {
    "text": "1877年：エジソンが蓄音機の特許を取得した",
    "keywords_ja": ["エジソン", "蓄音機", "特許"],
    "keywords_en": ["phonograph", "sound recording", "acoustic technology", "patent history"]
  },
  "paper": {
    "title": "The Political Economy of Sound Recording",
    "authors": ["Smith, J.", "Brown, K."],
    "journal": "Media, Culture & Society",
    "issn": "0163-4437",
    "year": 2019,
    "doi": "10.1177/0163443718810526",
    "doi_url": "https://doi.org/10.1177/0163443718810526",
    "abstract_original": "This article examines...",
    "abstract_ja": "本論文は、録音技術の政治経済学的側面を考察し...",
    "db_id": "taylor-francis-ssh"
  },
  "database": {
    "id": "taylor-francis-ssh",
    "name": "Taylor & Francis SSH Library",
    "description": "社会科学・人文科学分野の1,400誌以上を収録するジャーナルパッケージ。",
    "url": "https://www.tandfonline.com/",
    "access_note": "大学ネットワークまたはVPN接続が必要",
    "ip_restricted": true
  }
}
```

**`flow`フィールドの値：**
- `primary` — ①通常の検索でヒット
- `retry` — ②キーワード変更後にヒット
- `fallback-db` — ③別DB（JSTOR等）でヒット
- `fallback-faculty` — ④教員著作論文フォールバック

---

## 処理フロー詳細

### 日次バッチ（`scripts/fetch_daily.py`）

```
1. Wikipedia APIで今日の日付ページを取得
   → 「できごと」セクションからテキストを抽出
   → 複数ある場合はランダムに1件選択

2. Geminiに以下を指示：
   「次の出来事から、学術論文検索に適した英語キーワードを
    3〜5語生成してください。固有名詞よりも概念・分野語を優先すること。
    出力はJSON配列のみ。」

3. CrossRef APIで検索
   - query: Geminiが生成したキーワード
   - filter: issn:{issn-master内の全ISSN}（T&F SSH優先）
   - rows: 5（候補を複数取得してAbstractがあるものを選ぶ）
   - sort: relevance

4. ヒットした論文のAbstractをGeminiで日本語要約（200字程度）
   - プロンプト：「以下のAbstractを、大学生が読んでわかる日本語で200字以内に要約してください。」
   - AbstractがCrossRefにない場合：Unpaywallでリトライ

5. DOIドメインからdb_idを判定（databases.jsonのdoi_domainと照合）

6. today.jsonを生成・コミット
```

### フォールバックフロー

```
① CrossRef × T&F SSH ISSNフィルタ → ヒット → 採用
  ↓ 0件
② Geminiにキーワードを抽象化・言い換えさせて再検索
   プロンプト：「次のキーワードをより広い学術概念に言い換えてください。」
  → ヒット → 採用
  ↓ 0件
③ ISSNフィルタをJSTORに切り替えて再検索
  → ヒット → 採用
  ↓ 0件
④ 教員著作論文フォールバック
   a. CrossRef × ROR ID（ROR_ID）で検索
   b. 0件の場合：CrossRef × query.affiliation="Tokyo University of Foreign Studies"
   c. 結果をT&F SSH ISSNフィルタで絞り込み
   d. ヒットなければISSNフィルタなしで表示（DB案内は分野マッチングで選択）
```

---

## ウィジェット仕様

### 画面レイアウト

```
┌─────────────────────────────┐
│  【今日は何の日？】           │
│  ○月○日：△△が起きた日       │
│                              │
│  📄 論文タイトル（英語）      │
│  著者名 ／ 掲載ジャーナル名  │
│  出版年                      │
│                              │
│  [日本語要約テキスト]        │
│  （Gemini生成・200字程度）   │
│                              │
│  [この論文を読む →]          │
│  （DOIリンク・外部遷移）     │
├─────────────────────────────┤
│  【この論文が読めるDB】       │
│  Taylor & Francis            │
│  SSH Library                 │
│                              │
│  [DB説明テキスト]            │
│                              │
│  🔒 大学ネットワークまたは   │
│     VPN接続が必要です        │
│                              │
│  [データベースへアクセス →]  │
└─────────────────────────────┘
```

### 埋め込み方法（2種類実装すること）

**iframeによる埋め込み：**
```html
<iframe
  src="https://{username}.github.io/tufs-daily-article/widget/"
  width="400"
  height="600"
  frameborder="0"
  style="border:none;">
</iframe>
```

**JSスニペットによる埋め込み：**
```html
<div id="daily-article-widget"></div>
<script src="https://{username}.github.io/tufs-daily-article/widget/widget.js"></script>
```

### デザイン方針
- 外部CSSフレームワーク不使用（Vanilla CSS）
- 埋め込み先のデザインに馴染む最小限のスタイルのみ
- レスポンシブ対応（最小幅320px）
- フォントはシステムフォントのみ使用

---

## GitHub Actions設定

### 日次バッチ（`.github/workflows/daily.yml`）

```yaml
name: Daily Article Update
on:
  schedule:
    - cron: '30 15 * * *'  # JST 0:30（UTC 15:30）
  workflow_dispatch:        # 手動実行も可能にする

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python scripts/fetch_daily.py
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          CONTACT_EMAIL: ${{ secrets.CONTACT_EMAIL }}
          ROR_ID: https://ror.org/03f4q9q08
      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/today.json
          git diff --staged --quiet || git commit -m "chore: update today's article [$(date +%Y-%m-%d)]"
          git push
```

### 月次タイトルリスト更新（`.github/workflows/update-titles.yml`）

```yaml
name: Update ISSN Master
on:
  schedule:
    - cron: '0 16 1 * *'   # 毎月1日 JST 1:00
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python scripts/update_issn_master.py
      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/issn-master.json
          git diff --staged --quiet || git commit -m "chore: update ISSN master [$(date +%Y-%m)]"
          git push
```

---

## タイトルリスト取得仕様

### Taylor & Francis SSH Library
- **配布URL：** `https://files.taylorandfrancis.com/ssh-title-list.pdf`
  - ※URLにGAパラメータが付いた形で共有されているが、ベースURLが固定かどうかは実装時に確認すること
  - 固定でない場合は `https://librarianresources.taylorandfrancis.com/collection/social-science-humanities-library/` から最新URLをスクレイピングする
- **形式：** PDF（pdfplumberでテキスト抽出してISSN列をパース）
- **更新頻度：** 年次（月1回チェックで十分）

### JSTOR
- タイトルリストの取得方法は実装時に確認が必要
- CrossRef APIのISSNフィルタでJSTORのISSNを使う代替案も検討すること

---

## 実装上の注意事項

### ハルシネーション防止（重要）
- GeminiへのプロンプトはDBマスタのISSN・DB名リストを渡し「この中から選ぶ」形にする
- 個別論文のタイトル・著者・DOIをGeminiに生成させない
- 論文情報はすべてCrossRef APIから取得した実データのみ使用する

### エラーハンドリング
- 各API呼び出しにはtry-catchを実装し、失敗時は次のフォールバックに進む
- すべてのフォールバックが失敗した場合は前日のtoday.jsonをそのまま使用する
- エラーログはGitHub Actionsのログに出力する

### キャッシュ
- CrossRef・Unpaywallのレスポンスは当日中はキャッシュして重複リクエストを避ける

### Gemini APIの節約
- 1日の実行でGemini APIを呼ぶのは最大でも3〜4回に抑える（キーワード生成×1、言い換え×1、要約生成×1）

---

## README.md 作成方針

実装完了後、以下の構成でREADME.mdを作成すること。
GitHubで外部公開するため、他機関の図書館員・エンジニアが読むことを想定する。

### 必須セクション

**一般的な項目**
1. プロジェクト概要（1〜2文 ＋ スクリーンショットまたはデモGIF）
2. 技術スタック（使用言語・主要ライブラリ・外部API一覧）
3. セットアップ手順（clone → 環境構築 → Secrets登録 → GitHub Pages有効化）
4. 環境変数の設定（`.env.example`の各変数の説明）
5. デプロイ方法（GitHub Actions・GitHub Pagesの設定手順）
6. ライセンス（MITを推奨）
7. コントリビューション方針

**このプロジェクト特有の項目**
8. **契約DBマスタのカスタマイズ方法**
   - `data/databases.json`のフォーマット説明
   - 自機関の契約DBに合わせた編集方法
   - ISSNの調べ方・追加手順
9. **ウィジェットの埋め込み方法**
   - iframeコードスニペット（コピペで使えるように）
   - JSスニペット（コピペで使えるように）
   - 推奨表示サイズ
10. **T&FタイトルリストURLの更新方法**
    - URLが変わった場合の対応手順
11. **フォールバックの動作説明**
    - 検索0件時の動作フロー
    - 教員著作論文フォールバックのROR ID変更方法（他機関導入時の必須作業）
12. **利用上の注意・免責事項**
    - 表示論文は契約状況によりアクセスできない場合がある旨
    - Gemini生成コンテンツの正確性に関する免責
    - 各APIの利用規約へのリンク
13. **Gemini APIの費用について**
    - 無料枠の範囲と超過時の課金説明
    - 1日1回実行の場合の費用目安

---

## 未確認事項（実装前に確認すること）

| 確認事項 | 確認方法 |
|----------|----------|
| 東京外国語大学のROR IDが正しいか | ror.orgで「Tokyo University of Foreign Studies」を検索して確認 |
| T&F SSHタイトルリストPDFの安定URLが存在するか | 実際にアクセスしてリダイレクトの有無を確認 |
| JSTORタイトルリストの取得方法 | JSTORサポートサイトで確認 |
| 大学HPのCMSがiframe・JSスニペットを許可しているか | 大学Web担当部門に確認 |
| Gemini APIを大学契約のGoogle Workspaceで利用する場合の制約 | 大学情報部門に確認 |

---

## 開発フェーズ

### Phase 1（MVP・まずここまで）
- [ ] `data/databases.json` の作成（T&F SSH・JSTOR 2件のみ）
- [ ] `scripts/update_issn_master.py` の実装（T&F SSHのみ）
- [ ] `scripts/fetch_daily.py` の実装（①フロー + ④フォールバックのみ）
- [ ] `widget/index.html` の実装（基本レイアウト）
- [ ] GitHub Actions（日次・月次）の設定
- [ ] GitHub Pagesへのデプロイ確認

### Phase 2
- [ ] ②③のフォールバックフロー実装
- [ ] JSスニペット埋め込み対応
- [ ] JSTORタイトルリスト対応
- [ ] ウィジェットのレスポンシブ対応

### Phase 3（オプション）
- [ ] README.md の整備・外部公開
- [ ] 過去コンテンツのアーカイブ表示
- [ ] アクセス計測の簡易実装
