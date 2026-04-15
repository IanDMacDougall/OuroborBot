import random
from collections import namedtuple
from enum import IntEnum

#
# Direction constants
#
class Direction(IntEnum):
    UP    = 0
    RIGHT = 1
    DOWN  = 2
    LEFT  = 3

# Velocity vectors for each direction (row_delta, col_delta)
DIRECTION_VECTORS = {
    Direction.UP:    (-1,  0),
    Direction.RIGHT: ( 0,  1),
    Direction.DOWN:  ( 1,  0),
    Direction.LEFT:  ( 0, -1),
}

# Directions that are legal given the current heading (can't reverse)
LEGAL_TURNS = {
    Direction.UP:    [Direction.UP,    Direction.RIGHT, Direction.LEFT],
    Direction.RIGHT: [Direction.RIGHT, Direction.UP,    Direction.DOWN],
    Direction.DOWN:  [Direction.DOWN,  Direction.RIGHT, Direction.LEFT],
    Direction.LEFT:  [Direction.LEFT,  Direction.UP,    Direction.DOWN],
}

#
# Named result returned by step()
#
StepResult = namedtuple(
    "StepResult",
    ["alive", "ate_food", "score", "length", "steps", "cause_of_death"]
)

#
# Cell values used by get_grid()
#
CELL_EMPTY  = 0
CELL_FOOD   = 1
CELL_HEAD   = 2
CELL_BODY   = 3

#
# SnakeGame
#
class SnakeGame:
    """
    Manages a single Snake game instance.

    Grid coordinates: (row, col), origin at top-left.
    Snake stored as a list of (row, col) tuples, head at index 0.
    """

    def __init__(self, grid_size: int = 20, seed: int | None = None):
        self.grid_size = grid_size
        self._rng = random.Random(seed)
        self.reset()

    #
    # Public API
    #

    def reset(self):
        """Restart the game from scratch."""
        mid = self.grid_size // 2

        # Snake starts as 3 cells pointing upward from the centre
        self.snake: list[tuple[int, int]] = [
            (mid,     mid),
            (mid + 1, mid),
            (mid + 2, mid),
        ]
        self.direction  = Direction.UP
        self.score      = 0
        self.steps      = 0
        self.alive      = True
        self.cause_of_death: str | None = None

        self.food = self._place_food()

    def step(self, action: Direction) -> StepResult:
        """
        Advance the game by one tick.

        Parameters
        ----------
        action : Direction
            The move chosen by the algorithm.  Illegal reversal moves are
            silently replaced with the current heading.

        Returns
        -------
        StepResult namedtuple
        """
        if not self.alive:
            return self._result(ate_food=False)

        # Ignore 180-degree reversals
        if action not in LEGAL_TURNS[self.direction]:
            action = self.direction
        self.direction = action

        dr, dc = DIRECTION_VECTORS[action]
        head_r, head_c = self.snake[0]
        new_head = (head_r + dr, head_c + dc)

        # Collision: wall
        if not self._in_bounds(new_head):
            self.alive = False
            self.cause_of_death = "wall"
            return self._result(ate_food=False)

        # Collision: self
        # Exclude the tail because it will move away this tick
        if new_head in self.snake[:-1]:
            self.alive = False
            self.cause_of_death = "self"
            return self._result(ate_food=False)

        ate_food = new_head == self.food

        # Move snake
        self.snake.insert(0, new_head)
        if ate_food:
            self.score += 1
            self.food = self._place_food()
        else:
            self.snake.pop()  # remove tail

        self.steps += 1
        return self._result(ate_food=ate_food)

    def get_state(self) -> dict:
        """
        Return a serialisable snapshot of the entire game state.
        Used by algorithms to decide a move, and by the server to
        push updates to the browser.
        """
        return {
            "grid_size":      self.grid_size,
            "snake":          list(self.snake),        # [(r,c), ...]
            "head":           self.snake[0],
            "tail":           self.snake[-1],
            "food":           self.food,
            "direction":      int(self.direction),
            "score":          self.score,
            "length":         len(self.snake),
            "steps":          self.steps,
            "alive":          self.alive,
            "cause_of_death": self.cause_of_death,
            "grid":           self.get_grid(),         # 2-D list of CELL_* ints
        }

    def get_grid(self) -> list[list[int]]:
        """
        Return a 2-D grid (list of rows) with CELL_* integer values.
        Useful for algorithms that want a spatial view of the board.
        """
        g = self.grid_size
        grid = [[CELL_EMPTY] * g for _ in range(g)]

        for r, c in self.snake[1:]:
            grid[r][c] = CELL_BODY
        hr, hc = self.snake[0]
        grid[hr][hc] = CELL_HEAD
        fr, fc = self.food
        grid[fr][fc] = CELL_FOOD

        return grid

    def get_neighbors(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        """
        Return all in-bounds, non-body cells adjacent to pos.
        Useful for pathfinding algorithms.
        """
        r, c = pos
        neighbors = []
        for dr, dc in DIRECTION_VECTORS.values():
            nr, nc = r + dr, c + dc
            if self._in_bounds((nr, nc)) and (nr, nc) not in self.snake[:-1]:
                neighbors.append((nr, nc))
        return neighbors

    def get_all_neighbors(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        """
        Return all in-bounds cells adjacent to pos regardless of snake body.
        Useful for algorithms like Hamiltonian that build paths over the full grid.
        """
        r, c = pos
        neighbors = []
        for dr, dc in DIRECTION_VECTORS.values():
            nr, nc = r + dr, c + dc
            if self._in_bounds((nr, nc)):
                neighbors.append((nr, nc))
        return neighbors

    def get_free_cells(self) -> list[tuple[int, int]]:
        """Return all cells not occupied by the snake."""
        snake_set = set(self.snake)
        return [
            (r, c)
            for r in range(self.grid_size)
            for c in range(self.grid_size)
            if (r, c) not in snake_set
        ]

    def pos_to_direction(
        self, from_pos: tuple[int, int], to_pos: tuple[int, int]
    ) -> Direction | None:
        """Convert an adjacent (from, to) pair into a Direction, or None if non-adjacent."""
        dr = to_pos[0] - from_pos[0]
        dc = to_pos[1] - from_pos[1]
        for direction, (vr, vc) in DIRECTION_VECTORS.items():
            if dr == vr and dc == vc:
                return direction
        return None

    # 
    # Internal helpers
    # 

    def _in_bounds(self, pos: tuple[int, int]) -> bool:
        r, c = pos
        return 0 <= r < self.grid_size and 0 <= c < self.grid_size

    def _place_food(self) -> tuple[int, int]:
        """Randomly place food on an empty cell."""
        free = self.get_free_cells()
        if not free:
            # Board is completely full — the snake has won
            return (-1, -1)
        return self._rng.choice(free)

    def _result(self, ate_food: bool) -> StepResult:
        return StepResult(
            alive=self.alive,
            ate_food=ate_food,
            score=self.score,
            length=len(self.snake),
            steps=self.steps,
            cause_of_death=self.cause_of_death,
        )