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
    get_hidden_neighbors,
    get_flagged_neighbors,
    get_revealed_neighbors,
    is_hidden,
    is_flagged,
    is_revealed,
    get_clue,
    AGENT_UNKNOWN,
    AGENT_FLAGGED,
    AGENT_EXPLODED_MINE,
)

# =========================================================================
# Section 1: Define First-Order Logic Terms (FOL Terms)
# =========================================================================
pyDatalog.create_terms(
    "R, C, R2, C2, N, H, "
    "Cell, Neighbor, "
    "Hidden, Flagged, Revealed, ExplodedMine, Clue, "
    "HiddenCount, FlaggedCount, RemainingMineCount, "
    "Safe, Mine"
)


_dynamic_facts = []


def _add_dynamic_fact(predicate_name, *arguments):
    """add a dynamic fact and remember it so it can be removed later."""
    pyDatalog.assert_fact(predicate_name, *arguments)
    _dynamic_facts.append((predicate_name, arguments))


def _clear_dynamic_facts():
    """remove all facts generated during the previous iteration."""
    for predicate_name, arguments in _dynamic_facts:
        pyDatalog.retract_fact(predicate_name, *arguments)

    _dynamic_facts.clear()


# =========================================================================
# Section 2: Generation of Logical Facts and Rules
# =========================================================================


def init_rules():
    """ Minesweeper inference rules."""
    _dynamic_facts.clear()

    Safe(R2, C2) <= (
        Revealed(R, C)
        & Clue(R, C, N)
        & FlaggedCount(R, C, N)
        & Neighbor(R, C, R2, C2)
        & Hidden(R2, C2)
    )

    Mine(R2, C2) <= (
        Revealed(R, C)
        & RemainingMineCount(R, C, H)
        & HiddenCount(R, C, H)
        & Neighbor(R, C, R2, C2)
        & Hidden(R2, C2)
    )


def update_knowledge_base(agent_board, rows, cols):
    """
    replaces the previous turn's dynamic facts with facts representing the current shadow-board state.
    """
    _clear_dynamic_facts()

    # Add current cell-state facts.
    for r in range(rows):
        for c in range(cols):
            value = agent_board[(r, c)]

            if value == AGENT_UNKNOWN:
                _add_dynamic_fact("Hidden", r, c)

            elif value == AGENT_FLAGGED:
                _add_dynamic_fact("Flagged", r, c)

            elif value == AGENT_EXPLODED_MINE:
                _add_dynamic_fact("ExplodedMine", r, c)

            elif is_revealed(agent_board, r, c):
                _add_dynamic_fact("Revealed", r, c)
                _add_dynamic_fact("Clue", r, c, value)

            else:
                raise ValueError(
                    f"Invalid shadow-board value {value!r} at cell {(r, c)}"
                )

    # add counts associated with every revealed clue
    for r in range(rows):
        for c in range(cols):
            if not is_revealed(agent_board, r, c):
                continue

            clue = get_clue(agent_board, r, c)

            hidden_neighbors = get_hidden_neighbors(
                agent_board,
                r,
                c,
                rows,
                cols,
            )

            flagged_neighbors = get_flagged_neighbors(
                agent_board,
                r,
                c,
                rows,
                cols,
            )

            hidden_count = len(hidden_neighbors)
            flagged_count = len(flagged_neighbors)
            remaining_mine_count = clue - flagged_count

            # incorrect flag configuration
            if remaining_mine_count < 0:
                warnings.warn(
                    f"Cell {(r, c)} has clue {clue}, but "
                    f"{flagged_count} neighboring cells are flagged.",
                    RuntimeWarning,
                    stacklevel=2,
                )

            if remaining_mine_count > hidden_count:
                warnings.warn(
                    f"Cell {(r, c)} requires {remaining_mine_count} more mines, "
                    f"but only {hidden_count} hidden neighbors remain.",
                    RuntimeWarning,
                    stacklevel=2,
                )

            _add_dynamic_fact(
                "HiddenCount",
                r,
                c,
                hidden_count,
            )

            _add_dynamic_fact(
                "FlaggedCount",
                r,
                c,
                flagged_count,
            )

            _add_dynamic_fact(
                "RemainingMineCount",
                r,
                c,
                remaining_mine_count,
            )
def query_solver():
    """
    query pyDatalog for cells inferred to be safe or mines.
    """
    safe_set = {
        (int(row), int(col))
        for row, col in list(Safe(R, C))
    }

    mine_set = {
        (int(row), int(col))
        for row, col in list(Mine(R, C))
    }

    conflicts = safe_set & mine_set

    if conflicts:
        warnings.warn(
            "Contradictory deductions detected for cells: "
            f"{sorted(conflicts)}. "
            "Check the current flags and knowledge-base facts.",
            RuntimeWarning,
            stacklevel=2,
        )

        # do not perform an unsafe action on a contradictory cell, edge case handler
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
    ms = MineSweeper(rows=9, cols=9, mines=9, seed=99, auto_flood_fill=False)
    prolog_solver(ms)