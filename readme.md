# MineCheat
A minesweeper solver made for windows 7 minesweeper.

## Installation
Clone repository and install requirements.
```sh
git clone https://github.com/MouseCat212/MineCheat.git
pip install -r requirements.txt
```

## Usage
Open minesweeper. Ensure that the board is set to silver and blue under appearance options. Mine type does not matter.

Run the main program, ideally before revealing any squares, to set the width, height and borders of the board. The program will not show an image if no squares are revealed.
```sh
python main.py
```
It should work if a few squares have been revealed, however edge detection accuracy decreases the more of the board has been revealed.
If detection is funky (obvious by position of marked squares and percentages), the width and height (in squares) can be specified manually by passing them to the program like so:
```sh
python main.py width height
```
If detection is still funky, the borders of the board (in pixels from the top left of the window) can be passed like so:
```sh
python main.py width height left top right bottom
```
These values can be obtained by running getScreenshot.py and opening the resulting `out.png`. Values are taken from the leftmost bound of the black line (for left/right) or the topmost (for top/bottom).

After each player turn (revealing new squares) press enter on the keyboard to re-analyse the board and solve for new mines.  
The program will open an image in your default image viewer with definite mines marked with a red square, definite safe squares marked with a green square, and other squares marked with the percentage chance of a mine being there.  
To restart a game with the same size board enter 'r', to quit the program enter 'n'.