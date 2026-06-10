"""
Gasless redemption of resolved Polymarket positions via the official builder relayer
(py_builder_relayer_client). Requires Builder API credentials (not the same as CLOB L2 keys).


Env:
  POLYMARKET_AUTO_REDEEM=1          Enable background loop (bot live mode only).
  POLYMARKET_AUTO_REDEEM_INTERVAL_SEC=300
  POLYMARKET_AUTO_REDEEM_MAX_TX=25  Max redeem txs per relayer batch.
  POLYMARKET_AUTO_REDEEM_DRY_RUN=1  Log actions only; do not submit.
  POLYMARKET_RELAYER_URL=https://relayer-v2.polymarket.com
  POLYMARKET_CHAIN_ID=137
  POLYMARKET_OUTCOME_DECIMALS=6     Raw token amount = size * 10**decimals (neg-risk path).


  POLYMARKET_PK                     Same EOA as trading (relayer signs Safe txs).
  POLYMARKET_FUNDER                 Proxy/profile address for Data API `user` (if unset, EOA).


  POLYMARKET_BUILDER_API_KEY        Builder signing credentials
  POLYMARKET_BUILDER_SECRET
  POLYMARKET_BUILDER_PASSPHRASE
  (fallback names: BUILDER_API_KEY, BUILDER_SECRET, BUILDER_PASS_PHRASE)
"""
from __future__ import annotations


import os
import threading
import time
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple


import httpx
from eth_abi import encode as abi_encode
from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3


try:
    from py_builder_relayer_client.client import RelayClient
    from py_builder_relayer_client.models import OperationType, SafeTransaction
    from py_builder_signing_sdk.config import BuilderConfig
    from py_builder_signing_sdk.sdk_types import BuilderApiKeyCreds
except ImportError:  # pragma: no cover
    RelayClient = None  # type: ignore
    OperationType = None  # type: ignore
    SafeTransaction = None  # type: ignore
    BuilderConfig = None  # type: ignore
    BuilderApiKeyCreds = None  # type: ignore


DATA_API_POSITIONS = "https://data-api.polymarket.com/positions"


# Polygon mainnet (Polymarket)
USDC_POLYGON = to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
CTF_POLYGON = to_checksum_address("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045")
NEG_RISK_ADAPTER = to_checksum_address("0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296")


ZERO_BYTES32 = bytes(32)




def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")




def _wallet_for_data_api() -> str:
    from eth_account import Account


    funder = (os.getenv("POLYMARKET_FUNDER") or "").strip()
    if funder:
        return to_checksum_address(funder)
    pk = (os.getenv("POLYMARKET_PK") or "").strip()
    if not pk:
        raise ValueError("POLYMARKET_FUNDER or POLYMARKET_PK is required for auto-redeem")
    return Account.from_key(pk).address




def _builder_config() -> Optional[Any]:
    key = (
        os.getenv("POLYMARKET_BUILDER_API_KEY")
        or os.getenv("BUILDER_API_KEY")
        or ""
    ).strip()
    secret = (
        os.getenv("POLYMARKET_BUILDER_SECRET")
        or os.getenv("BUILDER_SECRET")
        or ""
    ).strip()
    passphrase = (
        os.getenv("POLYMARKET_BUILDER_PASSPHRASE")
        or os.getenv("BUILDER_PASS_PHRASE")
        or os.getenv("BUILDER_PASSPHRASE")
        or ""
    ).strip()
    if not (key and secret and passphrase):
        return None
    return BuilderConfig(
        local_builder_creds=BuilderApiKeyCreds(
            key=key,
            secret=secret,
            passphrase=passphrase,
        )
    )




def _outcome_decimals() -> int:
    try:
        return max(0, min(36, int(os.getenv("POLYMARKET_OUTCOME_DECIMALS", "6"))))
    except ValueError:
        return 6




def _to_raw_amount(size: float) -> int:
    d = _outcome_decimals()
    try:
        raw = int(Decimal(str(size)) * (Decimal(10) ** d))
    except (InvalidOperation, ValueError):
        return 0
    return max(0, raw)




def _outcome_index_from_position(p: Dict[str, Any]) -> int:
    oi = p.get("outcomeIndex")
    if oi is not None:
        try:
            v = int(oi)
            if v in (0, 1):
                return v
        except (TypeError, ValueError):
            pass
    out = (p.get("outcome") or "").strip().lower()
    if out in ("yes", "up", "y", "long"):
        return 0
    if out in ("no", "down", "n", "short"):
        return 1
    return 0




def _ctf_redeem_calldata(condition_id_hex: str) -> str:
    """redeemPositions(address,bytes32,bytes32,uint256[]) on CTF core."""
    cid = condition_id_hex.lower()
    if not cid.startswith("0x") or len(cid) != 66:
        raise ValueError(f"invalid conditionId: {condition_id_hex!r}")
    cond_bytes = bytes.fromhex(cid[2:])
    body = abi_encode(
        ["address", "bytes32", "bytes32", "uint256[]"],
        [USDC_POLYGON, ZERO_BYTES32, cond_bytes, [1, 2]],
    )
    sel = Web3.keccak(
        text="redeemPositions(address,bytes32,bytes32,uint256[])"
    )[:4]
    return Web3.to_hex(sel + body)




def _neg_risk_redeem_calldata(condition_id_hex: str, amounts: Tuple[int, int]) -> str:
    """redeemPositions(bytes32,uint256[]) on neg-risk adapter."""
    cid = condition_id_hex.lower()
    if not cid.startswith("0x") or len(cid) != 66:
        raise ValueError(f"invalid conditionId: {condition_id_hex!r}")
    cond_bytes = bytes.fromhex(cid[2:])
    body = abi_encode(
        ["bytes32", "uint256[]"],
        [cond_bytes, [amounts[0], amounts[1]]],
    )
    sel = Web3.keccak(text="redeemPositions(bytes32,uint256[])")[:4]
    return Web3.to_hex(sel + body)




