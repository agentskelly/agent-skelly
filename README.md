<div align="center">

<img src="media/logo.png" alt="Agent Skelly" width="90" />

# RITUAL — Agent Skellies

**An agent-gated NFT crafting game on BNB Smart Chain.**
Mint free Potions → burn 4 at the altar → summon an Agent Skelly.

<img src="media/ritual.gif" alt="The Ritual" width="420" />

**[Website — agent-skelly.fun](https://agent-skelly.fun)** · **[X — @agent_skelly](https://x.com/agent_skelly)** · **BNB Smart Chain**

</div>

---

## What is this

RITUAL is an agent-gated NFT crafting game on BNB Smart Chain (chainId 56).

- **Mint Potions** — the free-minted fuel. 10,000 supply. Agent-gated (a backend signs a voucher for your wallet; no puzzle).
- **Perform the ritual** — burn **4 Potions** + a small BNB fee to summon **1 Agent Skelly**, a necro-trader skull PFP.
- **Tier & element are earned** — a Skelly's TIER is the sum of the 4 potions' rarity points; its ELEMENT is their dominant type. Burn **4 of the same type** → a **Pure Ascended** Skelly.
- **Last Skelly Standing** — every ritual also enters a burn-to-win endgame. The last summoners split the prize pool when the countdown runs out.

There is **no token** and **no direct Skelly mint** — the only way to get an Agent Skelly is the ritual. Max **2,500** will ever exist (10,000 potions ÷ 4 per ritual).

---

## Potions

Four types × five rarities. Rarity carries points; the four you burn decide your Skelly's tier.

| Blood | Bone | Soul | Venom |
|:---:|:---:|:---:|:---:|
| <img src="media/potions/blood-legendary.png" width="120" /> | <img src="media/potions/bone-legendary.png" width="120" /> | <img src="media/potions/soul-legendary.png" width="120" /> | <img src="media/potions/venom-legendary.png" width="120" /> |

Rarity points: Common 1 · Uncommon 2 · Rare 4 · Epic 8 · Legendary 16.

## Agent Skellies

Crafted-only, framed by rarity (Common → Legendary) so tier reads at a glance.

| Legendary | Epic | Rare | Uncommon |
|:---:|:---:|:---:|:---:|
| <img src="media/skellies/skelly-legendary.png" width="150" /> | <img src="media/skellies/skelly-epic.png" width="150" /> | <img src="media/skellies/skelly-rare.png" width="150" /> | <img src="media/skellies/skelly-uncommon.png" width="150" /> |

More summons:

<p>
<img src="media/skellies/skelly-sample-1000.png" width="130" />
<img src="media/skellies/skelly-sample-1500.png" width="130" />
<img src="media/skellies/skelly-sample-2000.png" width="130" />
<img src="media/skellies/skelly-sample-2400.png" width="130" />
</p>

---

## Agent skill

This repo is an agent skill. An agent mints and rituals end-to-end through a CLI — the backend only **signs** vouchers, your wallet broadcasts every transaction. Nothing here touches a private key.

### Quick start

```bash
pip install eth-abi eth-utils

# 1. Mint Potions (repeat to collect at least 4)
python3 ritual.py mint --wallet 0xYOURWALLET

# 2. Perform the ritual — burn 4 Potions, summon an Agent Skelly
python3 ritual.py ritual --wallet 0xYOURWALLET --potions 1234,5678,9012,3456
```

Each command prints ready-to-send transaction(s). Broadcast them from your wallet in order.

Set `RITUAL_API` to the live API base (default `https://agent-skelly.fun/api`), or put contract addresses in `config.json`. Full flow and notes are in [`SKILL.md`](SKILL.md).

---

## How the loop works

1. **Mint Potions** — agent-gated, no puzzle. 10,000 supply.
2. **Collect 4** — each Potion has a type & rarity. Gather any 4 to fuel one ritual.
3. **Perform the Ritual** — burn the 4 Potions + the ritual fee. One atomic transaction.
4. **Summon an Agent Skelly** — crafted to your wallet. Its tier & element come from what you burned, and you become the last summoner in Last Skelly Standing.

---

## Contracts

Live on BNB Smart Chain (chainId 56). Verify each on BscScan.

| Contract | Address |
|---|---|
| PotionNFT | [`0x0Eb88f1b5Eb66264069f5B60D58886Ffa684Fd2C`](https://bscscan.com/address/0x0Eb88f1b5Eb66264069f5B60D58886Ffa684Fd2C) |
| AgentSkellyNFT | [`0xE4416f083fC74EC9BbfbAA20dcb5DD04d4A9F7df`](https://bscscan.com/address/0xE4416f083fC74EC9BbfbAA20dcb5DD04d4A9F7df) |
| RitualBurner | [`0x6dE9915c9c4c471aD8D39a248C1DE58B86c6B0Ce`](https://bscscan.com/address/0x6dE9915c9c4c471aD8D39a248C1DE58B86c6B0Ce) |
| LastSkellyStanding | [`0x9518a8A0D3058215776fe9D5ffFc41a7e95f22aE`](https://bscscan.com/address/0x9518a8A0D3058215776fe9D5ffFc41a7e95f22aE) |

Last Skelly Standing is renounced — no owner, no withdraw.

## Security

The backend only **signs** EIP-712 vouchers; your wallet broadcasts every transaction, and no private key is ever read.

- **Addresses are pinned.** `ritual.py` targets only the contracts above (hardcoded + `config.json`). A voucher that points anywhere else is refused — a compromised backend cannot redirect your funds.
- **Scoped approvals.** The ritual approves *only the 4 specific potions* being burned (`approve(burner, tokenId)` ×4), never `setApprovalForAll`.
- **Value caps.** Mint and ritual values above a hard cap are refused.
- **Prize pool is renounced.** `LastSkellyStanding` has no owner and no withdraw — only winners can `claim()` after the game closes. Verify `owner()` reverts (not Ownable) on BscScan.
- **No user-fund custody.** Your Potions and Skellies are ERC-721s in your wallet. `PotionNFT`/`RitualBurner` keep an owner that can adjust fees/signer and sweep the protocol's *own* fee revenue to the treasury — it cannot take your NFTs or the prize pool.

Don't trust, verify: read every contract on BscScan and simulate with your own wallet before broadcasting.

## License

[MIT](LICENSE) · BNB Smart Chain · chainId 56
