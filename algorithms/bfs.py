from algorithms.base import BaseAgent
from game.snake import Direction


class BFSAgent(BaseAgent):

    name = "BFS"

    #
    # Gets the next action based off the current state
    #
    def get_action(self, state: dict, game) -> Direction:
        head  = tuple(state["head"])
        food  = tuple(state["food"])
        snake = [tuple(s) for s in state["snake"]]

        path = self._bfs(head, food, game)
        if path and len(path) > 1: # path exists
            direct = game.pos_to_direction(head, path[1])
            return direct if direct is not None else Direction(state["direction"])
        
        return self._survival_move(head, snake, game, state)


    #
    # Returns a path using BFS
    # - looks like [start, ..., goal]
    # - None if unreachable
    #
    def _bfs(self, start, goal, game):
        queue = [[start]]
        visted = {start}

        while queue:
            path = queue.pop(0)
            node = path[-1]

            if node == goal:
                return path
            
            for neighbor in game.get_neighbors(node):
                if neighbor not in visted:  
                    visted.add(neighbor)
                    queue.append(path+[neighbor])

        return None




    def reset(self):
        pass