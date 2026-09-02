#!/usr/bin/env python3
"""投稿キューから1本を選んで Instagram に公開する。

GitHub Actions が毎日1回起動してこれを実行する。
Windsor.ai の write action `create_video_post` を叩いている。
Instagram は単一動画のフィード投稿をすべてリールとして公開する。

キューに出せるものが無ければ、何もせずに正常終了する。
ネタが無いまま自動で回り続けないための作りである。
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

REPO = "chikatabi/chikatabi-ig-media"
BRANCH = "main"
ACCOUNT = "17841410925416057"  # Instagram @chika_tabi_
ENDPOINT = "https://connectors.windsor.ai/instagram/actions"
QUEUE_PATH = "queue.json"
JST = timezone(timedelta(hours=9))


def raw_url(path):
    """リポジトリ内のファイルの、誰でも開ける URL を組み立てる。

    Instagram は公開URLの動画しか受け付けないため、この経路が必要になる。
    """
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"


def load_queue():
    with open(QUEUE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue, message):
    """キューを書き戻して、その変更をリポジトリに記録する。"""
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        f.write("\n")
    subprocess.run(["git", "add", QUEUE_PATH], check=True)
    subprocess.run(["git", "commit", "-m", message], check=True)
    subprocess.run(["git", "push"], check=True)


def pick(queue, today):
    """公開日が今日以前で、まだ出していない先頭の1本を返す。

    status の意味:
      draft   … CHIKA がタイトルとキャプションを確認していない。出さない
      ready   … 出してよい
      posting … 投稿の途中で止まった。人が見るまで先へ進めない
      done    … 公開済み
    """
    for entry in queue:
        if entry.get("status") == "posting":
            sys.exit(
                f"前回の実行が投稿の途中で止まっています（{entry['id']}）。\n"
                "Instagram に出ているかを目で確かめてから、queue.json の status を\n"
                "出ていれば done、出ていなければ ready に直してください。\n"
                "二重投稿を避けるため、ここでは自動で判断しません。"
            )
    for entry in queue:
        if entry.get("status") == "ready" and entry["date"] <= today:
            return entry
    return None


def check_url(url):
    """動画が本当に公開されているかを、投稿前に確かめる。"""
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 200:
                sys.exit(f"動画のURLが {response.status} を返しました: {url}")
            return int(response.headers.get("Content-Length", 0))
    except urllib.error.URLError as error:
        sys.exit(f"動画のURLを開けませんでした: {url}\n{error}")


def publish(video_url, caption, api_key):
    body = json.dumps(
        {
            "account": ACCOUNT,
            "action": "create_video_post",
            "params": {"video_url": video_url, "caption": caption},
        }
    ).encode()
    request = urllib.request.Request(
        f"{ENDPOINT}?api_key={api_key}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        sys.exit(f"Windsor が {error.code} を返しました。\n{detail}")


def main():
    api_key = os.environ.get("WINDSOR_API_KEY")
    if not api_key:
        sys.exit(
            "WINDSOR_API_KEY が設定されていません。\n"
            "リポジトリの Settings > Secrets and variables > Actions で登録してください。"
        )

    today = datetime.now(JST).strftime("%Y-%m-%d")
    queue = load_queue()
    entry = pick(queue, today)
    if entry is None:
        print(f"{today}: 今日出す動画はキューにありません。何もしませんでした。")
        return

    url = raw_url(entry["video"])
    size = check_url(url)
    print(f"{entry['id']} を投稿します（{entry['video']} / {size:,} バイト）")

    # 投稿を始める前に印を付けて記録しておく。
    # ここで記録しておかないと、投稿が成功した直後に落ちたときに
    # 次の実行が同じ動画をもう一度出してしまう。
    entry["status"] = "posting"
    save_queue(queue, f"Start posting {entry['id']}")

    result = publish(url, entry["caption"], api_key)

    entry["status"] = "done"
    entry["posted_at"] = datetime.now(JST).isoformat(timespec="seconds")
    entry["result"] = json.dumps(result, ensure_ascii=False)
    save_queue(queue, f"Posted {entry['id']}")
    print(entry["result"])


if __name__ == "__main__":
    main()
