from PIL import Image, ImageDraw

from pywintypes import error
from statistics import StatisticsError

from itertools import count

from dataclasses import dataclass

import sys

from getScreenshot import getWindowScreenshot
from getGrid import getGameGrid
from functions import checkSquare, UNCHECKED, FLAG

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
        # get new screenshot
        img = safeGetScreenshot()

        # check if window has been resized
        if img.size != lastImgSize:
            _, _, _, top, bottom, left, right = safeGetGrid(img)
            boxSide = (((right-left)/width) + ((bottom-top)/height))/2
            lastImgSize = img.size

        # check all unchecked squares
        coordsToRemove: set[tuple[int, int]] = set()
        for coords in unchecked:
            squareVal = checkSquare(img, (left + round(coords[0]*boxSide), top + round(coords[1]*boxSide)), boxSide)
            if squareVal != UNCHECKED:
                if squareVal != FLAG and squareVal != '0':
                    # square is unsolved
                    unsolved.add(coords)
                # update value in grid
                grid[coords[0]][coords[1]] = squareVal
                coordsToRemove.add(coords)
        unchecked -= coordsToRemove

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

        coordsToRemove = set()
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
                coordsToRemove.add(coords)
            else:
                # add new zone
                key = next(zoneKey)
                zones[key] = Zone(bombCount, tempZonedSquares)

                # add square to zoned squares or add zone to square if already exists
                for square in tempZonedSquares:
                    if square in zonedSquares:
                        zonedSquares[square].add(key)
                    else:
                        zonedSquares[square] = {key}
        
        # removed solved squares from unsolved list
        unsolved -= coordsToRemove
        
        # decompose zones (remove overlap where possible)
        squaresSet = set(zonedSquares)
        while len(squaresSet) != 0:
            changedSquares: set[tuple[int, int]] = set()

            square = squaresSet.pop()
            # check each zone applied to square for 0 or 100 percent bomb chance
            for z in zonedSquares[square]:
                if (zones[z].bombs == 0 or zones[z].bombs == len(zones[z].squares)) and len(zonedSquares[square]) > 1:
                    # remove and update all other zones
                    for z1 in zonedSquares[square] - {z}:
                        squareSet = {square}
                        changedSquares |= zones[z1].squares - squareSet
                        if zones[z].bombs != 0:
                            zones[z1].bombs -= 1
                        zones[z1].squares -= squareSet

                    zonedSquares[square] = {z}
                    break # there's only one zone on this square now. Don't bother checking any more
            else:
                # no 0 or 100 found, check for overlap to decompose
                checkedZones: set[int] = set()
                while not zonedSquares[square].issubset(checkedZones):
                    # get base zone for comparison
                    for k1 in zonedSquares[square]:
                        if k1 not in checkedZones:
                            break
                    checkedZones.add(k1)

                    # get second zone for comparison
                    bSolved = False
                    for k2 in zonedSquares[square]:
                        if k2 not in checkedZones:
                            overlap = zones[k1].squares & zones[k2].squares

                            # get minimum number of mines in overlap
                            zone1Potential = zones[k1].bombs - (len(zones[k1].squares) - len(overlap))
                            zone2Potential = zones[k2].bombs - (len(zones[k2].squares) - len(overlap))
                            potential = max(zone1Potential, zone2Potential)

                            # check if one zone is solved by overlap
                            if potential == zones[k1].bombs or potential == zones[k2].bombs:
                                checkedZones.add(k2)
                                # update zones
                                changedSquares |= zones[k1].squares
                                changedSquares |= zones[k2].squares
                                bSolved = True
                                break
                    
                    if bSolved:
                        # create new zone
                        newKey = next(zoneKey)
                        zones[newKey] = Zone(potential, overlap)

                        zones[k1].bombs -= potential
                        zones[k1].squares -= overlap

                        zones[k2].bombs -= potential
                        zones[k2].squares -= overlap

                        for square in overlap:
                            # remove existing zones from square
                            zoneSet = zonedSquares[square]
                            zoneSet.discard(k1)
                            zoneSet.discard(k2)
                            # add new zone to square
                            zoneSet.add(newKey)
                            zonedSquares[square] = zoneSet

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

        
        cont = input("Press enter to continue, type 'n' to stop, or type 'r' to restart with the same size grid: ")
        if 'n' in cont.lower():
            bTurn = False
        elif 'r' in cont.lower():
            # reset lists
            unsolved.clear()
            # reset grid to all unchecked
            grid = [[UNCHECKED for _ in range(height)] for _ in range(width)]
            unchecked = {(x, y) for x in range(width) for y in range(height)}