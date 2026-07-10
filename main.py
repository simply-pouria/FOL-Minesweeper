import pygame
import time
import random
from pyDatalog import pyDatalog
from src.minesweeper import MineSweeper
from src.environment_manager import (
    init_static_facts,
    create_agent_board,
    record_start_cell,
    reveal_cell,
    flag_cell,
    unflag_cell,
    get_hidden_neighbers,
    get_flagged_neighbers,
    get_revealed_neighbers,
    is_hidden,
    is_flagged,
    is_revealed,
    get_clue,
    AGENT_UNKNOWN,
    AGENT_FLAGGED,
)

# =========================================================================
# Section 1: Define First-Order Logic Terms (FOL Terms)
# Students should define the required terms, facts, and rules for pyDatalog here.
# =========================================================================
# Hint: pyDatalog.create_terms('X, Y, R, C, ...')

pyDatalog.create_terms(
    'R, C, R2, C2, N, H, '
    'Cell, neighber, Hidden, Flagged, Revealed, Clue, '
    'HiddenCount, FlaggedCount, RemainingMineCount, '
    'Safe, Mine'
)

_dynamic_facts = []


def _add_dynamic_fact(predicate_name, *arguments):
    pyDatalog.assert_fact(predicate_name, *arguments)
    _dynamic_facts.append((predicate_name, arguments))


def _clear_dynamic_facts():
    for predicate_name, arguments in _dynamic_facts:
        pyDatalog.retract_fact(predicate_name, *arguments)

    _dynamic_facts.clear()


# Suggested constants for the agent's internal memory (Shadow Board)
AGENT_UNKNOWN = -1
AGENT_FLAGGED = -2

# =========================================================================
# Section 2: Generation of Logical Facts and Rules
# =========================================================================


def init_rules():
    """
    Task 2: Define logical inference rules (Safety Rule and Danger Rule).
    According to the project documentation, rules must be defined based on first-order logic.
    """
    # Safe(R2, C2) <= (...)
    # Mine(R2, C2) <= (...)

    _dynamic_facts.clear()

    Safe(R2, C2) <= (
            Revealed(R, C)
            & Clue(R, C, N)
            & FlaggedCount(R, C, N)
            & neighber(R, C, R2, C2)
            & Hidden(R2, C2)
    )

    Mine(R2, C2) <= (
            Revealed(R, C)
            & RemainingMineCount(R, C, H)
            & HiddenCount(R, C, H)
            & neighber(R, C, R2, C2)
            & Hidden(R2, C2)
    )


def update_knowledge_base(agent_board, rows, cols):
    """
    Task 3: Convert the agent's internal memory (agent_board) into dynamic facts in each turn.
    Before adding new facts, facts from the previous turn must be cleared.
    """

    _clear_dynamic_facts()

    for r in range(rows):
        for c in range(cols):
            value = agent_board[(r, c)]

            if value == AGENT_UNKNOWN:
                _add_dynamic_fact('Hidden', r, c)

            elif value == AGENT_FLAGGED:
                _add_dynamic_fact('Flagged', r, c)

            else:
                _add_dynamic_fact('Revealed', r, c)
                _add_dynamic_fact('Clue', r, c, value)

    for r in range(rows):
        for c in range(cols):
            if not is_revealed(agent_board, r, c):
                continue

            clue = get_clue(agent_board, r, c)

            hidden_neighbors = get_hidden_neighbers(
                agent_board,
                r,
                c,
                rows,
                cols,
            )

            flagged_neighbors = get_flagged_neighbers(
                agent_board,
                r,
                c,
                rows,
                cols,
            )

            hidden_count = len(hidden_neighbors)
            flagged_count = len(flagged_neighbors)
            remaining_mine_count = clue - flagged_count

            _add_dynamic_fact(
                'HiddenCount',
                r,
                c,
                hidden_count,
            )

            _add_dynamic_fact(
                'FlaggedCount',
                r,
                c,
                flagged_count,
            )

            _add_dynamic_fact(
                'RemainingMineCount',
                r,
                c,
                remaining_mine_count,
            )


def query_solver():
    """
    Task 4: Query the inference engine to find safe cells and mines.
    Output: Two lists containing the coordinates of safe cells and mine cells.
    """
    safe_moves = []
    mine_moves = []

    # Code for querying Safe(R, C) and Mine(R, C)

    safe_answers = list(Safe(R, C))
    mine_answers = list(Mine(R, C))

    safe_set = {
        (int(row), int(col))
        for row, col in safe_answers
    }

    mine_set = {
        (int(row), int(col))
        for row, col in mine_answers
    }

    conflicts = safe_set & mine_set

    safe_set -= conflicts
    mine_set -= conflicts

    safe_moves = sorted(safe_set)
    mine_moves = sorted(mine_set)

    return safe_moves, mine_moves


# =========================================================================
# Section 3: Uncertainty Handling Strategy (Smart Guess) - Optional/Bonus
# =========================================================================

def get_safest_guess(agent_board, rows, cols):
    """
    Task 5 (Optional): Calculate the probability of cells being mines during a logical deadlock.
    """
    return None


# =========================================================================
# Section 4: Main Agent Loop
# =========================================================================

def prolog_solver(game):
    # Initialize static facts and rules
    init_static_facts(game.rows, game.cols)
    init_rules()

    # Create agent's internal memory (Shadow Board) - initially all cells are unknown
    agent_board = create_agent_board(game.rows, game.cols)
    start_r, start_c = record_start_cell(game, agent_board)
    print(f"Starting at guaranteed safe position: {start_r}, {start_c}")

    running = True
    while running and not game.game_over:
        # Handle Pygame events to prevent the window from freezing/crashing
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 1. Update the knowledge base based on the latest state of the agent's memory
        update_knowledge_base(agent_board, game.rows, game.cols)

        # 2. Query the logic engine
        safe_moves, mine_moves = query_solver()
        move_made = False

        # 3. Apply the extracted logical actions to the game environment and update memory
        # Hint: Reveal safe cells first, then flag the mine cells.

        # 4. Deadlock management (if no deterministic logical move is found)
        if not move_made and not game.game_over:
            print("Logical deadlock! Attempting guess...")
            # First use the Heuristic, and if no data is available, make a completely random choice
            pass

        # Render the environment and add a short delay to observe the solving process
        game.render()
        time.sleep(0.2)

    # Keep the window open after the game ends
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        game.render()


if __name__ == "__main__":
    # Default settings based on the first scenario (Simple level) in the evaluation table
    # Note: auto_flood_fill must be False to preserve the encapsulation of the agent's memory.
    ms = MineSweeper(rows=9, cols=9, mines=10, seed=99, auto_flood_fill=False)
    prolog_solver(ms)