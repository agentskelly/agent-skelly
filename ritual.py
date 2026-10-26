#!/usr/bin/env python3
"""RITUAL agent CLI — fetch signed vouchers from the backend and emit ready-to-send transactions.

The backend only SIGNS; your wallet broadcasts. Nothing here ever touches a private key.

  python3 ritual.py mint   --wallet 0x..
  python3 ritual.py ritual --wallet 0x.. --potions 1234,5678,9012,3456

Each command prints a JSON object with the transaction(s) to broadcast. On any failure it prints
{"error": "..."} to stderr and exits non-zero, so an agent can parse the outcome either way.

Safety model: the backend may SIGN a voucher, but it can NEVER redirect your funds. The contract
addresses are pinned below (and in config.json); a voucher that points anywhere else is refused.
The ritual approves ONLY the 4 potions being burned (never setApprovalForAll), and mint/fee values
above a hard cap are refused. Simulate with your wallet before broadcasting if you want belt + braces.

Environment:
  RITUAL_API   API base (default https://agent-skelly.fun/api)
"""
import os, sys, json, re, argparse, urllib.request, urllib.error

try:
    from eth_abi import encode
    from eth_utils import keccak
except ImportError:
    sys.exit('error: missing dependencies. Run: pip install eth-abi eth-utils')

API = os.environ.get("RITUAL_API", "https://agent-skelly.fun/api").rstrip("/")
_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")

# The ONLY contracts this skill will ever target (BNB Smart Chain, chainId 56).
# config.json may override these, but a backend RESPONSE can never redirect to another address.
KNOWN = {
    "potion": "0x0Eb88f1b5Eb66264069f5B60D58886Ffa684Fd2C",  # PotionNFT
    "burner": "0x6dE9915c9c4c471aD8D39a248C1DE58B86c6B0Ce",  # RitualBurner
}
# Hard safety caps. Mint is free (price 0); the ritual fee is ~1.5 USD in BNB. These caps
# sit far above that so price swings pass, but a malicious/overpriced voucher is refused.
MAX_MINT_WEI = 5 * 10**15   # 0.005 BNB
MAX_FEE_WEI  = 5 * 10**16   # 0.05 BNB


def _die(msg):
    """Emit a machine-parseable error and exit non-zero."""
    print(json.dumps({"error": str(msg)}), file=sys.stderr)
    sys.exit(1)


def _check_wallet(w):
    if not _ADDR_RE.match(w or ""):
        _die(f"invalid --wallet address: {w!r} (expected 0x + 40 hex chars)")
    return w


