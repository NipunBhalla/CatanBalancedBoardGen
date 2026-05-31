# Catan Balanced Board Generator

> **About this fork**
>
> This is a fork of the original [HALAT CatanBalancer](#credits). The original always placed the **desert in the centre tile** of the board. That was my main gripe — a real Catan setup can have the desert anywhere — so this repo was created to fix it. The desert can now land on **any** tile (random by default, or forced to the centre if you want the old behaviour).
>
> While fixing that, a few other quality-of-life features were added: a **seed system** for reproducible boards and a **headless CLI / JSON mode**. See [Changes in this fork](#changes-in-this-fork).

Generates a balanced, valid Catan board layout and renders it with matplotlib — or prints it as JSON for scripting.

---

## Quick start

```bash
# GUI (default): opens a rendered board, desert placed randomly, prints the seed used
python catan_board_generator.py

# Reproduce an exact board 
python catan_board_generator.py --seed 8o1q732xcb3ncq4t

# Headless: print the full board as JSON to stdout, no window
python catan_board_generator.py --cli --seed myCustomSeed

# Keep the classic centre desert
python catan_board_generator.py --desert-tile middle
```

Requires Python 3 with `numpy` and `matplotlib` installed (`matplotlib` is only needed for the GUI, not for `--cli`).

---

## Board placement rules (from the original)

The generator uses **rejection sampling** — it keeps re-rolling until every balance rule is satisfied. These rules are unchanged from the original.

### Tile placement

- Resource pool: **4 sheep, 4 wheat, 4 wood, 3 stone, 3 brick** (18 resource tiles + 1 desert = 19).
- **No two brick tiles adjacent**, and **no two stone tiles adjacent** — these are the scarce resources (3 each), so clustering them is a real balance problem.
- **No cluster of 3+ of the same resource** for wheat / wood / sheep — two adjacent is fine, a third same-type neighbour fails the board.
- **Port constraint** (`portCheck`): a resource-specific port may not sit next to its own resource tile (that would make a 2:1 port overpowered). Enforced via the `portBannedTiles` table.

### Number placement

Dice numbers: one 2, two each of 3–6 and 8–11, one 12 (no 7). Assigned to every non-desert tile, then validated against four rules:

| Rule | Description |
|------|-------------|
| No adjacent duplicates | No two neighbouring tiles share the same roll number |
| No same number on same resource | Each resource type gets at most one tile of a given number |
| No 6 and 8 on the same resource | A resource type can't have both a 6 and an 8 |
| No adjacent 6 and 8 | A 6-tile and an 8-tile can't be neighbours |

The 6/8 rules matter because those are the highest-probability rolls (5/36 each); stacking them is a major imbalance.

---

## Changes in this fork

### 1. Desert can go anywhere

The desert is no longer hard-coded to the centre. Control it with `--desert-tile`:

| Value | Behaviour |
|-------|-----------|
| `random` *(default)* | Desert is placed on a randomly chosen tile |
| `middle` | Desert on the centre tile (the original behaviour) |

All balance rules still hold for any desert position — there are always exactly 18 resource tiles and 18 roll numbers regardless of where the desert sits.

### 2. Seed system (Minecraft-style)

Every run is driven by a single seed. Run without `--seed` and a random one is generated and printed; reuse that seed to regenerate the **identical** board.

```bash
python catan_board_generator.py --seed forest42
```

- `--seed` accepts **any text or number** (e.g. `12345`, `myBoard`, `forest42`). Strings are hashed deterministically.
- Same seed **and** same `--desert-tile` → same board. (Note: `random` desert mode consumes one extra random draw, so a given seed produces a different layout in `random` vs `middle` mode — this is expected.)

### 3. CLI / JSON mode

`--cli` prints the whole board as JSON to stdout and skips the GUI entirely (matplotlib isn't even imported), so it's fast and scriptable.

```bash
python catan_board_generator.py --cli --seed 12345
```

```json
{
  "seed": "12345",
  "desert": { "x": -1, "y": 1 },
  "tiles": [
    { "id": 0, "x": -2, "y": 2, "resource": "wood", "number": 5 }
  ],
  "ports": [
    { "x1": -1, "y1": 4.04, "x2": 0, "y2": 4.62, "id": 0, "type": "wood" }
  ]
}
```

The JSON includes the seed (so the run is fully reproducible), the desert coordinate, every tile (id, coordinates, resource, roll number), and every port (both pier coordinates, id, type).

### 4. Renamed entry point

The script was renamed `HALAT-CatanBalancer.py` → `catan_board_generator.py` (underscores, so no quoting is needed on the command line).

---

## Command-line reference

```
python catan_board_generator.py [--cli] [--seed SEED] [--desert-tile {middle,random}]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--cli` | off | Print board as JSON to stdout instead of opening the GUI |
| `--seed SEED` | random | Seed (any text/number) for reproducible generation |
| `--desert-tile {middle,random}` | `random` | Where the desert is placed |

Flags are shared between modes: the GUI also honours `--seed` and `--desert-tile`; `--cli` only switches output from a window to JSON.

---

## Credits

Fork of the original **HALAT CatanBalancer** project. Original generation logic and balance rules are preserved; this fork adds configurable desert placement, seeding, and a CLI/JSON mode.
