import heapq
from collections import deque
from algorithms.base import BaseAgent
from game.snake import Direction


class AStarAgent(BaseAgent):

    name = "A*"

    def get_action(self, state: dict, game) -> Direction:
        head = tuple(state["head"])
        food = tuple(state["food"])
        snake = [tuple(s) for s in state["snake"]]

        path = self._astar(head, food, snake, game)
        if path and len(path) > 1 and self._safe_to_follow(path, snake, game):
            direct = game.pos_to_direction(head, path[1])
            return direct if direct is not None else Direction(state["direction"])

        tail_path = self._astar(head, snake[-1], snake, game)
        if tail_path and len(tail_path) > 1:
            direct = game.pos_to_direction(head, tail_path[1])
            return direct if direct is not None else Direction(state["direction"])

        return self._survival_move(head, snake, game, state)


    #
    # Returns a path using Astar
    # - looks like [start, ..., goal]
    # - None if unreachable
    #
    def _astar(self, start, goal, snake, game):
        def h(pos):
            return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])

        heap = [(h(start), 0, start, [start])]
        visited = {}

        while heap:
            f, g, node, path = heapq.heappop(heap)

            if node == goal:
                return path

            if visited.get(node, float('inf')) <= g:
                continue
            visited[node] = g

            for nb in game.get_neighbors(node):
                new_g = g + 1
                if visited.get(nb, float('inf')) > new_g:
                    heapq.heappush(heap, (new_g + h(nb), new_g, nb, path + [nb]))

        return None


    #
    # Simulate following path to food
    # 
    def _safe_to_follow(self, path, snake, game) -> bool:
        sim = list(snake)
        for step in path[1:]:
            sim.insert(0, step)
            sim.pop()
        return self._reachable(sim[0], sim[-1], set(sim[:-1]), game)

    #
    # reachability check
    #
    def _reachable(self, start, goal, blocked, game) -> bool:
        if start == goal:
            return True
        visited = {start}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for nb in game.get_all_neighbors(node):
                if nb == goal:
                    return True
                if nb not in visited and nb not in blocked:
                    visited.add(nb)
                    queue.append(nb)
        return False


    def reset(self):
        pass