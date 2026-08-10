# Polymarket BTC 5-Minute Trading Bot

> Automated **UP/DOWN** bot for [Polymarket](https://polymarket.com) BTC 5-minute markets (`btc-updown-5m-*`). Paper trade first, go live when ready.

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Predicts whether BTC goes **up or down** each 5-minute window using Coinbase price data, 5m candles, and Polymarket CLOB order-book signals.

---

## Easy Mode (no coding)

| Step | Windows | Mac / Ubuntu |
|------|---------|--------------|
| **Install** | `Install.bat` | `chmod +x install.sh start.sh && ./install.sh` |
| **Open dashboard** | `Start.bat` | `./start.sh` |
| **Run** | **Setup** → paste keys → **Control** → **Start practice** | same |

- **Practice** = simulation (no real money) · **Live** = real USDC orders  
- API keys: **[Generate Keys](https://polymarkettool-272623624738.us-central1.run.app/)** (one click)

---

## Free vs Premium

| | **Free** (this repo) | **Premium** |
|--|----------------------|-------------|
| Dashboard, practice/live, API setup | ✓ | ✓ |
| Standard predictor (defaults) | ✓ | Enhanced ensemble + tuning |
| Performance charts & analytics | — | ✓ |
| Advanced settings (martingale, timing) | — | ✓ |
| Log downloads | — | ✓ |
| Priority support | — | ✓ |

**Get Premium:** **[Premium Version](https://polymarkettool-272623624738.us-central1.run.app/premium)**

Contact: [@dearolaf](https://t.me/dearolaf) · [WhatsApp +1 319 210 1283](https://wa.me/13192101283) · [xapple126@gmail.com](mailto:xapple126@gmail.com)

After purchase, add to `.env`: `BOT_PLAN=premium`

---

## Terminal (developers)

**Requires:** Python 3.14+, Git, Polymarket API credentials, USDC on Polygon for live.

```bash
git clone https://github.com/dearolaf/Polymarket-BTC-5Minutes-Trading-Bot.git
cd Polymarket-BTC-5Minutes-Trading-Bot
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in credentials
```

```bash
python 5m_bot_runner.py           # simulation (default)
python 5m_bot_runner.py --live    # real orders
python 5m_bot_runner.py --test-mode   # faster eval for testing
```

| Flag | Effect |
|------|--------|
| `--live` | Real Polymarket orders |
| `--test-mode` | Simulation with faster scoring |
| `--verbose` | Full debug logs |

---

## Key settings (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `POLYMARKET_PK` | — | Wallet private key |
| `POLYMARKET_API_KEY/SECRET/PASSPHRASE` | — | CLOB API credentials |
| `USE_LIGHTWEIGHT_PREDICTOR` | `1` | Enable predictor |
| `MARKET_BUY_USD` | `10.0` | USD per trade |
| `MARTINGALE_BASE_USD` | `1` | Base stake after win |
| `MARTINGALE_MAX_STAKE_USD` | `16` | Max martingale stake |
| `POLYMARKET_AUTO_REDEEM` | `1` | Auto-redeem winners |

Full list: see `.env.example`.

**Logs:** `log.txt` (trade summary) · `logs/orders.log` (detail) · `python view_paper_trades.py`

---

## FAQ

**How much to start?** Default $10/trade. Keep extra USDC for gas and martingale.

**Binance/Bybit bot?** No — this trades **Polymarket prediction markets**, not exchange spot.

**24/7?** Yes — `5m_bot_runner.py` auto-restarts on crash.

**Profitable?** No guarantee. Always test in practice mode first.

---

## Disclaimer

**Trading involves significant risk of loss.** Educational use only. Test in simulation before live. Only trade what you can afford to lose.

---

## Community & donate

- **Premium:** [polymarkettool/premium](https://polymarkettool-272623624738.us-central1.run.app/premium)
- **Keys tool:** [Generate Keys](https://polymarkettool-272623624738.us-central1.run.app/)
- **Telegram:** [@dearolaf](https://t.me/dearolaf) · **WhatsApp:** [+1 319 210 1283](https://wa.me/13192101283) · **Email:** xapple126@gmail.com
- **Issues:** [GitHub Issues](https://github.com/dearolaf/Polymarket-BTC-5Minutes-Trading-Bot/issues)

**Donate (USDT/USDC):** `0x60ef6388d63016a457e2bf880f34b4d4052d0ef5` (ERC-20 & BEP-20)

Built with [NautilusTrader](https://nautilustrader.io/) · [Polymarket](https://polymarket.com/)

<!--
GitHub About:
Description: BTC 5-minute trading bot for Polymarket — paper + live mode, Easy Mode dashboard, Coinbase signals.
Topics: polymarket, bitcoin, btc, trading-bot, crypto-bot, algorithmic-trading, 5-minute-trading, prediction-markets
-->
