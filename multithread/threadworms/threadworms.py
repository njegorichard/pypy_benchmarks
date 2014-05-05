# Threadworms (a Python/Pygame threading demonstration)
# By Al Sweigart al@inventwithpython.com
# http://inventwithpython.com/blog
# Released under a "Simplified BSD" license

# This is meant to be an educational example of multithreaded programming,
# so I get kind of verbose in the comments.

from common.abstract_threading import atomic, Future, print_abort_info
import time
import random, sys, threading

# Setting up constants
CELLS_WIDE = 1000 # how many cells wide the grid is
CELLS_HIGH = 1000 # how many cells high the grid is
GRID = []
NUM_STEPS = 0
MAX_WORM_SIZE = 5


UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'

HEAD = 0
BUTT = -1 # negative indexes count from the end, so -1 will always be the last index


class Worm(threading.Thread): # "Thread" is a class in the "threading" module.
    def __init__(self, name='Worm', maxsize=MAX_WORM_SIZE, color=None):
        threading.Thread.__init__(self)
        self.name = name
        self.rnd = random.Random()
        self.maxsize = maxsize

        if color is None:
            self.color = (random.randint(60, 255), random.randint(60, 255), random.randint(60, 255))
        else:
            self.color = color

        # GRID_LOCK.acquire() # block until this thread can acquire the lock
        with atomic:
            while True:
                startx = random.randint(0, CELLS_WIDE - 1)
                starty = random.randint(0, CELLS_HIGH - 1)
                if GRID[startx][starty] is None:
                    break # we've found an unoccupied cell in the grid

            GRID[startx][starty] = self.color # modify the shared data structure
        # GRID_LOCK.release()


        self.body = [{'x': startx, 'y': starty}]
        self.direction = random.choice((UP, DOWN, LEFT, RIGHT))


    def run(self):
        for _ in range(NUM_STEPS):
            if self.rnd.randint(0, 100) < 20: # 20% to change direction
                self.direction = self.rnd.choice((UP, DOWN, LEFT, RIGHT))

            with atomic:
                print_abort_info(0.01)
                # GRID_LOCK.acquire() # don't return (that is, block) until this thread can acquire the lock

                nextx, nexty = self.getNextPosition()
                if nextx in (-1, CELLS_WIDE) or nexty in (-1, CELLS_HIGH) or GRID[nextx][nexty] is not None:
                    self.direction = self.getNewDirection()
                    if self.direction is None:
                        self.body.reverse() # Now the head is the butt and the butt is the head. Magic!
                        self.direction = self.getNewDirection()

                    if self.direction is not None:
                        nextx, nexty = self.getNextPosition()

                if self.direction is not None:
                    GRID[nextx][nexty] = self.color # update the GRID state
                    self.body.insert(0, {'x': nextx, 'y': nexty}) # update this worm's own state

                    if len(self.body) > self.maxsize:
                        GRID[self.body[BUTT]['x']][self.body[BUTT]['y']] = None # update the GRID state
                        del self.body[BUTT] # update this worm's own state (heh heh, worm butt)
                else:
                    self.direction = self.rnd.choice((UP, DOWN, LEFT, RIGHT)) # can't move, so just do nothing for now but set a new random direction

            # GRID_LOCK.release()


    def getNextPosition(self):
        if self.direction == UP:
            nextx = self.body[HEAD]['x']
            nexty = self.body[HEAD]['y'] - 1
        elif self.direction == DOWN:
            nextx = self.body[HEAD]['x']
            nexty = self.body[HEAD]['y'] + 1
        elif self.direction == LEFT:
            nextx = self.body[HEAD]['x'] - 1
            nexty = self.body[HEAD]['y']
        elif self.direction == RIGHT:
            nextx = self.body[HEAD]['x'] + 1
            nexty = self.body[HEAD]['y']
        else:
            assert False, 'Bad value for self.direction: %s' % self.direction

        return nextx, nexty


    def getNewDirection(self):
        x = self.body[HEAD]['x'] # syntactic sugar, makes the code below more readable
        y = self.body[HEAD]['y']

        newDirection = []
        if y - 1 not in (-1, CELLS_HIGH) and GRID[x][y - 1] is None:
            newDirection.append(UP)
        if y + 1 not in (-1, CELLS_HIGH) and GRID[x][y + 1] is None:
            newDirection.append(DOWN)
        if x - 1 not in (-1, CELLS_WIDE) and GRID[x - 1][y] is None:
            newDirection.append(LEFT)
        if x + 1 not in (-1, CELLS_WIDE) and GRID[x + 1][y] is None:
            newDirection.append(RIGHT)

        if newDirection == []:
            return None # None is returned when there are no possible ways for the worm to move.

        return self.rnd.choice(newDirection)

def run(worms=2, steps=10000000):
    global DISPLAYSURF, NUM_WORMS, NUM_STEPS, GRID
    NUM_WORMS = int(worms)
    NUM_STEPS = int(steps) // NUM_WORMS

    # using a deque instead of a list is kind of cheating
    # since it is a linked list of blocks. This means
    # that there are less conflicts.
    # So maybe remove this again when we support array-barriers in STM
    import collections
    list_to_use = collections.deque #list

    GRID = list_to_use()
    for x in range(CELLS_WIDE):
        GRID.append(list_to_use([None] * CELLS_HIGH))
#GRID_LOCK = threading.Lock() # pun was not intended

    # Draw some walls on the grid
#     squares = """
# ...........................
# ...........................
# ...........................
# .H..H..EEE..L....L.....OO..
# .H..H..E....L....L....O..O.
# .HHHH..EE...L....L....O..O.
# .H..H..E....L....L....O..O.
# .H..H..EEE..LLL..LLL...OO..
# ...........................
# .W.....W...OO...RRR..MM.MM.
# .W.....W..O..O..R.R..M.M.M.
# .W..W..W..O..O..RR...M.M.M.
# .W..W..W..O..O..R.R..M...M.
# ..WW.WW....OO...R.R..M...M.
# ...........................
# ...........................
# """
    #setGridSquares(squares)

    # Create the worm objects.
    worms = [] # a list that contains all the worm objects
    parallel_time = time.time()
    for i in range(NUM_WORMS):
        worms.append(Worm())
    for w in worms:
        w.start() # Start the worm code in its own thread.

    for t in worms:
        t.join()
    parallel_time = time.time() - parallel_time
    return parallel_time



def setGridSquares(squares, color=(192, 192, 192)):
    squares = squares.split('\n')
    if squares[0] == '':
        del squares[0]
    if squares[-1] == '':
        del squares[-1]

    with atomic:
        # GRID_LOCK.acquire()
        for y in range(min(len(squares), CELLS_HIGH)):
            for x in range(min(len(squares[y]), CELLS_WIDE)):
                if squares[y][x] == ' ':
                    GRID[x][y] = None
                elif squares[y][x] == '.':
                    pass
                else:
                    GRID[x][y] = color
        # GRID_LOCK.release()




if __name__ == '__main__':
    run()
