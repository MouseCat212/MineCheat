from PIL import Image, ImageDraw

from pywintypes import error
from statistics import StatisticsError

from itertools import count

from dataclasses import dataclass

import sys

from getScreenshot import getWindowScreenshot
from getGrid import getGameGrid
from functions import checkSquare, UNCHECKED, FLAG

# TODO change to tuple
ADJACENT = [
    (0, -1),
    (1, -1),
    (1, 0),
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (-1, -1)
]

@dataclass
class Zone:
    bombs: int
    squares: set[tuple[int, int]]

# functions to wrap error handling
def safeGetScreenshot():
    try:
        return getWindowScreenshot()
    except error as ex:
        args = ex.args or ()
        code = args[0] if len(args) >= 1 else None
        msg = args[2] if len(args) >= 3 else ""
        if code == 1400 and 'Invalid window handle' in msg:
            print("Minesweeper not open. Please ensure game is running.")
            sys.exit(1)
        else:
            raise ex

def safeGetGrid(img: Image.Image):
    try:
        return getGameGrid(img)
    except StatisticsError:
        print("Error: Minesweeper is minimised.")
        sys.exit(1)

def getUncheckedVals(
    img: Image.Image,
    unchecked: set[tuple[int, int]],
    left: int,
    top: int,
    boxSide: float
) -> dict[
    tuple[int, int], str
]:
    return {
        coords:
        checkSquare(
            img,
            (left + round(coords[0]*boxSide), top + round(coords[1]*boxSide)),
            boxSide
        )
        for coords in unchecked
    }

def checkUnchecked(
    squareVals: dict[tuple[int, int], str]
) -> tuple[
    dict[tuple[int, int], str],
    set[tuple[int, int]]
]:
    checked: dict[tuple[int, int], str] = {}
    unsolved: set[tuple[int, int]] = set()
    for coords, squareVal in squareVals.items():
        if squareVal != UNCHECKED:
            if squareVal != FLAG and squareVal != '0':
                # square is unsolved
                unsolved.add(coords)
            checked[coords] = squareVal
    return(checked, unsolved)

def createZones(
    grid: list[list[str]],
    unsolved: set[tuple[int, int]],
    width: int,
    height: int
) -> tuple[
    set[tuple[int, int]],
    list[Zone]
]:
    solved: set[tuple[int, int]] = set()
    zones: list[Zone] = []

    for coords in unsolved:
        bombCount = int(grid[coords[0]][coords[1]])
        tempZonedSquares: set[tuple[int, int]] = set()
        # check all adjacent squares
        for adj in ADJACENT:
            adjCoords = (coords[0]+adj[0], coords[1]+adj[1])
            if not (0 <= adjCoords[0] < width and 0 <= adjCoords[1] < height):
                # coords out of grid bounds
                continue
            squareVal = grid[adjCoords[0]][adjCoords[1]]
            if squareVal == FLAG:
                # bomb accounted for, 1 less to find in zone
                bombCount -= 1
            elif squareVal == UNCHECKED:
                tempZonedSquares.add(adjCoords)
        
        if len(tempZonedSquares) == 0:
            # no unsolved squares adjacent, mark as solved
            solved.add(coords)
        else:
            zones.append(Zone(bombCount, tempZonedSquares))
    
    return(solved, zones)

def checkSquareSolved(squareZones: set[int], zones: dict[int, Zone]) -> int | None:
    for z in squareZones:
        if zones[z].bombs == 0 or zones[z].bombs == len(zones[z].squares):
            return z
    return None

def processOverlap(
    zone1: Zone,
    zone2: Zone
) -> tuple[
    int,
    set[tuple[int, int]]
]:
    overlap = zone1.squares & zone2.squares

    # get potential 
    zone1Potential = zone1.bombs - (len(zone1.squares) - len(overlap))
    zone2Potential = zone2.bombs - (len(zone2.squares) - len(overlap))
    potential = max(zone1Potential, zone2Potential)

    return potential, overlap

def checkZoneOverlap(
    squareZones: set[int],
    zones: dict[
        int,
        Zone
    ]
) -> tuple[
    int, # first zone in overlap
    int, # second zone in overlap
    set[tuple[int, int]], # squares in overlap
    int # potential number of bombs
] | None:
    squareZonesList = list(squareZones)
    for i in range(len(squareZonesList) - 1):
        z1 = squareZonesList[i]

        for i1 in range(i + 1, len(squareZonesList)):
            z2 = squareZonesList[i1]

            potential, overlap = processOverlap(zones[z1], zones[z2])

            # check if one zone is solved by overlap
            if potential == zones[z1].bombs or potential == zones[z2].bombs:
                return z1, z2, overlap, potential
    return None

def decomposeZone(
    zonedSquares: dict[
        tuple[int, int],
        set[int]
    ],
    zones: dict[
        int,
        Zone
    ],
    zoneKey: count,
    square: tuple[int, int]
) -> set[tuple[int, int]]:
    changedSquares: set[tuple[int, int]] = set()

    # check each zone applied to square for 0 or 100 percent bomb chance
    solvedZone = checkSquareSolved(zonedSquares[square], zones)
    if solvedZone is not None and len(zonedSquares[square]) > 1:
        # remove square from all other zones
        squareSet = {square}
        for z1 in zonedSquares[square] - {solvedZone}:
            zones[z1].squares -= squareSet
            changedSquares |= zones[z1].squares
            if zones[solvedZone].bombs != 0:
                zones[z1].bombs -= 1

        # remove other zones from square
        zonedSquares[square] = {solvedZone}
    else:
        # no 0 or 100 found, check for overlap to decompose
        result = checkZoneOverlap(zonedSquares[square], zones)
        if result is not None:
            k1, k2, overlap, potential = result

            changedSquares |= zones[k1].squares
            changedSquares |= zones[k2].squares

            # create new zone
            newKey = next(zoneKey)
            zones[newKey] = Zone(potential, overlap)

            # update existing zones
            zones[k1].bombs -= potential
            zones[k1].squares -= overlap

            zones[k2].bombs -= potential
            zones[k2].squares -= overlap
            for s in overlap:
                # remove existing zones from square
                zoneSet = zonedSquares[s]
                zoneSet.discard(k1)
                zoneSet.discard(k2)
                # add new zone to square
                zoneSet.add(newKey)
                zonedSquares[s] = zoneSet
    
    return changedSquares

