# SeamlessM4T Fine-Tuning for Ghanaian and West African Speech

## Dataset Reference

### Ghana ASR Dataset (2025)

A 2025 ScienceDirect research publication provides 5,000 hours of curated
speech data for Akan/Twi, Ewe, Dagbani, Dagaare, and Ikposo.

- Format: audio files (WAV, 16kHz mono) paired with text transcripts.
- Languages covered: Akan (Twi), Ewe, Dagbani, Dagaare, Ikposo.
- Domain: spontaneous speech, broadcast, read speech.
- Access: ScienceDirect data article, DOI to be linked when published
  (search ScienceDirect for "Ghana speech corpus 2025" or check
  https://www.sciencedirect.com/science/article/pii/S2352340925 for the
  relevant year's entry).

### Mozilla Common Voice - Twi

Community-contributed Twi recordings from Mozilla Common Voice.

Download:
```bash
# Install the Hugging Face datasets library
pip install datasets

python - <<'EOF'
from datasets import load_dataset
ds = load_dataset("mozilla-foundation/common_voice_16_0", "tw", split="train")
ds.save_to_disk("./data/common_voice_twi")
EOF
```

The Twi dataset is smaller than the Ghana ASR corpus but higher quality for
conversational speech. Use it for validation and to supplement training.

---

## Converting to SM4T Fine-Tuning Format

SeamlessM4T fine-tuning expects the fairseq S2T manifest format:

```
/path/to/audio/file1.wav\t<num_frames>\t<transcription text>
/path/to/audio/file2.wav\t<num_frames>\t<transcription text>
```

Conversion script sketch:

```python
import soundfile as sf
from pathlib import Path

def build_manifest(data_dir: str, output_tsv: str) -> None:
    rows = []
    for wav in Path(data_dir).rglob("*.wav"):
        info = sf.info(str(wav))
        frames = int(info.duration * info.samplerate)
        transcript = wav.with_suffix(".txt").read_text().strip()
        rows.append(f"{wav}\t{frames}\t{transcript}")
    Path(output_tsv).write_text("\n".join(rows))
```

---

## Fine-Tuning Steps

1. Prepare manifests for each language using the script above.
2. Convert audio to 16kHz WAV mono if not already in that format.
3. Follow the seamless_communication fine-tuning guide at:
   https://github.com/facebookresearch/seamless_communication/tree/main/docs/m4t
4. Launch training with the SM4T S2T configuration:
   ```bash
   python -m fairseq_cli.train \
     --task speech_to_text \
     --arch seamless_m4t_v2_large \
     --finetune-from-model seamlessM4T_v2_large \
     --lang-pairs twi-eng,ewe-eng,dik-eng \
     ...
   ```
5. Save the fine-tuned checkpoint.

---

## Swapping the Fine-Tuned Model into the Sidecar

The sidecar selects the model via the `SM4T_MODEL` environment variable.
Replace the default with your checkpoint path:

```yaml
# docker-compose.localization.yml
services:
  seamless-m4t:
    environment:
      - MODEL=/models/seamlessM4T_ghana_finetuned
    volumes:
      - /path/to/checkpoints:/models
```

No keprix code changes needed. The sidecar loads whatever model the variable
points to.

---

## Expected Accuracy After Fine-Tuning

Based on comparable fine-tuning experiments on low-resource African languages:

- Twi/Akan: WER improvement of 15-25 percentage points over base model.
- Ewe: 10-20 percentage points.
- Dagbani: 20-30 percentage points (lower base model coverage).

Fine-tuning on borehole domain speech (pump names, geological terms,
maintenance procedures) provides an additional 5-10 percentage point gain
for domain-specific transcription.
