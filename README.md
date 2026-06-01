# airwer

Word Error Rate for Air Traffic Control.

## Install

```bash
pip install airwer
```

## Usage

```python
import airwer

airwer.wer("descend flight level two five zero", "descend FL250")  # 0.0
airwer.wer("turn heading two one zero", "turn heading 220")        # > 0.0
```

## API

Each takes a single utterance (`str`) or a corpus (`Sequence[str]`), plus an
optional `WerConfig` to override the default `CANONICAL` profile.

| Function | What it scores |
| --- | --- |
| `wer(ref, hyp)` | Corpus Word Error Rate (the default metric) |
| `cer(ref, hyp)` | Character Error Rate |
| `numeric_wer(ref, hyp)` | WER over numbers only - safety-critical digits |
| `agreement(a, b)` | Symmetric `[0, 1]` overlap of two transcripts (`1` = identical), for model-vs-model voting |
| `ladder(ref, hyp)` | WER at each normalization rung, `raw` to `semantic` |
| `process(ref, hyp)` | Full `WerResult` - every metric plus per-utterance and distribution stats |

`normalize(text)` exposes the normalization step on its own. `WerConfig`, the
`profiles` presets, and the `vocab` term lists let you tune phraseology
handling.
