import os
from app import PERCENT, build_args

v = build_args("https://youtu.be/x", "video", "out")
assert "--merge-output-format" in v and "mp4" in v and "-x" not in v
assert v[-1] == "https://youtu.be/x" and os.path.join("out", "%(title)s.%(ext)s") in v
a = build_args("https://youtu.be/x", "audio", "out")
assert "-x" in a and "mp3" in a and "320K" in a and "--merge-output-format" not in a
assert PERCENT.search("[download]  42.5% of 10MiB").group(1) == "42.5"
print("ok")