def runTurn(
    grid: list[list[str]],
    unchecked: set[tuple[int, int]],
    unsolved: set[tuple[int, int]],
    lastImgSize: tuple[int, int],
    width: int,
    top: int,
    bottom: int,
    left: int,
    right: int,
    boxSide: float
):
    # get new screenshot
    img = safeGetScreenshot()

    # check if window has been resized
    if img.size != lastImgSize:
        _, _, _, top, bottom, left, right = safeGetGrid(img)
        boxSide = (((right-left)/width) + ((bottom-top)/height))/2
        lastImgSize = img.size
    
    # create zones
    zonedSquares: dict[
        tuple[int, int],
        set[int]
    ] = {}
    zones: dict[
        int,
        Zone
    ] = {}
    zoneKey = count(0)

    # check all unchecked squares
    uncheckedVals = getUncheckedVals(img, unchecked, left, top, boxSide)
    checked, newUnsolved = checkUnchecked(uncheckedVals)
    for coords, squareVal in checked.items():
        grid[coords[0]][coords[1]] = squareVal
        unchecked.remove(coords)
    unsolved |= newUnsolved

    # create new zones
    solved, newZones = createZones(grid, unsolved, width, height)
    unsolved -= solved
    for zone in newZones:
        # add new zone
        key = next(zoneKey)
        zones[key] = zone

        # add square to zoned squares or add zone to square if already exists
        for square in zone.squares:
            if square in zonedSquares:
                zonedSquares[square].add(key)
            else:
                zonedSquares[square] = {key}
    
    # decompose zones (remove overlap where possible)
    squaresSet = set(zonedSquares)
    while len(squaresSet) != 0:
        square = squaresSet.pop()
        changedSquares = decomposeZone(zonedSquares, zones, zoneKey, square)
        # add new squares to check
        squaresSet |= changedSquares
    
    # report on bombs
    if len(zonedSquares) > 0:
        imgMod = ImageDraw.Draw(img)

        for square in zonedSquares:
            xPos = round(left+square[0]*boxSide)
            yPos = round(top+square[1]*boxSide)
            chances = []
            for z in zonedSquares[square]:
                chances.append(zones[z].bombs/len(zones[z].squares))
            
            if 1.0 in chances:
                # 100 percent chance of bomb, mark red
                imgMod.rectangle((xPos + round(boxSide*0.1), yPos + round(boxSide*0.1), xPos + round(boxSide*0.9), yPos + round(boxSide*0.9)), fill="red")
            elif 0.0 in chances:
                # 0 percent chance of bomb, mark green
                imgMod.rectangle((xPos + round(boxSide*0.1), yPos + round(boxSide*0.1), xPos + round(boxSide*0.9), yPos + round(boxSide*0.9)), fill="green")
            else:
                # mark highest percentage chance of bomb
                imgMod.text((xPos + round(boxSide/10), yPos + round(boxSide/10)), f"{max(chances):.2f}", fill="black")
        
        img.show()
    
    return(lastImgSize, top, bottom, left, right)

if __name__ == "__main__":
    # get game screenshot
    img = safeGetScreenshot()
    lastImgSize = img.size

    # get game bounds and config
    width, height, boxSide, top, bottom, left, right = safeGetGrid(img)
    
    # check if window size and position are pre-defined
    if len(sys.argv) >= 3:
        try:
            width = int(sys.argv[1])
            height = int(sys.argv[2])
            if len(sys.argv) >= 7:
                left = int(sys.argv[3])
                top = int(sys.argv[4])
                right = int(sys.argv[5])
                bottom = int(sys.argv[6])
                # check in bounds:
                if not (0 <= left < img.size[0] and 
                        0 <= right < img.size[0] and
                        0 <= top < img.size[1] and
                        0 <= bottom < img.size[1]):
                    print("Error, specified bounds outside image bounds.")
                    sys.exit(1)
            boxSide = (((right-left)/width) + ((bottom-top)/height))/2
        except ValueError:
            print("All positional arguments must be integers.")
            sys.exit(1)

    # create grid, all squares are unchecked
    grid = [[UNCHECKED for _ in range(height)] for _ in range(width)]
    
    # create lists of squares
    unchecked = {(x, y) for x in range(width) for y in range(height)}
    unsolved: set[tuple[int, int]] = set()

    bTurn = True

    while bTurn:
        ## do turn
        lastImgSize, top, bottom, left, right = runTurn(grid, unchecked, unsolved, lastImgSize, width, top, bottom, left, right, boxSide)
        
        cont = input("Press enter to continue, type 'n' to stop, or type 'r' to restart with the same size grid: ")
        if 'n' in cont.lower():
            bTurn = False
        elif 'r' in cont.lower():
            # reset lists
            unsolved.clear()
            # reset grid to all unchecked
            grid = [[UNCHECKED for _ in range(height)] for _ in range(width)]
            unchecked = {(x, y) for x in range(width) for y in range(height)}