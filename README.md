# chikatabi-ig-media

Instagram `@chika_tabi_` に、毎朝7:30に完成済みのリールを1本ずつ自動で投稿する仕組みです。

Instagram のAPIは公開URLの動画しか受け付けません。そのためこのリポジトリはPublicにしてあり、
`videos/` に置いた動画は誰でもURLを開けば見られる状態になります。

## 使い方

1. `videos/` に完成MP4を置きます。**ファイル名はASCIIにしてください**（日本語名はURLで事故ります）。
2. `queue.json` に1件足します。
3. その1件の `status` を `ready` にします。翌朝7:30に自動で公開されます。

## queue.json の書き方

```json
{
  "id": "008",
  "date": "2026-09-04",
  "slot": "朝",
  "video": "videos/008_asa.mp4",
  "caption": "本文\n\n#chikatabi #旅行 #飛行機",
  "status": "draft"
}
```

`status` の意味は次のとおりです。

| status | 意味 |
|---|---|
| `draft` | CHIKA がタイトルとキャプションを確認していない。**自動では出ません** |
| `ready` | 出してよい。`date` が今日以前になったら公開されます |
| `posting` | 投稿の途中で止まった。人が見るまで先へ進みません |
| `done` | 公開済み。`posted_at` と `result` が書き込まれます |

`ready` のものが1つも無ければ、ワークフローは何もせずに終わります。
ネタが無いまま自動で回り続けないための作りです。

## 動く条件

- リポジトリの Settings → Secrets and variables → Actions に `WINDSOR_API_KEY` が要ります。
- Windsor.ai 側で Settings → API Access →
  「Enable write actions for Claude, ChatGPT & API」がオンになっている必要があります。

## 注意

- **投稿されるのは本番のアカウントです。** 試し打ちの場所はありません。
- GitHub Actions の cron は正確ではなく、混雑時に5〜30分ほど遅れます。
- 手で動かすときは Actions タブから `Run workflow` を押します。
