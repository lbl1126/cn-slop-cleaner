# cn-slop-cleaner

给 humanizer 和 stop-slop 加的本地检查器。上游是给对话模型看的英文说明，这里把它变成 Windows 上能跑的命令，并加上中文套话。

英文短语在 `third_party/stop-slop/phrases.md`，版权归 Hardik Pandya，MIT。中文规则在 `cn_patterns.json`。结构检查覆盖 humanizer 里最常见的一种句式：先否定再转折（「不是……而是……」以及英文 not X but Y）。humanizer 版权归 Siqi Chen，MIT。

```text
python cn_clean.py samples/sample_zh.txt
python cn_clean.py --self-test
```

它只标出句子，不改写，也不发明事实。

许可证见 `NOTICE.md`。
