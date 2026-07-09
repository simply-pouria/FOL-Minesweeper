from pyDatalog import pyDatalog

AGENT_UNKNOWN = -1
AGENT_FLAGGED = -2

pyDatalog.create_terms('Cell, neighber, R, C, R2, C2')


def init_static_facts(rows, cols):
    pyDatalog.clear()
    pyDatalog.create_terms('Cell, neighber, R, C, R2, C2')
    for r in range(rows):
        for c in range(cols):
            + Cell(r, c)
    for r in range(rows):
        for c in range(cols):
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        + neighber(r, c, nr, nc)


def create_agent_board(rows, cols):
    agent_board ={}
    for r in range(rows):
        for c in range(cols):
            agent_board[(r, c)] =AGENT_UNKNOWN
    return agent_board


def get_all_neighbers(r, c, rows, cols):
    neighbers =[]
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                neighbers.append((nr, nc))
    return neighbers


def get_hidden_neighbers(agent_board, r, c, rows, cols):
    return [
        (nr, nc) for (nr, nc) in get_all_neighbers(r, c, rows, cols)
        if agent_board[(nr, nc)] == AGENT_UNKNOWN
    ]


def get_flagged_neighbers(agent_board, r, c, rows, cols):
    return [
        (nr, nc) for (nr, nc) in get_all_neighbers(r, c, rows, cols)
        if agent_board[(nr, nc)] == AGENT_FLAGGED
    ]


def get_revealed_neighbers(agent_board, r, c, rows, cols):
    return [
        (nr, nc) for (nr, nc) in get_all_neighbers(r, c, rows, cols)
        if agent_board[(nr, nc)] not in (AGENT_UNKNOWN, AGENT_FLAGGED)
    ]


def is_hidden(agent_board, r, c):
    return agent_board[(r, c)] == AGENT_UNKNOWN


def is_flagged(agent_board, r, c):
    return agent_board[(r, c)] == AGENT_FLAGGED


def is_revealed(agent_board, r, c):
    return agent_board[(r, c)] not in (AGENT_UNKNOWN, AGENT_FLAGGED)


def get_clue(agent_board, r, c):
    if is_revealed(agent_board, r, c):
        return agent_board[(r, c)]
    return None


def record_start_cell(game, agent_board):
    start_r, start_c = game.get_start_pos()
    agent_board[(start_r, start_c)] =0
    return start_r, start_c


def reveal_cell(game, agent_board, r, c):
    if agent_board.get((r, c), AGENT_UNKNOWN) != AGENT_UNKNOWN:
        return agent_board[(r, c)]
    result = game.reveal(r, c)
    if result is None:
        return agent_board[(r, c)]
    agent_board[(r, c)] =result
    return result


def flag_cell(game, agent_board, r, c):
    if agent_board.get((r, c)) == AGENT_FLAGGED:
        return
    game.flag(r, c)
    agent_board[(r, c)] =AGENT_FLAGGED


def unflag_cell(game, agent_board, r, c):
    if agent_board.get((r, c)) != AGENT_FLAGGED:
        return
    game.unflag(r, c)
    agent_board[(r, c)] =AGENT_UNKNOWN


def render_environment(game):
    game.render()
