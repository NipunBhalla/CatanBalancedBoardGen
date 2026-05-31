# -*- coding: utf-8 -*-

import numpy as np
import random
import math
import argparse
import json
import sys

# config
defaultPortLocations = 1
portCheck = 1

hexRad = 2 / np.sqrt(3)

# --- ultra-balance helpers -------------------------------------------------
# Dice "pips" (dots under each number) = ways to roll it; higher = more likely.
PIP_BY_NUMBER = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}

# Resource tile counts (matches listOfTilesStart). 18 numbered tiles, 58 pips total.
RESOURCE_COUNTS = {'sheep': 4, 'wheat': 4, 'wood': 4, 'stone': 3, 'brick': 3}
TOTAL_PIPS = 58
NUM_TILES = 18

# Neighbour offsets in the doubled coordinate system.
NEIGHBOR_OFFSETS = [(2, 0), (1, 1), (-1, 1), (-2, 0), (-1, -1), (1, -1)]

# Pip strictness presets for ultra mode (None -> no pip constraint).
BALANCE_TOL = {'good': None, 'better': 2, 'best': 1}

# Safety cap so the ultra number-balancing search always terminates.
NUMBER_ATTEMPT_CAP = 100000


def is_neighbor(c, d):
    """True if tile d is a neighbour of tile c (doubled coords)."""
    return any(d[0] == c[0] + dx and d[1] == c[1] + dy for dx, dy in NEIGHBOR_OFFSETS)


def pip_target(resource):
    """Fair pip total for a resource if pips were split evenly per tile."""
    return RESOURCE_COUNTS[resource] * TOTAL_PIPS / NUM_TILES


def pip_sums(doubleCoord):
    """Total pips currently sitting on each resource (desert skipped)."""
    sums = {r: 0 for r in RESOURCE_COUNTS}
    for c in doubleCoord:
        if c[3] in sums and c[4] in PIP_BY_NUMBER:
            sums[c[3]] += PIP_BY_NUMBER[c[4]]
    return sums


def pip_balanced(sums, tol):
    """Within-group spread <= tol AND each resource within target +- tol."""
    if tol is None:
        return True
    group4 = [sums['sheep'], sums['wheat'], sums['wood']]
    group3 = [sums['stone'], sums['brick']]
    if max(group4) - min(group4) > tol:
        return False
    if max(group3) - min(group3) > tol:
        return False
    for r, total in sums.items():
        if abs(total - pip_target(r)) > tol:
            return False
    return True


def pip_badness(sums, tol):
    """How far the layout is over tolerance (0.0 == perfectly within tol)."""
    if tol is None:
        return 0.0
    group4 = [sums['sheep'], sums['wheat'], sums['wood']]
    group3 = [sums['stone'], sums['brick']]
    bad = max(0.0, (max(group4) - min(group4)) - tol)
    bad += max(0.0, (max(group3) - min(group3)) - tol)
    for r, total in sums.items():
        bad += max(0.0, abs(total - pip_target(r)) - tol)
    return bad


# Hexagon locations using a doubled coordinate system
# x location, y location, ID, type of tile, dice roll number
doubleCoordStart = [[-2, 2, 0, '', 0],
                    [0, 2, 1, '', 0],
                    [2, 2, 2, '', 0],
                    [-3, 1, 3, '', 0],
                    [-1, 1, 4, '', 0],
                    [1, 1, 5, '', 0],
                    [3, 1, 6, '', 0],
                    [-4, 0, 7, '', 0],
                    [-2, 0, 8, '', 0],
                    [0, 0, 9, '', 0],
                    [2, 0, 10, '', 0],
                    [4, 0, 11, '', 0],
                    [-3, -1, 12, '', 0],
                    [-1, -1, 13, '', 0],
                    [1, -1, 14, '', 0],
                    [3, -1, 15, '', 0],
                    [-2, -2, 16, '', 0],
                    [0, -2, 17, '', 0],
                    [2, -2, 18, '', 0]]

