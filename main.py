import PIL
import PIL.ImageDraw
from PIL import Image

from pywintypes import error
from statistics import StatisticsError

from itertools import count

import sys

from getScreenshot import getWindowScreenshot
from getGrid import getGameGrid
from functions import checkSquare

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

# functions to wrap error handling
def getGame():
    try:
        return getWindowScreenshot()
    except error as ex:
        if ex.args[0] == 1400 and ex.args[2] == 'Invalid window handle.':
            print("Minesweeper not open. Please ensure game is running.")
            exit()
        else:
            raise ex
def getGrid(img: Image.Image):
    try:
        return getGameGrid(img)
    except StatisticsError:
        print("Error: Minesweeper is minimised.")
        exit()

if __name__ == "__main__":
    # get game screenshot
    img = getGame()
    lastImgSize = img.size

    # get game bounds and config
    width, height, boxSide, top, bottom, left, right = getGrid(img)
    
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
                    exit()
            boxSide = (((right-left)/width) + ((bottom-top)/height))/2
        except ValueError:
            print("All positional arguments must be integers.")

    # create grid, all squares are unchecked
    grid = [['u' for _ in range(height)] for _ in range(width)]
    
    # create lists of squares
    unchecked = {(x, y) for x in range(width) for y in range(height)}
    unsolved: set[tuple[int, int]] = set()

    bTurn = True

    while bTurn:
        ## do turn
        # get new screenshot
        img = getGame()

        # check if window has been resized
        if img.size != lastImgSize:
            _, _, _, top, bottom, left, right = getGameGrid(img)
            boxSide = (((right-left)/width) + ((bottom-top)/height))/2
            lastImgSize = img.size

        # check all unchecked squares
        coordsToRemove: set[tuple[int, int]] = set()
        for coords in unchecked:
            squareVal = checkSquare(img, (left + (coords[0]*boxSide), top + (coords[1]*boxSide)), boxSide)
            if squareVal != 'u':
                if squareVal != 'f' and squareVal != '0':
                    # square is unsolved
                    unsolved.add(coords)
                # update value in grid
                grid[coords[0]][coords[1]] = squareVal
                coordsToRemove.add(coords)
        unchecked -= coordsToRemove

        # create zones
        zonedSquares: dict[
            tuple[int, int],
            set[str]
        ] = {}
        zones: dict[
            int,
            tuple[
                int,                 # bomb count
                set[tuple[int, int]] # squares in zone
            ]
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
                if squareVal == 'f':
                    # bomb accounted for, 1 less to find in zone
                    bombCount -= 1
                elif squareVal == 'u':
                    tempZonedSquares.add(adjCoords)
            if len(tempZonedSquares) == 0:
                # no unsolved squares adjacent, mark as solved
                coordsToRemove.add(coords)
            else:
                # add new zone
                key = next(zoneKey)
                zones[key] = (bombCount, tempZonedSquares)

                # add square to zoned squares or add zone to square if already exists
                for square in tempZonedSquares:
                    if square in zonedSquares:
                        zonedSquares[square].add(key)
                    else:
                        zonedSquares[square] = {key}
        
        # removed solved squares from unsolved list
        unsolved -= coordsToRemove
        
        # decompose zones (remove overlap where possible)
        # squaresDeque = deque(zonedSquares)
        squaresSet = set(zonedSquares)
        while len(squaresSet) != 0:
            changedSquares: set[tuple[int, int]] = set()

            square = squaresSet.pop()
            # check each zone applied to square for 0 or 100 percent bomb chance
            for z in zonedSquares[square]:
                if (zones[z][0] == 0 or zones[z][0] == len(zones[z][1])) and len(zonedSquares[square]) > 1:
                    # remove and update all other zones
                    for z1 in zonedSquares[square] - {z}:
                        z1Bombs, z1Squares = zones[z1]
                        changedSquares.update(z1Squares)
                        if zones[z][0] != 0:
                            z1Bombs -= 1
                        z1Squares = z1Squares - {square}

                        zones[z1] = (z1Bombs, z1Squares)
                    zonedSquares[square] = {z}
                    break # there's only one zone on this square now. Don't bother checking any more
            else:
                # no 0 or 100 found, check for overlap to decompose
                checkedZones: set[str] = set()
                while not zonedSquares[square].issubset(checkedZones):
                    # get base zone for comparison
                    for key1 in zonedSquares[square]:
                        if key1 not in checkedZones:
                            break
                    checkedZones.add(key1)

                    # get second zone for comparison
                    bSolved = False
                    for key2 in zonedSquares[square]:
                        if key2 not in checkedZones:
                            zone1Bombs, zone1Squares = zones[key1]
                            zone2Bombs, zone2Squares = zones[key2]

                            overlap = zone1Squares & zone2Squares

                            # get minimum number of mines in overlap
                            zone1Potential = zone1Bombs - (len(zone1Squares) - len(overlap))
                            zone2Potential = zone2Bombs - (len(zone2Squares) - len(overlap))
                            potential = max(zone1Potential, zone2Potential)

                            # check if one zone is solved by overlap
                            if potential == zone1Bombs or potential == zone2Bombs:
                                checkedZones.add(key2)
                                # update zones
                                changedSquares.update(zone1Squares, zone2Squares)
                                bSolved = True
                                break
                    
                    if bSolved:
                        # create new zone
                        newKey = next(zoneKey)
                        zones[newKey] = (potential, overlap)

                        k1Bombs = zone1Bombs - potential
                        k1Squares = zone1Squares - overlap

                        k2Bombs = zone2Bombs - potential
                        k2Squares = zone2Squares - overlap

                        zones[key1] = (k1Bombs, k1Squares)
                        zones[key2] = (k2Bombs, k2Squares)

                        for square in overlap:
                            # remove existing zones from square
                            zoneSet = zonedSquares[square]
                            zoneSet.discard(key1)
                            zoneSet.discard(key2)
                            # add new zone to square
                            zoneSet.add(newKey)
                            zonedSquares[square] = zoneSet
            # add new squares to check
            squaresSet.update(changedSquares)
        
        # report on bombs
        if len(zonedSquares) > 0:
            imgMod = PIL.ImageDraw.Draw(img)

            for square in zonedSquares:
                xPos = left+square[0]*boxSide
                yPos = top+square[1]*boxSide
                chances = []
                for z in zonedSquares[square]:
                    chances.append(zones[z][0]/len(zones[z][1]))
                
                if 1.0 in chances:
                    # 100 percent chance of bomb, mark red
                    imgMod.rectangle((xPos + round(boxSide*0.1), yPos + round(boxSide*0.1), xPos + round(boxSide*0.9), yPos + round(boxSide*0.9)), fill="red")
                elif 0.0 in chances:
                    # 0 percent chance of bomb, mark green
                    imgMod.rectangle((xPos + round(boxSide*0.1), yPos + round(boxSide*0.1), xPos + round(boxSide*0.9), yPos + round(boxSide*0.9)), fill="green")
                else:
                    # mark hightest percentage chance of bomb
                    imgMod.text((xPos + round(boxSide/10), yPos + round(boxSide/10)), f"{max(chances):.2f}", fill="black")
            
            img.show()

        
        cont = input("Press enter to continue, type 'n' to stop, or type 'r' to restart with the same size grid: ")
        if 'n' in cont.lower():
            bTurn = False
        elif 'r' in cont.lower():
            # reset lists
            unsolved.clear()
            # reset grid to all unchecked
            grid = [['u' for _ in range(height)] for _ in range(width)]
            unchecked = {(x, y) for x in range(width) for y in range(height)}