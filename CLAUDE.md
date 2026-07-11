# dashboard — 学習ダッシュボード専用リポ（shindanshi-dashboard）

2026-07-11 に まとめ(shindanshi-matome) から分離。**Gist同期の自動コミットはこのリポにだけ入れる**（まとめの履歴を汚さない）。

## 中身

- `学習ダッシュボード.html` — タスク型ダッシュボード（DATA部をClaudeが直接書換。「更新して」フル更新の対象）
- `学習進捗ダッシュボード.html` — 科目>タブ>論点の達成率（`_progress/update.sh` が再生成する出力先）
- `_progress/` — update.sh・build_dashboard.py・template.html・notes.json ほか

## 更新フロー（旧: まとめでコミット → 新: ここでコミット）

1. `bash _progress/update.sh` — 最新Gist(shindanshi-matome notes)取得 → 再生成 → Chromeで開く
2. コミット＆プッシュは**このリポで**行う: `git add -A && git commit && git push`
3. Pagesデプロイ確認: `gh run list -R Dora-suke/shindanshi-dashboard --limit 1`

公開URL:
- https://dora-suke.github.io/shindanshi-dashboard/学習ダッシュボード.html
- https://dora-suke.github.io/shindanshi-dashboard/学習進捗ダッシュボード.html

## 構造上の約束

- `build_dashboard.py` は**まとめ側の教材を読む**（BASE=../まとめ/1ヶ月前チェック、ROADMAP=../00_総合整理）。本リポは まとめ/dashboard/ に置かれている前提（移動したらパス再調整）。
- 表示・CSSの正本は `_progress/template.html`（生成HTML直編集は再生成で消える）。
- まとめ側の旧URL2箇所はリダイレクトスタブ（削除しない・ブックマーク互換用）。
- まとめリポには本フォルダは入らない（まとめ/.gitignore で `dashboard/` 除外済み）。
