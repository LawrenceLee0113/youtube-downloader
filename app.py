"""YouTube 下載器：外殼只負責 UI，實際下載交給 bin/ 裡的 yt-dlp（可自我更新）。"""
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk

BASE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
BIN = os.path.join(BASE, "bin")
YTDLP = os.path.join(BIN, "yt-dlp.exe" if os.name == "nt" else "yt-dlp")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # Windows 上不要跳出黑色主控台
# bin/ 放最前面，yt-dlp 會從 PATH 找到 ffmpeg 與 deno
ENV = {**os.environ, "PATH": BIN + os.pathsep + os.environ.get("PATH", "")}
PERCENT = re.compile(r"(\d+(?:\.\d+)?)%")

# MP4 內最好的畫質（AV1 > VP9 > H.264，依解析度優先），音訊用 AAC，只合併不重新壓縮
VIDEO = ["-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b", "--merge-output-format", "mp4"]
AUDIO = ["-x", "--audio-format", "mp3", "--audio-quality", "320K", "--embed-thumbnail"]


def build_args(url, mode, outdir):
    return [YTDLP, *(VIDEO if mode == "video" else AUDIO),
            "--embed-metadata", "--no-playlist", "--newline", "--encoding", "utf-8",
            "-o", os.path.join(outdir, "%(title)s.%(ext)s"), url]


def run(args, on_line):
    """執行 yt-dlp，逐行回呼，回傳 exit code。"""
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=ENV,
                         encoding="utf-8", errors="replace", creationflags=NO_WINDOW)
    for line in p.stdout:
        on_line(line.strip())
    return p.wait()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube 下載器")
        self.resizable(False, False)
        pad = {"padx": 8, "pady": 4}

        ttk.Label(self, text="YouTube 網址：").grid(row=0, column=0, sticky="w", **pad)
        self.url = ttk.Entry(self, width=60)
        self.url.grid(row=0, column=1, columnspan=2, **pad)

        self.mode = tk.StringVar(value="video")
        ttk.Radiobutton(self, text="影片 (MP4)", variable=self.mode, value="video").grid(row=1, column=1, sticky="w", **pad)
        ttk.Radiobutton(self, text="音樂 (MP3)", variable=self.mode, value="audio").grid(row=1, column=2, sticky="w", **pad)

        self.outdir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        ttk.Label(self, text="存到：").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.outdir, width=48).grid(row=2, column=1, sticky="w", **pad)
        ttk.Button(self, text="選擇…", command=self.pick).grid(row=2, column=2, sticky="e", **pad)

        self.bar = ttk.Progressbar(self, length=480, maximum=100)
        self.bar.grid(row=3, column=0, columnspan=3, **pad)
        self.status = ttk.Label(self, text="", width=70)
        self.status.grid(row=4, column=0, columnspan=3, sticky="w", **pad)

        self.dl_btn = ttk.Button(self, text="下載", command=self.download)
        self.dl_btn.grid(row=5, column=1, sticky="e", **pad)
        self.up_btn = ttk.Button(self, text="修復 / 更新下載引擎", command=self.update_engine)
        self.up_btn.grid(row=5, column=2, sticky="e", **pad)

        self.update_engine()  # 每次開啟自動更新

    def pick(self):
        d = filedialog.askdirectory(initialdir=self.outdir.get())
        if d:
            self.outdir.set(d)

    def ui(self, fn, *a):
        self.after(0, fn, *a)  # tkinter 只能在主執行緒動 UI

    def set_status(self, text):
        self.status.config(text=text[:90])
        m = PERCENT.search(text)
        if m and text.startswith("[download]"):
            self.bar["value"] = float(m.group(1))

    def busy(self, on):
        state = "disabled" if on else "normal"
        self.dl_btn.config(state=state)
        self.up_btn.config(state=state)

    def task(self, args, done_ok, done_fail):
        self.busy(True)
        self.bar["value"] = 0

        def work():
            try:
                code = run(args, lambda line: self.ui(self.set_status, line))
            except OSError as e:
                code = None
                self.ui(self.set_status, f"找不到下載引擎：{e}")
            if code == 0:
                self.ui(self.set_status, done_ok)
            elif code is not None:
                self.ui(self.set_status, done_fail)
            self.ui(self.busy, False)

        threading.Thread(target=work, daemon=True).start()

    def update_engine(self):
        self.task([YTDLP, "-U"], "下載引擎已是最新版。", "更新失敗，請確認網路，或稍後再試。")

    def download(self):
        url = self.url.get().strip()
        if not url:
            self.set_status("請先貼上 YouTube 網址。")
            return
        self.task(build_args(url, self.mode.get(), self.outdir.get()),
                  "下載完成！", "下載失敗：先按「修復 / 更新下載引擎」再試一次。")


if __name__ == "__main__":
    App().mainloop()
