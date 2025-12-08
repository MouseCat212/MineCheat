import math
from PIL import Image

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

def getPixelDifference(px1: tuple[int, int, int], px2: tuple[int, int, int]) -> float:
    return math.sqrt(float(px1[0]-px2[0])**2 + float(px1[1]-px2[1])**2 + float(px1[2]-px2[2])**2)

def getDistFromLine(linePx: tuple[tuple[int, int, int], tuple[int, int, int]], point: tuple[int, int, int]) -> float:
    a = getPixelDifference(linePx[0], point)
    b = getPixelDifference(linePx[1], point)
    c = getPixelDifference(*linePx)

    if linePx[0] == linePx[1]:
        return a
    
    alpha = math.acos(((b*b)+(c*c)-(a*a))/(2*b*c))
    beta = math.acos(((a*a)+(c*c)-(b*b))/(2*a*c))
    
    if alpha >= (math.pi/2):
        return b
    elif beta >= (math.pi/2):
        return a
    else:
        return b*math.sin(alpha)
    
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