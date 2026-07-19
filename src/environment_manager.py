from pyDatalog import pyDatalog

# Shadow-board states
AGENT_UNKNOWN = -1
AGENT_FLAGGED = -2
AGENT_EXPLODED_MINE = -3

pyDatalog.create_terms("Cell, Neighbor, R, C, R2, C2")


def init_static_facts(rows, cols):
    """
    Reset pydatalog and add static facts describing:
    """
    pyDatalog.clear()
    pyDatalog.create_terms("Cell, Neighbor, R, C, R2, C2")

    for r in range(rows):
        for c in range(cols):
            +Cell(r, c)

    for r in range(rows):
        for c in range(cols):
            for nr, nc in get_all_neighbors(r, c, rows, cols):
                +Neighbor(r, c, nr, nc)


def create_agent_board(rows, cols):
    return {
        (r, c): AGENT_UNKNOWN
        for r in range(rows)
        for c in range(cols)
    }


def get_all_neighbors(r, c, rows, cols):
    neighbors = []

    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue

            nr = r + dr
            nc = c + dc

            if 0 <= nr < rows and 0 <= nc < cols:
                neighbors.append((nr, nc))

    return neighbors


def get_hidden_neighbors(agent_board, r, c, rows, cols):
    return [
        (nr, nc)
        for nr, nc in get_all_neighbors(r, c, rows, cols)
        if agent_board[(nr, nc)] == AGENT_UNKNOWN
    ]


def get_flagged_neighbors(agent_board, r, c, rows, cols):
    return [
        (nr, nc)
        for nr, nc in get_all_neighbors(r, c, rows, cols)
        if agent_board[(nr, nc)] == AGENT_FLAGGED
    ]


def get_revealed_neighbors(agent_board, r, c, rows, cols):
    return [
        (nr, nc)
        for nr, nc in get_all_neighbors(r, c, rows, cols)
        if is_revealed(agent_board, nr, nc)
    ]


def is_hidden(agent_board, r, c):
    return agent_board.get((r, c)) == AGENT_UNKNOWN


def is_flagged(agent_board, r, c):
    return agent_board.get((r, c)) == AGENT_FLAGGED


def is_revealed(agent_board, r, c):
    """
    a revealed Minesweeper clue must be an integer from 0 to 8.
    """
    value = agent_board.get((r, c))
    return isinstance(value, int) and 0 <= value <= 8


def get_clue(agent_board, r, c):
    if is_revealed(agent_board, r, c):
        return agent_board[(r, c)]

    return None


def record_start_cell(game, agent_board):

    start_r, start_c = game.get_start_pos()
    agent_board[(start_r, start_c)] = 0

    return start_r, start_c


def reveal_cell(game, agent_board, r, c):
    """
    Reveal an unknown cell and update the shadow board.
    """
    if (r, c) not in agent_board:
        return None

    if not is_hidden(agent_board, r, c):
        return agent_board[(r, c)]

    result = game.reveal(r, c)

    if result is None:
        return None

    if result == -1:
        agent_board[(r, c)] = AGENT_EXPLODED_MINE
    else:
        agent_board[(r, c)] = result

    return result


def flag_cell(game, agent_board, r, c):

    if not is_hidden(agent_board, r, c):
        return False

    game.flag(r, c)
    agent_board[(r, c)] = AGENT_FLAGGED

    return True


def unflag_cell(game, agent_board, r, c):
    if not is_flagged(agent_board, r, c):
        return False

    game.unflag(r, c)
    agent_board[(r, c)] = AGENT_UNKNOWN

    return True


def render_environment(game):
    game.render()