from abc import ABC, abstractmethod
from game.snake import Direction


class BaseAgent(ABC):

    name: str = "Base Agent"

    def __init__(self, grid_size: int):
        self.grid_size = grid_size


    @abstractmethod
    def get_action(self, state: dict, game) -> Direction:
        """
        Choose the next move given the current game state

        Returns a Direction
        """


    def reset(self):
        """Called when the snake dies and a new game begins. Override if stateful."""


    def _survival_move(self, head, snake, game, state) -> Direction:
        """
        Fallback when no path to food exists.
        Picks the neighbour with the most reachable open space.
        """
        neighbours = game.get_neighbors(head)
        if not neighbours:
            return Direction(state["direction"])
 
        best_dir, best_space = None, -1
        for nb in neighbours:
            space = self._flood_fill(nb, set(snake), game)
            if space > best_space:
                best_space = space
                best_dir = game.pos_to_direction(head, nb)
 
        return best_dir if best_dir is not None else Direction(state["direction"])


    def _flood_fill(self, start, blocked, game) -> int:
        """Count cells reachable from start without crossing blocked."""
        visited = {start}
        queue   = [[start]]
        while queue:
            node = queue.pop(0)
            for nb in game.get_all_neighbors(node):
                if nb not in visited and nb not in blocked:
                    visited.add(nb)
                    queue.append(nb)
        return len(visited)
    
    