def fetch_redeemable_positions(user: str, timeout: float = 30.0) -> List[Dict[str, Any]]:
    params = {
        "user": user,
        "redeemable": "true",
        "limit": 500,
        "offset": 0,
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.get(DATA_API_POSITIONS, params=params)
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, list):
        return []
    return data




def _build_safe_transactions(positions: List[Dict[str, Any]]) -> List[SafeTransaction]:
    standard: set = set()
    neg_amounts: Dict[str, List[int]] = defaultdict(lambda: [0, 0])


    for p in positions:
        if not p.get("redeemable"):
            continue
        cid = p.get("conditionId")
        if not cid or not isinstance(cid, str):
            continue
        try:
            sz = float(p.get("size") or 0)
        except (TypeError, ValueError):
            continue
        if sz <= 0:
            continue


        if p.get("negativeRisk"):
            idx = _outcome_index_from_position(p)
            raw = _to_raw_amount(sz)
            neg_amounts[cid][idx] += raw
        else:
            standard.add(cid)


    txs: List[SafeTransaction] = []
    for cid in sorted(standard):
        txs.append(
            SafeTransaction(
                to=CTF_POLYGON,
                operation=OperationType.Call,
                data=_ctf_redeem_calldata(cid),
                value="0",
            )
        )
    for cid in sorted(neg_amounts.keys()):
        a0, a1 = neg_amounts[cid]
        if a0 == 0 and a1 == 0:
            continue
        txs.append(
            SafeTransaction(
                to=NEG_RISK_ADAPTER,
                operation=OperationType.Call,
                data=_neg_risk_redeem_calldata(cid, (a0, a1)),
                value="0",
            )
        )
    return txs




def redeem_once() -> bool:
    """
    Fetch redeemable positions and submit relayer redeem batch.
    Returns True if a relayer batch was submitted (or dry-run would submit).
    """
    if RelayClient is None:
        logger.warning("py_builder_relayer_client not installed — skip auto-redeem")
        return False


    dry = _truthy("POLYMARKET_AUTO_REDEEM_DRY_RUN")
    pk = (os.getenv("POLYMARKET_PK") or "").strip()
    if not pk:
        logger.warning("POLYMARKET_PK missing — cannot run auto-redeem")
        return False


    bcfg = _builder_config()
    if bcfg is None and not dry:
        logger.warning(
            "Builder API credentials missing — set POLYMARKET_BUILDER_API_KEY/SECRET/PASSPHRASE "
            "(or BUILDER_API_KEY/SECRET/BUILDER_PASS_PHRASE). Dry-run only without them."
        )
        return False


    user = _wallet_for_data_api()
    try:
        positions = fetch_redeemable_positions(user)
    except Exception as e:
        logger.warning(f"auto-redeem: Data API positions failed: {e}")
        return False


    txs = _build_safe_transactions(positions)
    try:
        cap = int(os.getenv("POLYMARKET_AUTO_REDEEM_MAX_TX", "25"))
    except ValueError:
        cap = 25
    cap = max(1, min(100, cap))
    if len(txs) > cap:
        logger.info(f"auto-redeem: capping batch {len(txs)} -> {cap} txs")
        txs = txs[:cap]


    if not txs:
        logger.debug("auto-redeem: no redeemable positions with non-zero size")
        return False


    logger.info(
        f"auto-redeem: submitting {len(txs)} redeem tx(s) for proxy/user {user} "
        f"(dry_run={dry})"
    )
    if dry:
        return True


    relayer_url = (
        os.getenv("POLYMARKET_RELAYER_URL") or "https://relayer-v2.polymarket.com"
    ).rstrip("/")
    try:
        chain_id = int(os.getenv("POLYMARKET_CHAIN_ID", "137"))
    except ValueError:
        chain_id = 137


    client = RelayClient(relayer_url, chain_id, private_key=pk, builder_config=bcfg)
    try:
        resp = client.execute(txs, metadata="redeem")
    except Exception as e:
        logger.error(f"auto-redeem: relayer execute failed: {e}")
        return False


    tx_id = getattr(resp, "transaction_id", None)
    logger.info(f"auto-redeem: relayer tx id {tx_id!r} (waiting for terminal state)")
    try:
        final = resp.wait()
    except Exception as e:
        logger.warning(f"auto-redeem: wait() ended with {e}")
        final = None
    if final:
        logger.info(f"auto-redeem: relayer state {final.get('state')!r} hash={final.get('transactionHash')!r}")
    return True




def _loop(stop: threading.Event) -> None:
    try:
        interval = float(os.getenv("POLYMARKET_AUTO_REDEEM_INTERVAL_SEC", "300"))
    except ValueError:
        interval = 300.0
    interval = max(60.0, min(86400.0, interval))


    logger.info(
        f"auto-redeem thread started (interval {interval:.0f}s). "
        "Requires Builder API creds + deployed Safe; see execution/polymarket_auto_redeem.py docstring."
    )
    while not stop.is_set():
        try:
            redeem_once()
        except Exception as e:
            logger.exception(f"auto-redeem loop error: {e}")
        if stop.wait(interval):
            break
    logger.info("auto-redeem thread stopped")




def start_auto_redeem_thread(stop: threading.Event) -> threading.Thread:
    t = threading.Thread(target=_loop, args=(stop,), name="PolymarketAutoRedeem", daemon=True)
    t.start()
    return t




