from PIL import Image
from statistics import mean

from functions import getPixelDifference

import time

DIFFERENCE_DIFF = 50
BLACK_DIFF = 125
PX_BUFFER = 15

def getGameGrid(img: Image.Image) -> tuple[int, int, float, int, int, int, int]:
    """
    Docstring for getGameGrid
    
    :param img: The screenshot of minesweeper
    :type img: Image
    :return: Tuple of:\n
        \twidth: in squares\n
        \theight: in squares\n
        \tsquare side length: in pixels\n
        \ttopmost bound: in pixels from top\n
        \tbottommost bound: in pixels from top\n
        \tleftmost bound: in pixels from left\n
        \trightmost bound: in pixels from left\n
    :rtype: tuple[int, int, float, int, int, int, int]
    """
    pixels = img.load() # load for faster pixel access
    
    # check if centre of image is on black, move if is
    cent = (round(img.size[0]/2),round(img.size[1]/2))
    px = pixels[cent]

    # go to black, then once more
    try:
        while getPixelDifference(px, (0, 0, 0)) > 50:
            cent = (cent[0] + 10, cent[1] + 10)
            px = pixels[cent]
        cent = (cent[0] + 10, cent[1] + 10)
        pixels[cent] # ensure still in image bounds
    except IndexError:
        # in case overruns image bounds, default to centre
        cent = (round(img.size[0]/2),round(img.size[1]/2))


    # get leftmost and rightmost bounds
    line1: list[int] = []
    px = pixels[0, cent[1]]
    lastPx: tuple = px
    for i in range(1, img.size[0]):
        px = pixels[i, cent[1]]
        # check if this pixel is significantly different from the last, and if it's close enough to black
        if getPixelDifference(px, lastPx) > DIFFERENCE_DIFF and getPixelDifference(px, (0, 0, 0)) < BLACK_DIFF:
            # check if this pixel is within buffer distance of the last edge pixel
            if len(line1) < 1 or i - line1[-1] > PX_BUFFER:
                line1.append(i)
        lastPx = px

    # get topmost and bottommost bounds
    line2: list[int] = []
    px = pixels[cent[0], 0]
    lastPx: tuple = px
    for i in range(1, img.size[1]):
        px = pixels[cent[0], i]
        # check if this pixel is significantly different from the last, and if it's close enough to black
        if getPixelDifference(px, lastPx) > DIFFERENCE_DIFF and getPixelDifference(px, (0, 0, 0)) < BLACK_DIFF:
            # check if this pixel is within buffer distance of the last edge pixel
            if len(line2) < 1 or i - line2[-1] > PX_BUFFER:
                line2.append(i)
        lastPx = px

    # filter outliers to remove black bars to sides of screen when playing in fullscreen
    line1Dists: list[int] = []
    line2Dists: list[int] = []
    for i in range(1, len(line1)):
        line1Dists.append(line1[i] - line1[i-1])
    for i in range(1, len(line2)):
        line2Dists.append(line2[i] - line2[i-1])

    lineDists = line1Dists + line2Dists
    meanDist = mean(lineDists)

    # only care about too big outliers
    line1Outliers = [_ for _ in line1Dists if _ > 1.25*meanDist]

    indexToRemove: set = set()
    distIndexToRemove: set = set()
    for i in range(len(line1Dists)):
        if line1Dists[i] in line1Outliers:
            distIndexToRemove.add(i)
            if i == 0:
                indexToRemove.add(i)
            elif i == len(line1Dists) - 1:
                indexToRemove.add(i + 1)

    for index in reversed(sorted(indexToRemove)):
        line1.pop(index)
    for index in reversed(sorted(distIndexToRemove)):
        line1Dists.pop(index)

    # get dists removing any broken ones
    dists = line1Dists + line2Dists
    distsMean = mean(dists)
    goodDists = [_ for _ in dists if _ <= distsMean*1.1 and _ >= distsMean*0.9]
    boxSide = mean(goodDists)

    # get width and height of grid
    width = round((line1[-1]-line1[0])/boxSide)
    height = round((line2[-1]-line2[0])/boxSide)

    # recalculate boxside to allow for some errors with detection
    boxSide = (((line1[-1]-line1[0])/width) + ((line2[-1]-line2[0])/height))/2

    return (width, height, boxSide, line2[0], line2[-1], line1[0], line1[-1])

if __name__ == "__main__":
    img = Image.open("out.png")
    gridData = getGameGrid(img)
    print("width: {}, height: {}, boxSide: {}, top: {}, bottom: {}, left: {}, right: {}".format(*gridData))