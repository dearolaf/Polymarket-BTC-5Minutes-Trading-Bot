"""
Polymarket BTC 5-Min Bot — Easy web dashboard (no coding required).
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from easy_app.config import (
    ENV_PATH,
    GENERATE_KEYS_URL,
    PROJECT_ROOT,
    credentials_complete,
    ensure_env_file,
    load_env,
    save_env,
    tail_file,
)
from easy_app.process import get_status, start_bot, stop_bot

st.set_page_config(
    page_title="Polymarket BTC Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

STATUS = get_status()


def refresh() -> None:
    st.rerun()


with st.sidebar:
    st.title("BTC 5-Min Bot")
    st.caption("Easy mode — no coding required")
    st.divider()

    if STATUS.get("running"):
        st.success(f"● Running — {STATUS.get('mode_label', 'Running')}")
        st.caption(f"Process ID: {STATUS.get('pid')}")
    else:
        st.info("● Stopped")

    if credentials_complete():
        st.success("API keys saved")
    else:
        st.warning("Complete setup first")

    st.divider()
    page = st.radio(
        "Menu",
        ["Control panel", "Setup keys", "Activity log", "Help"],
        label_visibility="collapsed",
    )


if page == "Control panel":
    st.header("Control panel")
    st.write(
        "Use **Practice mode** first (no real money). When you are ready, switch to **Live trading**."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("▶ Start practice", use_container_width=True, disabled=STATUS.get("running")):
            if not credentials_complete():
                st.error("Go to **Setup keys** and save your Polymarket credentials first.")
            else:
                try:
                    start_bot(live=False)
                    st.success("Practice mode started.")
                    refresh()
                except Exception as exc:
                    st.error(str(exc))

    with c2:
        if st.button("▶ Start live", use_container_width=True, disabled=STATUS.get("running")):
            if not credentials_complete():
                st.error("Go to **Setup keys** and save your Polymarket credentials first.")
            else:
                st.session_state["confirm_live"] = True

    with c3:
        if st.button("■ Stop bot", use_container_width=True, disabled=not STATUS.get("running")):
            stop_bot()
            st.success("Bot stopped.")
            refresh()

    if st.session_state.get("confirm_live"):
        st.error("**Live trading uses real money.** Only continue if your wallet is funded and keys are correct.")
        y, n = st.columns(2)
        with y:
            if st.button("Yes — start live trading", type="primary"):
                try:
                    start_bot(live=True)
                    st.session_state.pop("confirm_live", None)
                    st.success("Live trading started.")
                    refresh()
                except Exception as exc:
                    st.error(str(exc))
        with n:
            if st.button("Cancel"):
                st.session_state.pop("confirm_live", None)
                refresh()

    st.divider()
    st.subheader("Recent trades (summary)")
    st.code(tail_file(PROJECT_ROOT / "log.txt", max_lines=25), language=None)


elif page == "Setup keys":
    st.header("Setup your Polymarket keys")
    st.markdown(
        "If you are not sure how to generate keys, use the tool below. "
        "You can generate keys easily with one click."
    )
    st.link_button("Generate Keys", GENERATE_KEYS_URL, use_container_width=False)

    st.info(
        "**Email / Google login:** use Polymarket **Reveal Private Key** "
        "([Magic export](https://reveal.magic.link/polymarket)). "
        "**MetaMask:** export your wallet private key from the wallet app."
    )

    ensure_env_file()
    env = load_env()

    with st.form("setup_form"):
        pk = st.text_input(
            "Wallet private key (POLYMARKET_PK)",
            value=env.get("POLYMARKET_PK", ""),
            type="password",
        )
        api_key = st.text_input(
            "API key (POLYMARKET_API_KEY)",
            value=env.get("POLYMARKET_API_KEY", ""),
            type="password",
        )
        api_secret = st.text_input(
            "API secret (POLYMARKET_API_SECRET)",
            value=env.get("POLYMARKET_API_SECRET", ""),
            type="password",
        )
        passphrase = st.text_input(
            "Passphrase (POLYMARKET_PASSPHRASE)",
            value=env.get("POLYMARKET_PASSPHRASE", ""),
            type="password",
        )
        funder = st.text_input(
            "Proxy wallet address (optional)",
            value=env.get("POLYMARKET_FUNDER", ""),
        )

        st.divider()
        st.subheader("Trading settings (simple)")

        trade_usd = st.number_input(
            "Amount per trade (USD)",
            min_value=1.0,
            max_value=100.0,
            value=float(env.get("MARKET_BUY_USD") or "1.0"),
            step=1.0,
        )
        predictor_on = st.checkbox(
            "Use smart predictor (recommended)",
            value=(env.get("USE_LIGHTWEIGHT_PREDICTOR", "1") == "1"),
        )

        saved = st.form_submit_button("Save settings", type="primary", use_container_width=True)

    if saved:
        save_env(
            {
                "POLYMARKET_PK": pk.strip(),
                "POLYMARKET_API_KEY": api_key.strip(),
                "POLYMARKET_API_SECRET": api_secret.strip(),
                "POLYMARKET_PASSPHRASE": passphrase.strip(),
                "POLYMARKET_FUNDER": funder.strip(),
                "MARKET_BUY_USD": f"{trade_usd:.2f}",
                "USE_LIGHTWEIGHT_PREDICTOR": "1" if predictor_on else "0",
            }
        )
        st.success(f"Saved to `{ENV_PATH.name}`. You can start the bot from the Control panel.")
        refresh()

    st.caption("Your keys are stored only in `.env` on your computer — never share this file.")


elif page == "Activity log":
    st.header("Activity log")

    tab1, tab2 = st.tabs(["Trade summary (log.txt)", "Order detail (logs/orders.log)"])

    with tab1:
        st.code(tail_file(PROJECT_ROOT / "log.txt", max_lines=100), language=None)

    with tab2:
        st.code(tail_file(PROJECT_ROOT / "logs" / "orders.log", max_lines=100), language=None)

    if st.button("Refresh logs"):
        refresh()


else:
    st.header("Help")
    st.markdown(
        """
        ### Quick steps (no coding)

        1. **Install once**
           - Windows: double-click `Install.bat`
           - Mac / Ubuntu: `chmod +x install.sh start.sh` then `./install.sh`
        2. **Start the app**
           - Windows: double-click `Start.bat`
           - Mac / Ubuntu: `./start.sh`
        3. **Setup keys** → **Generate Keys** → paste values → **Save settings**
        4. **Control panel** → **Start practice** (simulation)
        5. When ready → **Start live** (real money)

        ### Advanced (terminal)

        ```bash
        python 5m_bot_runner.py           # practice
        python 5m_bot_runner.py --live    # live
        ```

        ### Support

        - GitHub Issues
        - Telegram: [@dearolaf](https://t.me/dearolaf)

        **Risk warning:** Trading involves loss. Start in practice mode.
        """
    )
