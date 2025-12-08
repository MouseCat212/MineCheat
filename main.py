import PIL
import PIL.ImageDraw

from pywintypes import error
from statistics import StatisticsError

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

if __name__ == "__main__":
    # get game screenshot
    try:
        img = getWindowScreenshot()
    except error as ex:
        if ex.args[0] == 1400 and ex.args[2] == 'Invalid window handle.':
            print("Minesweeper not open. Please ensure game is running.")
            exit()
        else:
            raise ex
    lastImgSize = img.size

    # get game bounds and config
    try:
        width, height, boxSide, top, bottom, left, right = getGameGrid(img)
    except StatisticsError:
        print("Error: Minesweeper is minimised.")
        exit()
    
    # check if window size and position are pre-defined
    if len(sys.argv) >= 3:
        width = int(sys.argv[1])
        height = int(sys.argv[2])
        if len(sys.argv) >= 7:
            left = int(sys.argv[3])
            top = int(sys.argv[4])
            right = int(sys.argv[5])
            bottom = int(sys.argv[6])
        boxSide = (((right-left)/width) + ((bottom-top)/height))/2

    # create lists of squares
    unchecked: list[tuple[int, int]] = []
    unsolved: list[tuple[int, int]] = []

    # create grid, all squares are unchecked
    grid: list[list[tuple[str]]] = []
    for x in range(width):
        grid.append([])
        for y in range(height):
            grid[x].append('u')
            unchecked.append((x, y))

    bTurn = True

    while bTurn:
        ## do turn
        # get new screenshot
        try:
            img = getWindowScreenshot()
        except error as ex:
            if ex.args[0] == 1400 and ex.args[2] == 'Invalid window handle.':
                print("Minesweeper not open. Please ensure game is running.")
                exit()
            else:
                raise ex

        # check if window has been resized
        if img.size != lastImgSize:
            try:
                # update values
                _, _, _, top, bottom, left, right = getGameGrid(img)
                # recalculate boxside to allow for errors in edge detection
                boxSide = (((right-left)/width) + ((bottom-top)/height))/2
            except StatisticsError:
                print("Error: Minesweeper is minimised.")
                exit()
            lastImgSize = img.size
        imgMod = PIL.ImageDraw.Draw(img)

        # check all unchecked squares
        indexToRemove: list[int] = []
        for i in range(len(unchecked)):
            squareVal = checkSquare(img, (left + (unchecked[i][0]*boxSide), top + (unchecked[i][1]*boxSide)), boxSide)
            if squareVal != 'u':
                if squareVal != 'f' and squareVal != '0':
                    # square is unsolved
                    unsolved.append(unchecked[i])
                # update value in grid
                grid[unchecked[i][0]][unchecked[i][1]] = squareVal
                indexToRemove.append(i)
        for i in reversed(indexToRemove):
            unchecked.pop(i)

        # create zones
        zonedSquares: dict[tuple[int, int], list[str]] = {}
        zones: dict[str, tuple[int, list[tuple[int, int]]]] = {}
        indexToRemove = []
        for i in range(len(unsolved)):
            coords = unsolved[i]
            bombCount = int(grid[coords[0]][coords[1]])
            tempZonedSquares: list[tuple[int, int]] = []
            # check all adjacent squares
            for adj in ADJACENT:
                adjCoords = (coords[0]+adj[0], coords[1]+adj[1])
                if adjCoords[0] >= width or adjCoords[0] < 0 or adjCoords[1] >= height or adjCoords[1] < 0:
                    # coords out of grid bounds
                    continue
                squareVal = grid[adjCoords[0]][adjCoords[1]]
                if squareVal == 'f':
                    # bomb accounted for, 1 less to find in zone
                    bombCount -= 1
                elif squareVal == 'u':
                    tempZonedSquares.append(adjCoords)
            if len(tempZonedSquares) == 0:
                # no unsolved squares adjacent, mark as solved
                indexToRemove.append(i)
            else:
                # add new zone
                key = str(coords[0])+'-'+str(coords[1])
                zones[key] = (bombCount, tempZonedSquares)

                # add square to zoned squares or add zone to square if already exists
                for square in tempZonedSquares:
                    if square in zonedSquares:
                        zonedSquares[square] = [*zonedSquares[square], key]
                    else:
                        zonedSquares[square] = [key]
        
        # removed solved squares from unsolved list
        for i in reversed(indexToRemove):
            unsolved.pop(i)
        
        # decompose zones (remove overlap where possible)
        squaresChanged = True
        while squaresChanged:
            squaresChanged = False
            # decompose 100% and 0%
            for square in zonedSquares:
                # check each zone applied to square for 0 or 100 percent bomb chance
                for z in zonedSquares[square]:
                    zone = zones[z]
                    bombChance = zone[0]/len(zone[1])
                    if (bombChance == 0 or bombChance == 1) and len(zonedSquares[square]) > 1:
                        # remove and update all other zones
                        for z1 in zonedSquares[square]:
                            if z1 != z:
                                zones[z1] = (
                                    zones[z1][0] - bombChance, # number of bombs in new zone
                                    [s for s in zones[z1][1] if s != square] # squares in new zone
                                )
                        zonedSquares[square] = [z]
                        squaresChanged = True
                        break # there's only one zone on this square now. Don't bother checking any more
                else:
                    # no 0 or 100 found, check for overlap to decompose
                    checkedZones: set[str] = set()
                    while not set(zonedSquares[square]).issubset(checkedZones):
                        # get base zone for comparison
                        for key1 in zonedSquares[square]:
                            if key1 not in checkedZones:
                                break
                        checkedZones.add(key1)

                        # get second zone for comparison
                        for key2 in zonedSquares[square]:
                            if key2 not in checkedZones:
                                break
                        else:
                            # base zone is last in list
                            continue

                        zone1 = zones[key1]
                        zone2 = zones[key2]

                        overlap = [s for s in zone1[1] if s in zone2[1]]

                        # get minimum number of mines in overlap
                        zone1Potential = zone1[0] - (len(zone1[1]) - len(overlap))
                        zone2Potential = zone2[0] - (len(zone2[1]) - len(overlap))
                        potential = max(zone1Potential, zone2Potential)

                        # check if one zone is solved by overlap
                        if potential == zone1[0] or potential == zone2[0]:
                            # create new zone
                            newKey = key1+"_"+key2
                            zones[newKey] = (potential, overlap)
                            zone1Squares = zone1[1]
                            zone2Squares = zone2[1]

                            for square in overlap:
                                # remove square from existing zones
                                zone1Squares.remove(square)
                                zone2Squares.remove(square)
                                # remove existing zones from square
                                zoneList = zonedSquares[square]
                                zoneList.remove(key1)
                                zoneList.remove(key2)
                                # add new zone to square
                                zoneList.append(newKey)
                                zonedSquares[square] = zoneList

                            zones[key1] = (zone1[0]-potential, zone1Squares)
                            zones[key2] = (zone2[0]-potential, zone2Squares)
                            squaresChanged = True
        
        # report on bombs
        if len(zonedSquares) > 0:
            for square in zonedSquares:
                xPos = left+square[0]*boxSide
                yPos = top+square[1]*boxSide
                chances = []
                for z in zonedSquares[square]:
                    zone = zones[z]
                    bombChance = float(zone[0])/len(zone[1])
                    chances.append(bombChance)
                
                if float(1) in chances:
                    # 100 percent chance of bomb, mark red
                    imgMod.rectangle((xPos + round(boxSide*0.1), yPos + round(boxSide*0.1), xPos + round(boxSide*0.9), yPos + round(boxSide*0.9)), fill="red")
                elif float(0) in chances:
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
            unchecked = []
            unsolved = []
            # reset grid to all unsolved
            for x in range(width):
                for y in range(height):
                    grid[x][y] = 'u'
                    unchecked.append((x,y))