"""Hedge a US importer's BRL and MXN payables with CRX NDFs, through the CRX Python SDK.

The default run is read-only. --quote requests quotes; --accept requests quotes and books them.
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import crx

CHAIN = "ethereum"
MIN_USD = 100
SIDE = "sell"  # sell USD forward, receive the invoice currency at a fixed rate
WAIT_S = 300
# The importer's payables. "usd" is the notional in USD, the base currency of each pair.
PAYABLES = [
    {"pair": "USD/BRL", "usd": 25_000, "days": 30, "what": "BRL invoice, Sao Paulo supplier"},
    {"pair": "USD/MXN", "usd": 10_000, "days": 60, "what": "MXN invoice, Monterrey supplier"},
]


def say(label: str, text: str) -> None:
    print(f"{label:<15}{text}", flush=True)


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def settles(days: int) -> datetime:
    """16:00 UTC on the due day, moved to Monday when the due day falls on a weekend."""
    t = (datetime.now(timezone.utc) + timedelta(days=days)).replace(hour=16, minute=0, second=0, microsecond=0)
    while t.weekday() >= 5:
        t += timedelta(days=1)
    return t


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--quote", action="store_true", help="request a quote for each payable; book nothing")
    mode.add_argument("--accept", action="store_true", help="request a quote for each payable and book it")
    args = ap.parse_args()
    run = "accept" if args.accept else "quote" if args.quote else "read-only"
    say("CRX", f"payables hedge: {run}")

    if run == "read-only":  # an empty name in the environment keeps the SDK from loading a key
        os.environ.update(CRX_WALLET_PK="", CRX_WALLET_PK_FILE="")
    try:
        c = crx.Client(network="mainnet", allow_mainnet=True)  # the key comes from CRX_WALLET_PK or CRX_WALLET_PK_FILE
    except crx.CrxError as e:
        say("Error", f"{e.code}: {e}")
        return 2
    try:
        h = c.health()
        chain = next(x for x in h["chains"] if x["key"] == CHAIN)
        say("GET /health", f"{h['status']}, healthy {str(h.get('healthy') is True).lower()}, chain {chain['key']} "
                           f"{chain['chain_id']}, core {chain['core']}")
        markets = {m.pair: m for m in c.markets()}
    except (crx.CrxError, StopIteration, KeyError) as e:
        say("Error", f"{getattr(e, 'code', 'bad_answer')}: {e}")
        return 1
    for p in PAYABLES:
        m = markets.get(p["pair"])
        if m is None or m.paused:
            say("GET /markets", f"{p['pair']} not offered")
            continue
        state = "open" if m.open else f"closed, opens {iso(m.next_open)}" if m.next_open else "closed"
        say("GET /markets", f"{m.pair} {state}, notional {m.min_notional} to {m.max_notional} USD")

    if run != "read-only" and c.address is None:
        say("Error", "config: set CRX_WALLET_PK or CRX_WALLET_PK_FILE to the account wallet key")
        return 2
    quotes = trades = errors = 0
    for p in PAYABLES:
        say("Payable", f"{p['pair']} {p['usd']} USD due in {p['days']} d, {p['what']}")
        if p["usd"] < MIN_USD:
            say("Error", f"below_min: the notional is under {MIN_USD} USD")
            errors += 1
            continue
        when = settles(p["days"])
        terms = f"{SIDE} {p['usd']} {p['pair']}, settles {iso(when)}"
        if run == "read-only":
            say("POST /rfqs", f"{terms}, not sent")
            continue
        say("POST /rfqs", terms)
        try:
            q = c.quote(p["pair"], SIDE, p["usd"], settles=when)
            quotes += 1
            accept_by = iso(q.closes_at) if q.closes_at else "-"
            say("Quote", f"{q.rate} {q.pair[4:]} per USD, accept by {accept_by}")
            if run == "accept":
                t = c.accept(q, wait=WAIT_S)
                extra = ", provisional" if t.provisional else ", final" if t.final else ""
                say("Trade", f"{t.status}{extra}")
                trades += t.status == "open"
        except crx.CrxError as e:
            say("Error", f"{e.code}: {e}")
            errors += 1
    if run == "read-only":
        say("Done", "read-only, nothing sent. Set CRX_WALLET_PK, then run with --quote or --accept.")
    else:
        say("Done", f"quotes {quotes}, trades {trades}, errors {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
