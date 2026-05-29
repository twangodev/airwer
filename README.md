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
