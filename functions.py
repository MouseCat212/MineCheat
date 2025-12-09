import math
from PIL import Image
from typing import TypeAlias

GREY = ((235, 244, 249), (169, 173, 205))
ONE = ((55, 75, 190), (140, 150, 190))
TWO = ((30, 100, 0), (105, 145, 110))
THREE = ((160, 5, 5), (155, 85, 100))
FOUR = ((0, 0, 120), (95, 100, 160))
FIVE = ((115, 10, 5), (155, 85, 95))
SIX = ((0, 120, 120), (100, 165, 180))
SEVEN = ((160, 0, 0), (170, 115, 135))
EIGHT = ((165, 5, 10), (165, 100, 110))
FLAG = ((255, 0, 0), (265, 15, 25))

point: TypeAlias = tuple[float | int, ...]

def calcTupleVector(point1: point, point2: point) -> point:
    # get vector between two tuples
    return tuple(p2 - p1 for p1, p2 in zip(point1, point2))

def calcTupleDot(point1: point, point2: point) -> int|float:
    # calculate dot product between two tuples
    return  sum(p1*p2 for p1, p2 in zip(point1, point2))

def scaleTupleVector(vec: point, scale: float) -> tuple[float, ...]:
    # scale a tuple bu a float
    return tuple(axis * scale for axis in vec)

def getDistFromLine(linePoints: tuple[point, point], point: point) -> float:
    # check if actually a line
    if linePoints[0] == linePoints[1]:
        return math.dist(linePoints[0], point)
    
    # get vector and magnitude of line
    lineVector = calcTupleVector(*linePoints)
    lineMagnitude = math.dist(*linePoints)
    
    # get vector to point
    pointVector = calcTupleVector(linePoints[0], point)

    # calculate projection onto line
    projectionScale = calcTupleDot(pointVector, lineVector)/(lineMagnitude**2)

    # check if projection is on line
    if projectionScale <= 0:
        return math.dist(point, linePoints[0])
    elif projectionScale >= 1:
        return math.dist(point, linePoints[1])
    
    # calculate projected point
    scaledLineVector = scaleTupleVector(lineVector, projectionScale)
    projectedPoint = tuple(point + vec for point, vec in zip(linePoints[0], scaledLineVector))

    # return vector rejection
    return math.dist(point, projectedPoint)
    
def checkSquare(img: Image, coords: tuple[int, int], size: float) -> str:
    pixels = img.load()
    x, y = coords
    if getDistFromLine(GREY, pixels[round(x+size*0.25), round(y+size*0.4)]) < 10:
        # check 2
        if getDistFromLine(TWO, pixels[round(x+size*0.5), round(y+size*0.8)]) < 20:
            retVal = '2'
        # check 6
        elif getDistFromLine(SIX, pixels[round(x+size*0.45), round(y+size*0.55)]) < 20:
            retVal = '6'
        # check 4
        elif getDistFromLine(FOUR, pixels[round(x+size*0.75), round(y+size*0.65)]) < 20:
            retVal = '4'
        # check 1
        elif getDistFromLine(ONE, pixels[round(x+size*0.6), round(y+size*0.5)]) < 20:
            retVal = '1'
        # check 8
        elif getDistFromLine(EIGHT, pixels[round(x+size*0.4), round(y+size*0.65)]) < 20:
            retVal = '8'
        # check 7
        elif getDistFromLine(SEVEN, pixels[round(x+size*0.55), round(y+size*0.7)]) < 20:
            retVal = '7'
        # check 5
        elif getDistFromLine(FIVE, pixels[round(x+size*0.45), round(y+size*0.4)]) < 20:
            retVal = '5'
        # check 3
        elif getDistFromLine(THREE, pixels[round(x+size*0.7), round(y+size*0.4)]) < 20:
            retVal = '3'
        else:
            retVal = '0'
    else:
        # check for flag
        if getDistFromLine(FLAG, pixels[round(x+size*0.45), round(y+size*0.3)]) < 20:
            retVal = 'f'
        else:
            # unclicked square
            retVal = 'u'
    
    return retVal