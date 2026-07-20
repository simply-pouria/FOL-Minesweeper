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
import sys
import warnings

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
    hidden_cells = [
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if is_hidden(agent_board, r, c)
    ]

    if not hidden_cells:
        return None

    risk_samples = {cell: [] for cell in hidden_cells}
    constraint_risks = []

    for r in range(rows):
        for c in range(cols):
            if not is_revealed(agent_board, r, c):
                continue

            hidden_neighbors = get_hidden_neighbors(
                agent_board, r, c, rows, cols
            )

            if not hidden_neighbors:
                continue

            flagged_count = len(
                get_flagged_neighbors(agent_board, r, c, rows, cols)
            )

            remaining_mines = get_clue(agent_board, r, c) - flagged_count
            remaining_mines = max(
                0,
                min(remaining_mines, len(hidden_neighbors)),
            )

            risk = remaining_mines / len(hidden_neighbors)
            constraint_risks.append(risk)

            for cell in hidden_neighbors:
                risk_samples[cell].append(risk)

    if not constraint_risks:
        return random.choice(hidden_cells)

    baseline_risk = sum(constraint_risks) / len(constraint_risks)
    scores = {}

    for cell in hidden_cells:
        samples = risk_samples[cell]

        if samples:
            scores[cell] = (max(samples), -len(samples))
        else:
            scores[cell] = (baseline_risk, 0)

    best_score = min(scores.values())
    best_cells = [
        cell
        for cell, score in scores.items()
        if score == best_score
    ]

    return random.choice(best_cells)
# =========================================================================
# Section 4: Main Agent Loop
# =========================================================================
def prolog_solver(
    game,
    render=True,
    delay=0.03,
    keep_window_open=False,
):
    init_static_facts(game.rows, game.cols)
    init_rules()

    agent_board = create_agent_board(game.rows, game.cols)
    start_r, start_c = record_start_cell(game, agent_board)

    print(
        f"Starting at guaranteed safe position: "
        f"{start_r}, {start_c}"
    )

    running = True
    iterations = 0
    guesses = 0
    iteration_limit = (game.rows * game.cols * 2) + 10

    while (
        running
        and not game.game_over
        and iterations < iteration_limit
    ):
        iterations += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if not running:
            break

        update_knowledge_base(
            agent_board,
            game.rows,
            game.cols,
        )

        safe_moves, mine_moves = query_solver()
        move_made = False

        for r, c in safe_moves:
            if not is_hidden(agent_board, r, c):
                continue

            result = reveal_cell(
                game,
                agent_board,
                r,
                c,
            )

            if result is not None:
                move_made = True

            if game.game_over:
                break

        if not game.game_over:
            for r, c in mine_moves:
                if flag_cell(
                    game,
                    agent_board,
                    r,
                    c,
                ):
                    move_made = True

                if game.game_over:
                    break

        if not move_made and not game.game_over:
            guess = get_safest_guess(
                agent_board,
                game.rows,
                game.cols,
            )

            if guess is None:
                print(
                    "Stopped: no hidden cell is available."
                )
                break

            guesses += 1
            print(
                f"Logical deadlock. Guessing cell {guess}."
            )

            result = reveal_cell(
                game,
                agent_board,
                *guess,
            )

            if result is None and not game.game_over:
                print(
                    "Stopped: the guessed cell could not "
                    "be revealed."
                )
                break

        if render:
            game.render()

            if delay > 0:
                time.sleep(delay)

    if (
        iterations >= iteration_limit
        and not game.game_over
    ):
        print("Stopped: iteration limit reached.")

    if render:
        game.render()

    if game.victory:
        print(
            f"Victory in {iterations} iterations "
            f"with {guesses} guesses."
        )
    elif game.game_over:
        print(
            f"Defeat after {iterations} iterations "
            f"and {guesses} guesses."
        )
    else:
        print(
            f"Solver stopped after {iterations} "
            f"iterations and {guesses} guesses."
        )

    while keep_window_open and running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        game.render()
        time.sleep(0.02)

    return agent_board


if __name__ == "__main__":
    SCENARIOS = {
        "simple": (9, 9, 9, 99),
        "standard": (15, 15, 35, 42),
        "challenge": (20, 20, 75, 123),
        "large": (80, 45, 200, -1),
    }

    if __name__ == "__main__":
        scenario_name = (
            sys.argv[1].lower()
            if len(sys.argv) > 1
            else "simple"
        )

        if scenario_name not in SCENARIOS:
            valid_names = ", ".join(SCENARIOS)
            raise ValueError(
                f"Unknown scenario '{scenario_name}'. "
                f"Use: {valid_names}"
            )

        rows, cols, mines, seed = SCENARIOS[scenario_name]

        ms = MineSweeper(
            rows=rows,
            cols=cols,
            mines=mines,
            seed=seed,
            auto_flood_fill=False,
        )

        prolog_solver(
            ms,
            render=True,
            delay=0.0 if scenario_name == "large" else 0.03,
            keep_window_open=False,
        )