# port locations
# x location (pier 1), y location (pier 1), x location (pier 2), y location (pier 2) ID, type of port
portCoord = [[-1, 3.5 * hexRad, 0, 4 * hexRad, 0, ''],
             [2, 4 * hexRad, 3, 3.5 * hexRad, 1, ''],
             [4, 2 * hexRad, 4, hexRad, 2, ''],
             [4, -hexRad, 4, -2 * hexRad, 3, ''],
             [3, -3.5 * hexRad, 2, -4 * hexRad, 4, ''],
             [0, -4 * hexRad, -1, -3.5 * hexRad, 5, ''],
             [-3, -2.5 * hexRad, -4, -2 * hexRad, 6, ''],
             [-5, -0.5 * hexRad, -5, +0.5 * hexRad, 7, ''],
             [-4, 2 * hexRad, -3, 2.5 * hexRad, 8, '']]

# List of tiles that are too close to the port to match the port's resource type
# Note tile ID 20 is used as filler/placeholder where less than 5 banned tiles are needed
# Port ID, Tile ID 1,  Tile ID 2,  Tile ID 3,  Tile ID 4,  Tile ID 5
portBannedTiles = [[0, 0, 1, 2, 4, 5],
                   [1, 1, 2, 5, 6, 20],
                   [2, 2, 5, 6, 10, 11],
                   [3, 10, 11, 14, 15, 18],
                   [4, 14, 15, 17, 18, 20],
                   [5, 13, 14, 16, 17, 18],
                   [6, 7, 8, 12, 13, 16],
                   [7, 3, 7, 8, 12, 20],
                   [8, 0, 3, 4, 7, 8]]

listOfPortsStart = ['wood',
                    '?',
                    'wheat',
                    'stone',
                    '?',
                    'sheep',
                    '?',
                    '?',
                    'brick']

listOfRollNumbersStart = [2,
                          3,
                          3,
                          4,
                          4,
                          5,
                          5,
                          6,
                          6,
                          8,
                          8,
                          9,
                          9,
                          10,
                          10,
                          11,
                          11,
                          12]

listOfTilesStart = ['sheep',
                    'sheep',
                    'sheep',
                    'sheep',
                    'wheat',
                    'wheat',
                    'wheat',
                    'wheat',
                    'wood',
                    'wood',
                    'wood',
                    'wood',
                    'stone',
                    'stone',
                    'stone',
                    'brick',
                    'brick',
                    'brick', ]


def assign_ports():
    listOfPorts = listOfPortsStart[:]
    for p in portCoord:
        if defaultPortLocations == 1:
            p[5] = listOfPorts[p[4]]
        else:
            p[5] = random.choice(listOfPorts)
            listOfPorts.remove(p[5])


