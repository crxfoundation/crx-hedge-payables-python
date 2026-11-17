# CRX payables hedge: Python

A US importer owes a BRL invoice in 30 days and an MXN invoice in 60 days.
This script requests CRX quotes for non-deliverable forwards (NDFs) that sell USD forward against each currency, and books them on request.
It uses the [CRX Python SDK](https://github.com/crxfoundation/crx-python). Margin and settlement are in USDC.

## Install

Python 3.10 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run read-only

No key needed. The script reads `GET /health` and `GET /markets`, then prints each quote request without sending it.

```bash
python hedge.py
```

Sample output: [RUN.txt](RUN.txt).

## Run with keys

Set `CRX_WALLET_PK` to the private key of an onboarded CRX account wallet, or `CRX_WALLET_PK_FILE` to a file that holds it. The account needs free USDC collateral for the margin.

```bash
export CRX_WALLET_PK_FILE=wallet.key
python hedge.py --quote    # request a quote for each invoice; books nothing
python hedge.py --accept   # request a quote for each invoice and book it
```

`--accept` books live trades. To change the invoices, edit `PAYABLES` in `hedge.py`. The notional is in USD, at least 100 USD. Pairs: USD/BRL and USD/MXN.

## Links

- [NDFs on CRX](https://crxfx.com/ndf)
- [Pricing](https://crxfx.com/pricing)
- [API reference (OpenAPI)](https://discover.crxfx.com/openapi-taker.yaml)

## License

Use only to access CRX services. See [LICENSE](LICENSE).
