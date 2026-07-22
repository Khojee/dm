# Us, in Data — Private Conversation Analytics

A local pipeline that parses Telegram + Instagram/Threads chat exports, computes
dozens of statistics with pandas, and generates an encrypted, premium-looking
static dashboard you can host on GitHub Pages.

## How it works

```
data/                      ← raw exports (never published)
  telegram/…/result.json
  instagram/…/your_instagram_activity/messages/…

chat-analyzer/
  parsers/                 ← auto-detect & parse export formats
  analytics/               ← activity, response times, emoji, words,
                             media, sentiment, timeline, awards, insights, recap
  dashboard/               ← the static web app (Tailwind + Plotly)
  crypto_util.py           ← AES-256-GCM encryption of the payload
  main.py                  ← one-command build
  output/                  ← the generated site (deploy this folder)
```

The analytics payload is **gzipped and encrypted at build time**
(AES-256-GCM, key derived from the passphrase with PBKDF2-SHA256 / 250k
iterations). The static site ships only ciphertext; decryption happens in the
browser via the Web Crypto API after the correct passphrase is entered.
No plaintext conversation data is ever in the published files.

## Usage

```bash
pip install -r requirements.txt
python main.py
```

Then open `output/index.html` (serve it, e.g. `python -m http.server -d output`)
and enter the passphrase.

## Configuration — `config.json`

| Key | Meaning |
|-----|---------|
| `data_dir` | Where to search (recursively) for exports |
| `passphrase` | The secret used to encrypt/unlock the dashboard |
| `participants` | Display names + all aliases used across platforms |
| `session_gap_minutes` | Gap that splits messages into conversation sessions |

## Deploying to GitHub Pages

Push the contents of `output/` to a `gh-pages` branch (or `/docs`). Do **not**
commit the `data/` folder. The passphrase is not stored anywhere in the output —
only a ciphertext that can be opened with it.

## Notes

- Parsers search recursively and support multiple JSON files per thread; no
  file names are hardcoded.
- Instagram's mojibake (latin-1-encoded UTF-8) is repaired automatically.
- Threads-app DMs are detected heuristically and labeled as their own platform.
- All insights and awards are template-generated from real numbers — nothing
  is fabricated.
