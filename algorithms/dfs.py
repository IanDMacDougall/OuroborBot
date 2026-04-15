from algorithms.base import BaseAgent
from game.snake import Direction


class DFSAgent(BaseAgent):

    name = "DFS"

    def get_action(self, state: dict, game) -> Direction:
        head  = tuple(state["head"])
        food  = tuple(state["food"])
        snake = [tuple(s) for s in state["snake"]]

        path = self._dfs(head, food, snake, game)

        if path and len(path) > 1:
            direct = game.pos_to_direction(head, path[1])
            return direct if direct is not None else Direction(state["direction"])

        # Fall Back
        return self._survival_move(head, snake, game, state)

    #
    # returns full path [start, ..., goal]
    # - None if unreachable
    #
    def _dfs(self, start, goal, snake, game):
        stack   = [(start, [start])]
        visited = {start}

        while stack:
            node, path = stack.pop() 

            if node == goal:
                return path

            # Push neighbours in reverse order so the first neighbour
            # is explored first (matches intuitive DFS direction order).
            for nb in reversed(game.get_neighbors(node)):
                if nb not in visited:
                    visited.add(nb)
                    stack.append((nb, path + [nb]))

        return None

    def reset(self):
        pass