def _get(path):
    req = urllib.request.Request(API + path, headers={"Accept": "application/json", "User-Agent": "ritual-skill"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        _die(f"API {e.code} on GET {path}: {e.read()[:200].decode('utf-8', 'replace')}")
    except Exception as e:
        _die(f"cannot reach API ({API}): {e}")


def _post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "ritual-skill"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        _die(f"API {e.code} on POST {path}: {e.read()[:200].decode('utf-8', 'replace')}")
    except Exception as e:
        _die(f"cannot reach API ({API}): {e}")


def _sel(sig):
    return keccak(sig.encode())[:4]


def _addrs():
    """Resolve the contract addresses the skill will target: config.json overrides the pinned
    KNOWN defaults. The backend is NEVER trusted to supply a transaction target."""
    cfg = {}
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(p):
        try:
            cfg = json.load(open(p))
        except Exception:
            cfg = {}
    potion = (cfg.get("potion") or KNOWN["potion"])
    burner = (cfg.get("burner") or KNOWN["burner"])
    if not _ADDR_RE.match(potion) or not _ADDR_RE.match(burner):
        _die("could not resolve pinned contract addresses (check config.json)")
    return {"potion": potion, "burner": burner}


def cmd_mint(wallet):
    _check_wallet(wallet)
    potion = _addrs()["potion"]
    v = _get(f"/mint-voucher?wallet={wallet}")
    if v.get("error"):
        _die("backend: " + v["error"])
    # SAFETY: the backend signs a voucher, it does NOT get to choose where your BNB goes.
    if (v.get("contract") or "").lower() != potion.lower():
        _die(f"backend returned an unexpected contract {v.get('contract')!r} (pinned {potion}); refusing")
    price = int(v["priceWei"])
    if price > MAX_MINT_WEI:
        _die(f"mint price {price} wei exceeds the safety cap {MAX_MINT_WEI} wei; refusing")
    data = _sel("mintWithVoucher(uint256,uint256,bytes)") + encode(
        ["uint256", "uint256", "bytes"],
        [int(v["nonce"]), int(v["deadline"]), bytes.fromhex(v["signature"][2:])])
    tx = {"to": potion, "data": "0x" + data.hex(), "value": str(price)}
    print(json.dumps({"action": "mint", "tx": tx,
                      "note": "Broadcast this payable tx from your wallet to mint a Potion."}, indent=2))


def cmd_ritual(wallet, potions):
    _check_wallet(wallet)
    ids = [int(x) for x in potions.split(",") if x.strip()] if potions else []
    if len(ids) != 4 or len(set(ids)) != 4:
        _die("need exactly 4 distinct potion token IDs, comma-separated (e.g. --potions 1,2,3,4)")
    a = _addrs()
    potion, burner = a["potion"], a["burner"]
    v = _post("/ritual-voucher", {"wallet": wallet, "potionIds": ids})
    if v.get("error"):
        _die("backend: " + v["error"])
    # SAFETY: reject a backend that tries to redirect the burn/approval to another burner.
    if v.get("burner") and v["burner"].lower() != burner.lower():
        _die(f"backend returned an unexpected burner {v['burner']!r} (pinned {burner}); refusing")
    fee = int(v["feeWei"])
    if fee > MAX_FEE_WEI:
        _die(f"ritual fee {fee} wei exceeds the safety cap {MAX_FEE_WEI} wei; refusing")
    # 1) approve ONLY the 4 potions being burned (scoped — never setApprovalForAll)
    approve_txs = []
    for i, tid in enumerate(ids):
        ad = _sel("approve(address,uint256)") + encode(["address", "uint256"], [burner, tid])
        approve_txs.append({"step": i + 1, "desc": f"approve the RitualBurner for potion #{tid} only",
                            "tx": {"to": potion, "data": "0x" + ad.hex(), "value": "0"}})
    # 2) ritual(potionIds[4], tier, element, metaId, nonce, deadline, sig) payable
    ritual_data = _sel("ritual(uint256[4],uint8,uint8,uint256,uint256,uint256,bytes)") + encode(
        ["uint256[4]", "uint8", "uint8", "uint256", "uint256", "uint256", "bytes"],
        [ids, int(v["tier"]), int(v["element"]), int(v["metaId"]),
         int(v["nonce"]), int(v["deadline"]), bytes.fromhex(v["signature"][2:])])
    tx_ritual = {"to": burner, "data": "0x" + ritual_data.hex(), "value": str(fee)}
    print(json.dumps({
        "action": "ritual",
        "result": {"tier": v["tierName"], "element": v["elementName"], "totalPoints": v["totalPoints"]},
        "txs": approve_txs + [
            {"step": 5, "desc": "burn the 4 potions + pay fee -> summon the Agent Skelly", "tx": tx_ritual},
        ],
        "note": "Send the 4 scoped approvals (skip any already approved), then the final payable ritual tx. "
                "One Agent Skelly is crafted to you; your approval is limited to exactly these 4 potions."
    }, indent=2))


def main():
    ap = argparse.ArgumentParser(
        prog="ritual",
        description="RITUAL agent CLI — mint Potions and perform the ritual to summon Agent Skellies on BNB Chain. "
                    "Prints ready-to-send transactions as JSON; your wallet broadcasts them. The backend only "
                    "signs vouchers — contract addresses are pinned, so it can never redirect your funds.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="{mint,ritual}")

    m = sub.add_parser("mint", help="fetch a signed voucher and emit the Potion mint tx")
    m.add_argument("--wallet", required=True, metavar="0xADDR", help="the agent wallet that will mint and own the Potion")

    r = sub.add_parser("ritual", help="burn 4 Potions + fee to summon 1 Agent Skelly")
    r.add_argument("--wallet", required=True, metavar="0xADDR", help="the agent wallet that owns the 4 Potions")
    r.add_argument("--potions", required=True, metavar="A,B,C,D", help="4 distinct Potion token IDs you own, comma-separated")

    args = ap.parse_args()
    if args.cmd == "mint":
        cmd_mint(args.wallet)
    elif args.cmd == "ritual":
        cmd_ritual(args.wallet, args.potions)


if __name__ == "__main__":
    main()
