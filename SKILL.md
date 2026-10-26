---
name: ritual
description: Mint RITUAL Potions and perform the ritual to summon Agent Skellies on BNB Chain. Use when a user asks to mint a Potion, craft/summon an Agent Skelly, or play Last Skelly Standing.
---

# RITUAL — Agent Skill

RITUAL is an agent-gated NFT crafting game on BNB Smart Chain (chainId 56).

- **Mint Potions** — the fuel. **Free** — the on-chain mint price is 0; you only pay gas. 10,000 supply. Agent-gated (a backend signs a voucher for your wallet).
- **Perform the ritual** — burn **4 Potions** + a small BNB fee to summon **1 Agent Skelly** (a necro-trader skull PFP). The Skelly's TIER comes from the sum of the 4 potions' rarity points; its ELEMENT from their dominant type (4-of-a-kind = Pure Ascended).
- Every ritual also enters you into **Last Skelly Standing** (burn-to-win endgame).

There is **no token** and **no direct Skelly mint** — the only way to get an Agent Skelly is the ritual.

## Prerequisites

- An agent wallet with a little BNB (mint is free, gas only; ritual ~1.5 USDT in BNB, + gas).
- Python 3 with `eth-abi`, `eth-utils` (`pip install eth-abi eth-utils`).

## 1 · Mint a Potion

```bash
python3 ritual.py mint --wallet <YOUR_WALLET>
```

This fetches a signed MintVoucher from the backend and prints a ready-to-send transaction:

```json
{"to": "<PotionNFT>", "data": "0x...", "value": "<priceWei>"}
```

Broadcast that transaction from your wallet (it calls `mintWithVoucher(nonce, deadline, sig)` payable).
Repeat to collect at least **4 Potions**. Max 40 per wallet.

## 2 · Perform the ritual (summon an Agent Skelly)

Pick 4 Potion token IDs you own, then:

```bash
python3 ritual.py ritual --wallet <YOUR_WALLET> --potions 1234,5678,9012,3456
```

This fetches a signed RitualVoucher (the backend reads the 4 potions' committed traits and fixes the
resulting tier/element/art) and prints **five** transactions to send in order:

1–4. `approve(<RitualBurner>, tokenId)` on the Potion contract — one per potion, scoped to exactly the 4 you are burning (never `setApprovalForAll`; skip any already approved).
5. `ritual(potionIds[4], tier, element, metaId, nonce, deadline, sig)` **payable** (value = fee) on the RitualBurner.

After it confirms: the 4 Potions are burned and **1 Agent Skelly is crafted to your wallet**, and you
become the last summoner in Last Skelly Standing (the 6-hour countdown resets).

## Notes

- Vouchers expire (~15 min) — broadcast promptly.
- The backend never holds your keys; it only SIGNS vouchers. Your wallet broadcasts every transaction.
- Rarity is provably-fair (the metadata set is committed on-chain via `provenanceHash` at deploy). Burn better potions → higher-tier Skelly.
- **Addresses are pinned** in `ritual.py` (and `config.json`) — the backend only signs vouchers and can never redirect a transaction target. Approvals are scoped to the 4 burned potions, and mint/fee values above a hard cap are refused.
- **Last Skelly Standing is renounced** — no owner, no withdraw; only winners can `claim()` after the game closes. Don't trust, verify: read the contracts on BscScan.
