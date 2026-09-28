# Polymarket BTC 5-Minute Trading Bot

> **v4.0.0** — Automated **UP/DOWN** bot for [Polymarket](https://polymarket.com) BTC 5-minute markets (`btc-updown-5m-*`).

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![v4.0.0](https://img.shields.io/badge/release-v4.0.0-green.svg)](https://github.com/dearolaf/Polymarket-BTC-5Minutes-Trading-Bot/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Uses Coinbase BTC price, 5m candles, and Polymarket CLOB book signals. **Practice first**, then go live.

### What's new in v4.0.0
- **Min-score filter** — weak predictor signals are skipped (not just logged)
- **Stake sync** — `MARKET_BUY_USD` drives martingale base stake
- **Premium presets** — `BOT_PLAN=premium` enables stricter defaults (0.55 min score, trend/candle filters)
- **Simulation fix** — practice mode logs to `log.txt` only (no random paper trades)
- **Test mode** in dashboard + improved auto-restart logging (`logs/runner.log`)

---

## Easy Mode (no coding)

| Step | Windows | Mac / Ubuntu |
|------|---------|--------------|
| Install | `Install.bat` | `./install.sh` |
| Dashboard | `Start.bat` | `./start.sh` |
| Run | **Setup** → keys → **Control** → **Start practice** | same |

- **Practice** = simulation · **Test mode** = faster scoring · **Live** = real USDC  
- Keys: **[Generate Keys](https://polymarkettool-272623624738.us-central1.run.app/)**

---

## Free vs Premium

| | **Free** | **Premium** |
|--|----------|-------------|
| Dashboard, practice/live | ✓ | ✓ |
| Min-score signal filter | ✓ (0.50 default) | ✓ (0.55 + trend/candle filters) |
| Performance analytics | — | ✓ |
| Advanced settings | — | ✓ |
| Log downloads | — | ✓ |

**Get Premium:** **[Premium Version](https://polymarkettool-272623624738.us-central1.run.app/premium)**  
Contact: [@dearolaf](https://t.me/dearolaf) · [WhatsApp](https://wa.me/13192101283) · xapple126@gmail.com  
After purchase: `BOT_PLAN=premium` in `.env`

---

## Terminal

```bash
git clone https://github.com/dearolaf/Polymarket-BTC-5Minutes-Trading-Bot.git
cd Polymarket-BTC-5Minutes-Trading-Bot
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt && cp .env.example .env
```

```bash
python 5m_bot_runner.py              # practice
python 5m_bot_runner.py --test-mode  # faster eval
python 5m_bot_runner.py --live       # real orders
pytest tests/                        # run v4 tests
```

---

## Key `.env` settings

| Variable | Default | Notes |
|----------|---------|-------|
| `MARKET_BUY_USD` | `10.0` | Base stake (synced to martingale) |
| `PREDICTOR_MIN_SCORE` | `0.50` | Skip trades below this \|score\| |
| `MARTINGALE_MAX_STAKE_USD` | `16` | Martingale cap |
| `BOT_PLAN` | `free` | Set `premium` after purchase |

See `.env.example` for the full list.

**Logs:** `log.txt` · `logs/orders.log` · `logs/runner.log`

---

## Disclaimer

**Trading involves significant risk.** Educational use only. Test in simulation before live. Only trade what you can afford to lose.

---

## Community

- **Premium:** [polymarkettool/premium](https://polymarkettool-272623624738.us-central1.run.app/premium)
- **Keys:** [Generate Keys](https://polymarkettool-272623624738.us-central1.run.app/)
- **Telegram:** [@dearolaf](https://t.me/dearolaf) · **Issues:** [GitHub](https://github.com/dearolaf/Polymarket-BTC-5Minutes-Trading-Bot/issues)

**Donate (USDT/USDC):** `0x60ef6388d63016a457e2bf880f34b4d4052d0ef5`
