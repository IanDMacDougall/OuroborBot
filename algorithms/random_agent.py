import random
from algorithms.base import BaseAgent
from game.snake import Direction, DIRECTION_VECTORS


class RandomAgent(BaseAgent):

    name = "Random"

    def __init__(self, grid_size: int):
        super().__init__(grid_size)
        self._rng = random.Random()

    def get_action(self, state: dict, game) -> Direction:
        head = tuple(state["head"])

        safe = [
            direction
            for direction, (dr, dc) in DIRECTION_VECTORS.items()
            if (head[0] + dr, head[1] + dc) in game.get_neighbors(head)
        ]

        return self._rng.choice(safe) if safe else Direction(state["direction"])

    def reset(self):
        pass