def place_resources_ultra(doubleCoord, desertX, desertY):
    """Place resources via randomized backtracking so no two tiles of the same
    resource touch and port resource-bans are respected.

    Rejection sampling almost never finds such a layout (~1 in 100k random
    fills), so ultra searches directly. Returns (ok, deadEnds): ok is True on
    success (always True for the standard board), False only if no arrangement
    exists; deadEnds is how many placements had to be undone (search effort).
    Mutates c[3]; assumes assign_ports() has already run."""
    n = len(doubleCoord)
    neighbors = [[] for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j and is_neighbor(doubleCoord[i], doubleCoord[j]):
                neighbors[i].append(j)

    # Resources a tile may NOT take because a same-type port sits beside it.
    banned = {c[2]: set() for c in doubleCoord}
    if portCheck == 1:
        for p in portCoord:
            if p[5] in RESOURCE_COUNTS:
                for tid in portBannedTiles[p[4]][1:]:
                    if tid in banned:
                        banned[tid].add(p[5])

    order = []
    for idx, c in enumerate(doubleCoord):
        if c[0] == desertX and c[1] == desertY:
            c[3] = 'desert'
        else:
            c[3] = ''
            order.append(idx)
    # Fill the most-constrained tiles (most neighbours) first -> fewer dead ends.
    order.sort(key=lambda i: -len(neighbors[i]))

    counts = dict(RESOURCE_COUNTS)
    deadEnds = [0]  # placements undone because they led nowhere

    def backtrack(k):
        if k == len(order):
            return True
        idx = order[k]
        c = doubleCoord[idx]
        choices = []
        for r in RESOURCE_COUNTS:
            if counts[r] <= 0 or r in banned[c[2]]:
                continue
            if any(doubleCoord[j][3] == r for j in neighbors[idx]):
                continue
            choices.append(r)
        random.shuffle(choices)  # seed-driven variety across boards
        for r in choices:
            c[3] = r
            counts[r] -= 1
            if backtrack(k + 1):
                return True
            counts[r] += 1
            c[3] = ''
            deadEnds[0] += 1
        return False

    ok = backtrack(0)
    return ok, deadEnds[0]


def generate_board(doubleCoord, desertX, desertY, mode='classic', balance='better'):
    """Assign resources and roll numbers.

    mode='classic' reproduces the original behaviour exactly.
    mode='ultra' forbids ANY two same-resource tiles from touching and (for
    balance 'better'/'best') balances the pip totals across resources.
    Returns (tileFails, numberFails, balance_info)."""

    tol = BALANCE_TOL[balance] if mode == 'ultra' else None

    numOfTileFails = 0
    numOfNumberFails = 0

    assign_ports()

    resourceCapHit = False
    numberCapHit = False

    if mode == 'ultra':
        # Backtracking finds a no-touch, port-valid layout directly. Rejection
        # sampling effectively never does (~1 in 100k random fills); backtracking
        # finds one in <1ms across every desert position. Dead-ends (undone
        # placements) are the analogue of classic's tile fails.
        ok, numOfTileFails = place_resources_ultra(doubleCoord, desertX, desertY)
        if not ok:
            resourceCapHit = True  # no arrangement exists (never for standard board)
    else:
        hasFailed = 0
        successfulBoard = 1

        while successfulBoard == 1:
            # reset
            successfulBoard = 0
            hasFailed = 0
            listOfTiles = listOfTilesStart[:]
            for c in doubleCoord:
                c[3] = ''

            for c in doubleCoord:
                if c[0] == desertX and c[1] == desertY:
                    c[3] = 'desert'
                else:
                    timeOutCounter = 0
                    if portCheck == 1:
                        isBannedByPort = 1
                        while isBannedByPort == 1 and timeOutCounter < 100:
                            tileNotAllowed = 0
                            # pick a tile resource
                            c[3] = random.choice(listOfTiles)
                            # loop through the port IDs
                            for p in portCoord:
                                # check if the port type is equal to the selected tile resource
                                if p[5] == c[3]:
                                    # check if the current hex ID is on the banned list for that port
                                    for i in range(5):
                                        if portBannedTiles[p[4]][i + 1] == c[2]:
                                            tileNotAllowed = 1
                                    if tileNotAllowed == 0:
                                        isBannedByPort = 0
                            timeOutCounter = timeOutCounter + 1

                    else:
                        c[3] = random.choice(listOfTiles)
                    if timeOutCounter >= 100:
                        # print("Port Failed")
                        successfulBoard = 1

                    if len(listOfTiles) != 1:
                        listOfTiles.remove(c[3])

            # brick and stone check
            for c in doubleCoord:
                if c[3] == 'stone' or c[3] == 'brick':
                    # run through tiles - if one is a neighbour then check if it is the same resource
                    for d in doubleCoord:
                        if is_neighbor(c, d):
                            # print(str(d[2]) + " is a neighbour of " + str(c[2]))
                            if d[3] == c[3]:
                                hasFailed = 1

            # other resources check
            for c in doubleCoord:
                if c[3] == 'wheat' or c[3] == 'wood' or c[3] == 'sheep':
                    # run through tiles - if one is a neighbour then check if it is the same resource
                    for d in doubleCoord:
                        if is_neighbor(c, d):
                            # print(str(d[2]) + " is a neighbour of " + str(c[2]))
                            if d[3] == c[3]:
                                # if neighbour is the same resource check all of it's neighbours as well
                                for e in doubleCoord:
                                    if is_neighbor(d, e):
                                        if e[2] != c[2] and e[3] == d[3]:
                                            hasFailed = 1

            if hasFailed == 1:
                hasFailed = 0
                successfulBoard = 1
                # print("FAILED")
                numOfTileFails = numOfTileFails + 1

    # Asigning numbers
    numberAttempts = 0
    best_badness = None
    best_numbers = None
    successfulNumbers = 1
    while successfulNumbers == 1:
        # reset
        successfulNumbers = 0
        listOfRollNumbers = listOfRollNumbersStart[:]
        hasFailedNumber = 0
        numberAttempts = numberAttempts + 1

        for c in doubleCoord:
            if c[0] == desertX and c[1] == desertY:
                pass
            else:
                c[4] = random.choice(listOfRollNumbers)
                if len(listOfRollNumbers) != 1:
                    listOfRollNumbers.remove(c[4])

        # check no two of the same number next to eachother
        for c in doubleCoord:
            for d in doubleCoord:
                if is_neighbor(c, d):
                    # print(str(d[2]) + " is a neighbour of " + str(c[2]))
                    if d[4] == c[4]:
                        hasFailedNumber = 1

        # no two of the same number on one resource check
        for c in doubleCoord:
            for d in doubleCoord:
                if d[2] != c[2]:
                    if d[3] == c[3] and d[4] == c[4]:
                        hasFailedNumber = 1

        # no six and eight on the same resource
        for c in doubleCoord:
            if c[4] == 6 or c[4] == 8:
                for d in doubleCoord:
                    if d[2] != c[2]:
                        if d[3] == c[3] and (d[4] == 6 or d[4] == 8):
                            hasFailedNumber = 1

        # no six and eight next to eachother check
        for c in doubleCoord:
            if c[4] == 6 or c[4] == 8:
                for d in doubleCoord:
                    if is_neighbor(c, d):
                        # print(str(d[2]) + " is a neighbour of " + str(c[2]))
                        if d[4] == 6 or d[4] == 8:
                            hasFailedNumber = 1

        if hasFailedNumber == 1:
            # print("NUMBER FAILED")
            successfulNumbers = 1
            numOfNumberFails = numOfNumberFails + 1
        elif mode == 'ultra' and tol is not None:
            # hard constraints met; now enforce pip balance (best-effort)
            sums = pip_sums(doubleCoord)
            badness = pip_badness(sums, tol)
            if best_badness is None or badness < best_badness:
                best_badness = badness
                best_numbers = [c[4] for c in doubleCoord]
            if badness > 0:
                successfulNumbers = 1
                numOfNumberFails = numOfNumberFails + 1

        if mode == 'ultra' and successfulNumbers == 1 and numberAttempts >= NUMBER_ATTEMPT_CAP:
            # give up: restore the closest-balanced hard-valid layout found
            if best_numbers is not None:
                for c, n in zip(doubleCoord, best_numbers):
                    c[4] = n
            successfulNumbers = 0
            numberCapHit = True

    sums = pip_sums(doubleCoord)
    balance_info = {
        'mode': mode,
        'balance': balance if mode == 'ultra' else None,
        'pip_totals': sums,
        'pip_targets': {r: round(pip_target(r), 1) for r in RESOURCE_COUNTS},
        'balanced': (pip_balanced(sums, tol) if (mode == 'ultra' and tol is not None) else None),
        'resource_cap_hit': resourceCapHit,
        'number_cap_hit': numberCapHit,
    }
    return numOfTileFails, numOfNumberFails, balance_info


def board_to_json(doubleCoord, seed, desertX, desertY, balance_info=None):
    tiles = [{"id": c[2], "x": c[0], "y": c[1], "resource": c[3], "number": c[4]}
             for c in doubleCoord]
    ports = [{"x1": p[0], "y1": p[1], "x2": p[2], "y2": p[3], "id": p[4], "type": p[5]}
             for p in portCoord]
    board = {
        "seed": seed,
        "desert": {"x": desertX, "y": desertY},
        "tiles": tiles,
        "ports": ports,
    }
    if balance_info is not None:
        board["mode"] = balance_info["mode"]
        board["balance"] = balance_info["balance"]
        board["balanced"] = balance_info["balanced"]
        board["pip_totals"] = balance_info["pip_totals"]
        board["pip_targets"] = balance_info["pip_targets"]
    return board


def make_board(seed=None, desert_tile='random', mode='classic', balance='better'):
    """Generate a board and return it as a JSON-serialisable dict.
    Shared by the CLI and the Flask API so both stay in sync.

    seed: any text/number for deterministic output (blank/None -> random).
    desert_tile: 'middle' (centre tile) or 'random' (any tile).
    mode: 'classic' (original) or 'ultra' (no same-resource touching + pip balance).
    balance: 'good' | 'better' | 'best' pip strictness (only used when mode='ultra').
    """
    seed = seed if seed is not None else str(random.randrange(2 ** 32))
    random.seed(seed)

    doubleCoord = [row[:] for row in doubleCoordStart]

    if desert_tile == 'middle':
        desertX, desertY = 0, 0
    else:
        dt = random.choice(doubleCoord)
        desertX, desertY = dt[0], dt[1]

    tileFails, numberFails, balance_info = generate_board(
        doubleCoord, desertX, desertY, mode=mode, balance=balance)

    # Classic keeps its original JSON envelope; ultra adds balance metadata.
    board = board_to_json(doubleCoord, seed, desertX, desertY,
                          balance_info if mode == 'ultra' else None)
    board["tileFails"] = tileFails
    board["numberFails"] = numberFails
    if mode == 'ultra':
        board["resourceCapHit"] = balance_info["resource_cap_hit"]
        board["numberCapHit"] = balance_info["number_cap_hit"]
    return board


def plot_board(doubleCoord, desertX, desertY):
    import matplotlib.pyplot as plt
    from matplotlib.patches import RegularPolygon

    plt.rcParams['figure.dpi'] = 120
    fig, ax = plt.subplots(1, figsize=(8, 8))
    ax.set_aspect('equal')
    ax.axis([-7, 7, -7, 7])
    plt.axis('off')

    # Plotting
    outerCoord1 = [[2, 4 * hexRad], [2, 5 * hexRad], [-5 * (hexRad / np.sqrt(3)), 5 * hexRad], [-3 - (hexRad / 2) * np.sqrt(3), 4 * hexRad], [-3, 3.5 * hexRad], [-2, 4 * hexRad], [-1, 3.5 * hexRad], [0, 4 * hexRad], [1, 3.5 * hexRad]]
    outerCoord1.append(outerCoord1[0])  # repeat the first point to create a 'closed loop'

    arr = np.array(outerCoord1)
    arr2 = np.transpose(arr)

    rotArr = np.array([[math.cos(math.radians(60)), -math.sin(math.radians(60))], [math.sin(math.radians(60)), math.cos(math.radians(60))]])
    outerCoord2 = np.matmul(rotArr, arr2)
    outerCoord3 = np.matmul(rotArr, outerCoord2)
    outerCoord4 = np.matmul(rotArr, outerCoord3)
    outerCoord5 = np.matmul(rotArr, outerCoord4)
    outerCoord6 = np.matmul(rotArr, outerCoord5)

    oceanAlpha = 0.2

    xs, ys = zip(*outerCoord1)  # create lists of x and y values
    ax.plot(xs, ys, color='blue', alpha=oceanAlpha)

    outerCoord2 = np.transpose(outerCoord2)
    outerCoord2 = outerCoord2.tolist()
    xs, ys = zip(*outerCoord2)  # create lists of x and y values
    ax.plot(xs, ys, color='blue', alpha=oceanAlpha)

    outerCoord3 = np.transpose(outerCoord3)
    outerCoord3 = outerCoord3.tolist()
    xs, ys = zip(*outerCoord3)  # create lists of x and y values
    ax.plot(xs, ys, color='blue', alpha=oceanAlpha)

    outerCoord4 = np.transpose(outerCoord4)
    outerCoord4 = outerCoord4.tolist()
    xs, ys = zip(*outerCoord4)  # create lists of x and y values
    ax.plot(xs, ys, color='blue', alpha=oceanAlpha)

    outerCoord5 = np.transpose(outerCoord5)
    outerCoord5 = outerCoord5.tolist()
    xs, ys = zip(*outerCoord5)  # create lists of x and y values
    ax.plot(xs, ys, color='blue', alpha=oceanAlpha)

    outerCoord6 = np.transpose(outerCoord6)
    outerCoord6 = outerCoord6.tolist()
    xs, ys = zip(*outerCoord6)  # create lists of x and y values
    ax.plot(xs, ys, color='blue', alpha=oceanAlpha)

    for c in doubleCoord:

        if c[3] == 'sheep':
            tileColour = 'green'
        elif c[3] == 'wood':
            tileColour = '#023020'
        elif c[3] == 'wheat':
            tileColour = 'yellow'
        elif c[3] == 'brick':
            tileColour = 'red'
        elif c[3] == 'stone':
            tileColour = 'gray'
        elif c[3] == 'desert':
            tileColour = 'orange'

        hexagon = RegularPolygon((c[0], c[1] * 1.5 * hexRad), numVertices=6, radius=hexRad, alpha=0.6, edgecolor='k', facecolor=tileColour)
        ax.add_patch(hexagon)

    for p in portCoord:

        if p[5] == 'sheep':
            portColour = 'green'
        elif p[5] == 'wood':
            portColour = '#023020'
        elif p[5] == 'wheat':
            portColour = 'yellow'
        elif p[5] == 'brick':
            portColour = 'red'
        elif p[5] == 'stone':
            portColour = 'gray'
        elif p[5] == '?':
            portColour = 'black'

        circlePort = plt.Circle((p[0], p[1]), 0.2, edgecolor=portColour, fill=False)
        ax.add_patch(circlePort)
        circlePort = plt.Circle((p[2], p[3]), 0.2, edgecolor=portColour, fill=False)
        ax.add_patch(circlePort)

    # plot circles for numbers
    for c in doubleCoord:
        if c[0] == desertX and c[1] == desertY:
            pass
        else:
            numberCircle = plt.Circle((c[0], c[1] * 1.5 * hexRad), 0.5, edgecolor='black', facecolor='white')
            ax.add_patch(numberCircle)
            if c[4] == 6 or c[4] == 8:
                textColour = 'red'
            else:
                textColour = 'black'
            plt.text(c[0], c[1] * 1.5 * hexRad, c[4], ha='center', va='center', size=14, color=textColour)

    # plt.autoscale(enable = True)
    plt.show()


def parse_args():
    parser = argparse.ArgumentParser(description="Balanced Catan board generator.")
    parser.add_argument('--cli', action='store_true',
                        help="Print the board as JSON to stdout instead of opening the GUI.")
    parser.add_argument('--seed', type=str, default=None,
                        help="Seed (any text or number) for deterministic generation. Same seed + same --desert-tile -> same board.")
    parser.add_argument('--desert-tile', choices=['middle', 'random'], default='random',
                        help="Where the desert goes. 'random' (default) picks any tile; 'middle' uses the centre.")
    parser.add_argument('--mode', choices=['classic', 'ultra'], default='classic',
                        help="'classic' (default) is the original generator. 'ultra' forbids any two "
                             "same-resource tiles from touching and balances pips across resources.")
    parser.add_argument('--balance', choices=['good', 'better', 'best'], default=None,
                        help="Pip balance strictness for --mode ultra. good = no pip constraint, "
                             "better = within +-2 (default), best = within +-1. Ignored in classic mode.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.mode == 'classic' and args.balance is not None:
        print("Note: --balance only applies to --mode ultra; ignoring it for classic mode.",
              file=sys.stderr)
    balance = args.balance if args.balance is not None else 'better'

    if args.cli:
        board = make_board(seed=args.seed, desert_tile=args.desert_tile,
                           mode=args.mode, balance=balance)
        if board.get("resourceCapHit"):
            print("Warning: hit resource attempt cap; some same-resource tiles may touch.",
                  file=sys.stderr)
        if board.get("numberCapHit"):
            print("Warning: hit number attempt cap; kept the closest pip balance found.",
                  file=sys.stderr)
        print(json.dumps(board, indent=2))
    else:
        seed = args.seed if args.seed is not None else str(random.randrange(2 ** 32))
        random.seed(seed)

        doubleCoord = [row[:] for row in doubleCoordStart]

        if args.desert_tile == 'middle':
            desertX, desertY = 0, 0
        else:
            dt = random.choice(doubleCoord)
            desertX, desertY = dt[0], dt[1]

        tileFails, numberFails, balance_info = generate_board(
            doubleCoord, desertX, desertY, mode=args.mode, balance=balance)

        if balance_info['resource_cap_hit']:
            print("Warning: hit resource attempt cap; some same-resource tiles may touch.",
                  file=sys.stderr)
        if balance_info['number_cap_hit']:
            print("Warning: hit number attempt cap; kept the closest pip balance found.",
                  file=sys.stderr)

        print("Seed = " + str(seed))
        print("Mode = " + args.mode + ((" (" + balance + ")") if args.mode == 'ultra' else ""))
        print("Number of tile fails = " + str(tileFails) + " and number of number fails = " + str(numberFails))
        totals = balance_info['pip_totals']
        targets = balance_info['pip_targets']
        print("Pip totals (target): " + ", ".join(
            r + "=" + str(totals[r]) + " (" + str(targets[r]) + ")" for r in totals))
        if balance_info['balanced'] is not None:
            print("Balanced = " + str(balance_info['balanced']))
        plot_board(doubleCoord, desertX, desertY)
