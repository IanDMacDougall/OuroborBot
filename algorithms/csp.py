from collections import deque
from algorithms.base import BaseAgent
from game.snake import Direction


class CSPAgent(BaseAgent):

    name = "CSP"

    # Minimum free-space ratio before a move is considered critical.
    # A move is rejected if it leaves fewer than (body_length * SPACE_RATIO)
    # reachable cells.
    SPACE_RATIO = 0.5

    def get_action(self, state: dict, game) -> Direction:
        head = tuple(state["head"])
        food = tuple(state["food"])
        snake = [tuple(s) for s in state["snake"]]
        current_dir = Direction(state["direction"])

        # Step 1: Domain reduction (C1)
        # get_neighbors already removes wall and body collisions.
        candidates = game.get_neighbors(head)

        if not candidates:
            return current_dir

        # Step 2: Forward checking (C2, C3, C4)
        scored = []
        for nb in candidates:
            direction = game.pos_to_direction(head, nb)
            if direction is None:
                continue
            score = self._evaluate(nb, food, snake, game)
            if score is not None:
                scored.append((score, nb, direction))

        if scored:
            scored.sort(reverse=True)
            return scored[0][2]

        # Step 3: All moves failed constraints — survival only
        best = max(
            candidates,
            key=lambda nb: self._flood_fill(nb, set(snake[:-1]), game)
        )
        direct = game.pos_to_direction(head, best)
        return direct if direct is not None else current_dir


    #
    # Constraint evaluation
    #
    def _evaluate(self, next_pos, food, snake, game):
        # Simulate the snake after taking this step (tail vacates)
        sim_snake = [next_pos] + snake[:-1]
        blocked = set(sim_snake)

        # C2: Sufficient reachable space
        space = self._flood_fill(next_pos, blocked - {next_pos}, game)
        min_space = int(len(snake) * self.SPACE_RATIO)

        if space < min_space:
            return None          # critical constraint, reject move

        # C3 / C4: Food path and post-eat escape
        eating = (next_pos == food)

        if eating:
            # C4: After eating, snake grows, can we still reach the tail?
            sim_grown = [next_pos] + snake   # tail does NOT shrink on eat
            tail = sim_grown[-1]
            if not self._bfs_reachable(next_pos, tail, set(sim_grown[:-1]), game):
                if space < len(snake) + 2:
                    return None  # eating here would likely trap us
        else:
            # C3: A path to food should still be reachable
            has_food_path = self._bfs_reachable(next_pos, food, blocked, game)
            if not has_food_path:
                # Soft constraint, penalise heavily but don't eliminate.
                # The snake can survive without food access if it has
                # enough space to outlast the situation.
                space = space // 4

        # MRV score
        food_dist = abs(next_pos[0] - food[0]) + abs(next_pos[1] - food[1])
        return space * 10 - food_dist

    #
    # Helpers
    #

    #
    # Return True if goal is reachable
    #
    def _bfs_reachable(self, start, goal, blocked, game) -> bool:
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