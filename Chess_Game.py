"""
Chess Game v2 (pygame)

New in this version
-------------------
* Full legal-move rules: a king can never move into (or stay in) an attacked square,
  pinned pieces cannot expose their king.
* Check, checkmate and stalemate detection.
* Castling (king side and queen side) and en passant.
* Pawn promotion with a choice of piece (queen / rook / bishop / knight).
* Draw rules: stalemate, threefold repetition, 50-move rule, insufficient material.
* Play against the computer (Easy / Hard). The human plays White.
* Start menu, last-move highlight, restart (ENTER) and back-to-menu (M) after a game.

Requirements:
    pip install pygame requests
    pip install rembg        (optional - only used to remove image backgrounds)

Piece images are downloaded once and cached in the "chess_pieces" folder next to
this file. Without internet the game still works with simple built-in pieces.

Controls:
    Left click ......... select a piece / choose a destination
    FORFEIT (bottom right) .. give up the game
    ENTER .............. new game (after game over)
    M .................. back to the menu (after game over)
    ESC ................ cancel promotion choice
"""

import itertools
import os
import random
import threading

import pygame

pygame.init()

WIDTH = 1000
HEIGHT = 900

screen = pygame.display.set_mode([WIDTH, HEIGHT])
pygame.display.set_caption('Chess Game')

font = pygame.font.Font('freesansbold.ttf', 20)
medium_font = pygame.font.Font('freesansbold.ttf', 40)
big_font = pygame.font.Font('freesansbold.ttf', 50)

timer = pygame.time.Clock()
fps = 60

# ==========================================================================
#  CHESS ENGINE  (pure logic - no pygame here)
#  Coordinates are (x, y): x = file 0..7, y = rank 0..7.
#  White starts at the top (y = 0, 1) and moves towards y = 7.
# ==========================================================================
START_WHITE_PIECES = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook',
                      'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn']
START_WHITE_LOCATIONS = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0),
                         (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)]
START_BLACK_PIECES = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook',
                      'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn']
START_BLACK_LOCATIONS = [(0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7),
                         (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6)]

KNIGHT_D = [(1, 2), (1, -2), (2, 1), (2, -1), (-1, 2), (-1, -2), (-2, 1), (-2, -1)]
KING_D = [(1, 0), (1, 1), (1, -1), (-1, 0), (-1, 1), (-1, -1), (0, 1), (0, -1)]
ROOK_D = [(0, 1), (0, -1), (1, 0), (-1, 0)]
BISHOP_D = [(1, -1), (-1, -1), (1, 1), (-1, 1)]
PROMOTION_PIECES = ['queen', 'rook', 'bishop', 'knight']

MATE = 100000
INF = 10 ** 9


def opp(color):
    return 'black' if color == 'white' else 'white'


class Position:
    """board: {(x, y): (color, kind)}  |  turn: 'white'/'black'
    castling: frozenset of 'wK','wQ','bK','bQ'  |  ep: en-passant target square or None"""
    __slots__ = ('board', 'turn', 'castling', 'ep', 'halfmove')

    def __init__(self, board, turn, castling, ep, halfmove):
        self.board = board
        self.turn = turn
        self.castling = castling
        self.ep = ep
        self.halfmove = halfmove


def start_position():
    board = {}
    for piece, loc in zip(START_WHITE_PIECES, START_WHITE_LOCATIONS):
        board[loc] = ('white', piece)
    for piece, loc in zip(START_BLACK_PIECES, START_BLACK_LOCATIONS):
        board[loc] = ('black', piece)
    return Position(board, 'white', frozenset(['wK', 'wQ', 'bK', 'bQ']), None, 0)


def position_key(pos):
    return (tuple(sorted(pos.board.items())), pos.turn, pos.castling, pos.ep)


def find_king(board, color):
    for sq, piece in board.items():
        if piece[1] == 'king' and piece[0] == color:
            return sq
    return None


def attacked(board, sq, by):
    """Is square `sq` attacked by any piece of colour `by`?"""
    x, y = sq
    d = 1 if by == 'white' else -1
    for dx in (-1, 1):
        p = board.get((x + dx, y - d))
        if p is not None and p[0] == by and p[1] == 'pawn':
            return True
    for dx, dy in KNIGHT_D:
        p = board.get((x + dx, y + dy))
        if p is not None and p[0] == by and p[1] == 'knight':
            return True
    for dx, dy in KING_D:
        p = board.get((x + dx, y + dy))
        if p is not None and p[0] == by and p[1] == 'king':
            return True
    for directions, kinds in ((ROOK_D, ('rook', 'queen')), (BISHOP_D, ('bishop', 'queen'))):
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            while 0 <= nx <= 7 and 0 <= ny <= 7:
                p = board.get((nx, ny))
                if p is not None:
                    if p[0] == by and p[1] in kinds:
                        return True
                    break
                nx += dx
                ny += dy
    return False


def in_check(pos, color=None):
    color = color or pos.turn
    king = find_king(pos.board, color)
    return king is not None and attacked(pos.board, king, opp(color))


def gen_moves(pos, captures_only=False):
    """Pseudo-legal moves (may leave own king in check). Move = (from, to, promotion)."""
    board = pos.board
    color = pos.turn
    enemy = opp(color)
    moves = []

    for frm, (c, kind) in board.items():
        if c != color:
            continue
        x, y = frm

        if kind == 'pawn':
            d = 1 if color == 'white' else -1
            start = 1 if color == 'white' else 6
            last = 7 if color == 'white' else 0
            ny = y + d
            if not 0 <= ny <= 7:
                continue
            one = (x, ny)
            if one not in board:
                if ny == last:
                    for promo in PROMOTION_PIECES:
                        moves.append((frm, one, promo))
                elif not captures_only:
                    moves.append((frm, one, None))
                    two = (x, y + 2 * d)
                    if y == start and two not in board:
                        moves.append((frm, two, None))
            for dx in (-1, 1):
                nx = x + dx
                if 0 <= nx <= 7:
                    t = (nx, ny)
                    target = board.get(t)
                    if (target is not None and target[0] != color) or (target is None and t == pos.ep):
                        if ny == last:
                            for promo in PROMOTION_PIECES:
                                moves.append((frm, t, promo))
                        else:
                            moves.append((frm, t, None))

        elif kind == 'knight' or kind == 'king':
            offsets = KNIGHT_D if kind == 'knight' else KING_D
            for dx, dy in offsets:
                t = (x + dx, y + dy)
                if 0 <= t[0] <= 7 and 0 <= t[1] <= 7:
                    target = board.get(t)
                    if target is None:
                        if not captures_only:
                            moves.append((frm, t, None))
                    elif target[0] != color:
                        moves.append((frm, t, None))

        else:  # rook, bishop, queen
            if kind == 'rook':
                directions = ROOK_D
            elif kind == 'bishop':
                directions = BISHOP_D
            else:
                directions = ROOK_D + BISHOP_D
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                while 0 <= nx <= 7 and 0 <= ny <= 7:
                    t = (nx, ny)
                    target = board.get(t)
                    if target is None:
                        if not captures_only:
                            moves.append((frm, t, None))
                    else:
                        if target[0] != color:
                            moves.append((frm, t, None))
                        break
                    nx += dx
                    ny += dy

    # castling
    if not captures_only:
        row = 0 if color == 'white' else 7
        p = 'w' if color == 'white' else 'b'
        if board.get((4, row)) == (color, 'king') and (p + 'K' in pos.castling or p + 'Q' in pos.castling):
            if not attacked(board, (4, row), enemy):
                if (p + 'K' in pos.castling and board.get((7, row)) == (color, 'rook')
                        and (5, row) not in board and (6, row) not in board
                        and not attacked(board, (5, row), enemy) and not attacked(board, (6, row), enemy)):
                    moves.append(((4, row), (6, row), None))
                if (p + 'Q' in pos.castling and board.get((0, row)) == (color, 'rook')
                        and (1, row) not in board and (2, row) not in board and (3, row) not in board
                        and not attacked(board, (3, row), enemy) and not attacked(board, (2, row), enemy)):
                    moves.append(((4, row), (2, row), None))
    return moves


def apply_move(pos, move):
    """Return (new_position, captured_kind_or_None). Handles castling, en passant, promotion."""
    frm, to, promo = move
    board = dict(pos.board)
    color, kind = board.pop(frm)
    captured = board.pop(to, None)

    if kind == 'pawn' and to[0] != frm[0] and captured is None:  # en passant
        captured = board.pop((to[0], frm[1]))

    if kind == 'king' and abs(to[0] - frm[0]) == 2:  # castling: move the rook too
        row = frm[1]
        if to[0] == 6:
            board[(5, row)] = board.pop((7, row))
        else:
            board[(3, row)] = board.pop((0, row))

    board[to] = (color, promo if promo else kind)

    ep = None
    if kind == 'pawn' and abs(to[1] - frm[1]) == 2:
        ep = (frm[0], (frm[1] + to[1]) // 2)

    rights = set(pos.castling)
    if kind == 'king':
        p = 'w' if color == 'white' else 'b'
        rights.discard(p + 'K')
        rights.discard(p + 'Q')
    for sq in (frm, to):
        if sq == (0, 0):
            rights.discard('wQ')
        elif sq == (7, 0):
            rights.discard('wK')
        elif sq == (0, 7):
            rights.discard('bQ')
        elif sq == (7, 7):
            rights.discard('bK')

    halfmove = 0 if (kind == 'pawn' or captured is not None) else pos.halfmove + 1
    new_pos = Position(board, opp(pos.turn), frozenset(rights), ep, halfmove)
    return new_pos, (captured[1] if captured else None)


def legal_moves(pos):
    color = pos.turn
    enemy = opp(color)
    result = []
    for move in gen_moves(pos):
        child, _ = apply_move(pos, move)
        king = find_king(child.board, color)
        if king is not None and not attacked(child.board, king, enemy):
            result.append(move)
    return result


def insufficient_material(pos):
    others = [p[1] for p in pos.board.values() if p[1] != 'king']
    if not others:
        return True
    return len(others) == 1 and others[0] in ('bishop', 'knight')


# ==========================================================================
#  COMPUTER PLAYER
# ==========================================================================
PIECE_VALUE = {'pawn': 100, 'knight': 320, 'bishop': 330, 'rook': 500, 'queen': 900, 'king': 0}


def evaluate(pos):
    """Score from the point of view of the side to move (positive = good)."""
    score = 0
    for (x, y), (color, kind) in pos.board.items():
        value = PIECE_VALUE[kind]
        if kind in ('pawn', 'knight', 'bishop'):  # small bonus for central squares
            value += int(10 - 3 * (abs(x - 3.5) + abs(y - 3.5)))
        if kind == 'pawn':
            progress = y if color == 'white' else 7 - y
            value += 6 * progress
        score += value if color == 'white' else -value
    return score if pos.turn == 'white' else -score


def move_order_key(pos, move):
    frm, to, promo = move
    victim = pos.board.get(to)
    score = 0
    if victim is not None:
        score += 10 * PIECE_VALUE[victim[1]] - PIECE_VALUE[pos.board[frm][1]]
    elif pos.board[frm][1] == 'pawn' and to[0] != frm[0]:
        score += 10 * 100 - 100
    if promo:
        score += PIECE_VALUE[promo]
    return -score


def quiesce(pos, alpha, beta, qdepth):
    stand = evaluate(pos)
    if stand >= beta:
        return stand
    if stand > alpha:
        alpha = stand
    if qdepth >= 4:
        return stand
    color = pos.turn
    enemy = opp(color)
    for move in sorted(gen_moves(pos, True), key=lambda m: move_order_key(pos, m)):
        child, _ = apply_move(pos, move)
        king = find_king(child.board, color)
        if king is None or attacked(child.board, king, enemy):
            continue
        score = -quiesce(child, -beta, -alpha, qdepth + 1)
        if score >= beta:
            return score
        if score > alpha:
            alpha = score
    return alpha


def negamax(pos, depth, alpha, beta, ply, use_quiesce):
    moves = legal_moves(pos)
    if not moves:
        return -MATE + ply if in_check(pos) else 0
    if pos.halfmove >= 100 or insufficient_material(pos):
        return 0
    if depth == 0:
        return quiesce(pos, alpha, beta, 0) if use_quiesce else evaluate(pos)
    best = -INF
    for move in sorted(moves, key=lambda m: move_order_key(pos, m)):
        child, _ = apply_move(pos, move)
        score = -negamax(child, depth - 1, -beta, -alpha, ply + 1, use_quiesce)
        if score > best:
            best = score
        if score > alpha:
            alpha = score
        if alpha >= beta:
            break
    return best


# difficulty: (search depth, random margin in centipawns, quiescence search)
LEVELS = {'easy': (1, 150, False), 'hard': (3, 0, True)}


def choose_move(pos, level):
    moves = legal_moves(pos)
    if not moves:
        return None
    depth, margin, use_quiesce = LEVELS[level]
    ordered = sorted(moves, key=lambda m: move_order_key(pos, m))

    if margin > 0:  # easy: pick randomly among the reasonably good moves
        scored = []
        for move in ordered:
            child, _ = apply_move(pos, move)
            scored.append((-negamax(child, depth - 1, -INF, INF, 1, use_quiesce), move))
        best = max(s for s, _ in scored)
        return random.choice([m for s, m in scored if s >= best - margin])

    best_score, best_move = -INF, ordered[0]
    alpha = -INF
    for move in ordered:
        child, _ = apply_move(pos, move)
        score = -negamax(child, depth - 1, -INF, -alpha, 1, use_quiesce)
        score += random.random()  # tiny noise so equal moves vary between games
        if score > best_score:
            best_score, best_move = score, move
        alpha = max(alpha, int(best_score))
    return best_move


# ==========================================================================
#  PIECE IMAGES
# ==========================================================================
IMAGE_URLS = {
    'black_queen': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025946/black_queen.png',
    'black_king': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025948/black_king.png',
    'black_rook': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025345/black_rook.png',
    'black_bishop': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025951/black_bishop.png',
    'black_knight': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025947/black_knight.png',
    'black_pawn': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025945/black_pawn.png',
    'white_queen': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025952/white_queen.png',
    'white_king': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025943/white_king.png',
    'white_rook': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025949/white_rook.png',
    'white_bishop': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025944/white_bishop.png',
    'white_knight': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025325/white_knight.png',
    'white_pawn': 'https://media.geeksforgeeks.org/wp-content/uploads/20240302025953/white_pawn.png',
}

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chess_pieces')
LETTERS = {'pawn': 'P', 'queen': 'Q', 'king': 'K', 'knight': 'N', 'rook': 'R', 'bishop': 'B'}
piece_list = ['pawn', 'queen', 'king', 'knight', 'rook', 'bishop']


def fallback_piece(color, kind):
    """Simple built-in piece used when the image cannot be downloaded."""
    surf = pygame.Surface((80, 80), pygame.SRCALPHA)
    fill = (245, 245, 245) if color == 'white' else (35, 35, 35)
    edge = (20, 20, 20) if color == 'white' else (230, 230, 230)
    text_color = (20, 20, 20) if color == 'white' else (240, 240, 240)
    pygame.draw.circle(surf, fill, (40, 40), 34)
    pygame.draw.circle(surf, edge, (40, 40), 34, 3)
    letter = medium_font.render(LETTERS[kind], True, text_color)
    surf.blit(letter, letter.get_rect(center=(40, 40)))
    return surf


def download_piece(name):
    import requests
    response = requests.get(IMAGE_URLS[name], timeout=15)
    response.raise_for_status()
    data = response.content
    try:
        import rembg
        data = rembg.remove(data)
    except ImportError:
        pass
    return data


def load_piece(color, kind):
    name = f'{color}_{kind}'
    path = os.path.join(CACHE_DIR, name + '.png')
    try:
        if not os.path.exists(path):
            data = download_piece(name)
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(data)
        image = pygame.image.load(path).convert_alpha()
    except Exception as error:  # no internet, missing packages, bad file ...
        print(f'Could not load image for {name} ({error}); using a simple piece instead.')
        image = fallback_piece(color, kind)
    return image


def build_images(color):
    big, small = [], []
    for kind in piece_list:
        image = load_piece(color, kind)
        size = 65 if kind == 'pawn' else 80
        big.append(pygame.transform.smoothscale(image, (size, size)))
        small.append(pygame.transform.smoothscale(image, (45, 45)))
    return big, small


white_images, small_white_images = build_images('white')
black_images, small_black_images = build_images('black')


# ==========================================================================
#  GAME STATE
# ==========================================================================
_game_ids = itertools.count(1)


class Game:
    def __init__(self, mode):
        self.mode = mode  # '2p', 'easy' or 'hard'
        self.id = next(_game_ids)
        self.pos = start_position()
        self.history = [position_key(self.pos)]
        self.captured_white = []   # black pieces captured by White
        self.captured_black = []   # white pieces captured by Black
        self.selected = None
        self.promo_choices = None  # list of promotion moves waiting for the player's choice
        self.last_move = None
        self.over = False
        self.result = ''
        self.legal = legal_moves(self.pos)
        self.check = False

    # ----- helpers -----
    @property
    def turn_step(self):
        return (0 if self.pos.turn == 'white' else 2) + (1 if self.selected else 0)

    def is_computer_turn(self):
        return self.mode != '2p' and not self.over and self.pos.turn == 'black'

    def human_turn(self):
        return not self.over and not self.is_computer_turn()

    def destinations(self):
        if self.selected is None:
            return []
        return [m[1] for m in self.legal if m[0] == self.selected]

    # ----- actions -----
    def forfeit(self):
        if self.over:
            return
        loser = 'white' if self.mode != '2p' else self.pos.turn
        self.finish(f'{opp(loser).capitalize()} won the game!', 'Forfeit')

    def finish(self, text, reason=''):
        self.over = True
        self.result = text
        self.reason = reason
        self.selected = None
        self.promo_choices = None

    def click(self, sq):
        if not self.human_turn():
            return

        if self.promo_choices:  # waiting for the promotion piece
            if sq[1] == 3 and 2 <= sq[0] <= 5:
                promo = PROMOTION_PIECES[sq[0] - 2]
                for move in self.promo_choices:
                    if move[2] == promo:
                        self.promo_choices = None
                        self.play(move)
                        return
            return

        piece = self.pos.board.get(sq)
        if piece is not None and piece[0] == self.pos.turn:
            self.selected = None if self.selected == sq else sq
        elif self.selected is not None:
            candidates = [m for m in self.legal if m[0] == self.selected and m[1] == sq]
            if not candidates:
                self.selected = None
            elif len(candidates) > 1:  # promotion: ask which piece
                self.promo_choices = candidates
            else:
                self.play(candidates[0])

    def play(self, move):
        mover = self.pos.turn
        self.pos, captured = apply_move(self.pos, move)
        if captured:
            (self.captured_white if mover == 'white' else self.captured_black).append(captured)
        self.last_move = (move[0], move[1])
        self.selected = None
        self.promo_choices = None
        self.history.append(position_key(self.pos))
        self.legal = legal_moves(self.pos)
        self.check = in_check(self.pos)

        if not self.legal:
            if self.check:
                self.finish(f'Checkmate! {mover.capitalize()} won!', 'Checkmate')
            else:
                self.finish('Stalemate - Draw!', 'Stalemate')
        elif self.history.count(self.history[-1]) >= 3:
            self.finish('Draw by repetition!', 'Repetition')
        elif self.pos.halfmove >= 100:
            self.finish('Draw by 50-move rule!', '50-move')
        elif insufficient_material(self.pos):
            self.finish('Draw - not enough material!', 'Material')


class AIRunner:
    """Runs the computer's search in a background thread so the window never freezes."""

    def __init__(self):
        self.running = False
        self.requested = None   # key of the position being searched
        self.result = None      # (key, move)

    def update(self, game):
        if game is None or not game.is_computer_turn():
            return
        key = (game.id, len(game.history))
        if self.result is not None and self.result[0] == key:
            move = self.result[1]
            self.result = None
            self.requested = None
            game.play(move)
        elif not self.running and self.requested != key:
            self.requested = key
            self.running = True
            threading.Thread(target=self._run, args=(game.pos, game.mode, key), daemon=True).start()

    def _run(self, pos, level, key):
        try:
            move = choose_move(pos, level)
            self.result = (key, move)
        finally:
            self.running = False

    def thinking(self, game):
        return game is not None and game.is_computer_turn() and not game.over


# ==========================================================================
#  DRAWING
# ==========================================================================
counter = 0


def draw_board(game):
    for i in range(32):
        column = i % 4
        row = i // 4
        if row % 2 == 0:
            pygame.draw.rect(screen, 'light gray', [600 - (column * 200), row * 100, 100, 100])
        else:
            pygame.draw.rect(screen, 'light gray', [700 - (column * 200), row * 100, 100, 100])

    if game.last_move:
        for sq in game.last_move:
            pygame.draw.rect(screen, 'yellow', [sq[0] * 100 + 3, sq[1] * 100 + 3, 95, 95], 4)

    pygame.draw.rect(screen, 'gray', [0, 800, WIDTH, 100])
    pygame.draw.rect(screen, 'gold', [0, 800, WIDTH, 100], 5)
    pygame.draw.rect(screen, 'gold', [800, 0, 200, HEIGHT], 5)

    status_text = ['White: Select a Piece to Move!', 'White: Select a Destination!',
                   'Black: Select a Piece to Move!', 'Black: Select a Destination!']
    if game.over:
        text = 'Game Over'
    elif game.is_computer_turn():
        text = 'Computer is thinking...'
    else:
        text = status_text[game.turn_step]
    screen.blit(big_font.render(text, True, 'black'), (20, 820))

    for i in range(9):
        pygame.draw.line(screen, 'black', (0, 100 * i), (800, 100 * i), 2)
        pygame.draw.line(screen, 'black', (100 * i, 0), (100 * i, 800), 2)

    screen.blit(medium_font.render('FORFEIT', True, 'black'), (810, 830))


def draw_pieces(game):
    for (x, y), (color, kind) in game.pos.board.items():
        index = piece_list.index(kind)
        images = white_images if color == 'white' else black_images
        if kind == 'pawn':
            screen.blit(images[0], (x * 100 + 22, y * 100 + 30))
        else:
            screen.blit(images[index], (x * 100 + 10, y * 100 + 10))

    if game.selected is not None:
        sel_color = 'red' if game.pos.turn == 'white' else 'blue'
        x, y = game.selected
        pygame.draw.rect(screen, sel_color, [x * 100 + 1, y * 100 + 1, 100, 100], 2)


def draw_valid(game):
    color = 'red' if game.pos.turn == 'white' else 'blue'
    for sq in set(game.destinations()):
        center = (sq[0] * 100 + 50, sq[1] * 100 + 50)
        if sq in game.pos.board:
            pygame.draw.circle(screen, color, center, 45, 4)  # capture: ring
        else:
            pygame.draw.circle(screen, color, center, 8)      # normal move: dot


def draw_captured(game):
    for i, kind in enumerate(game.captured_white):
        screen.blit(small_black_images[piece_list.index(kind)], (825, 5 + 50 * i))
    for i, kind in enumerate(game.captured_black):
        screen.blit(small_white_images[piece_list.index(kind)], (925, 5 + 50 * i))


def draw_check(game):
    """Flashing square around the king of the side to move when it is in check."""
    if game.check and counter < 15:
        king = find_king(game.pos.board, game.pos.turn)
        if king:
            color = 'dark red' if game.pos.turn == 'white' else 'dark blue'
            pygame.draw.rect(screen, color, [king[0] * 100 + 1, king[1] * 100 + 1, 100, 100], 5)


def draw_promotion(game):
    pygame.draw.rect(screen, 'black', [190, 250, 420, 165])
    screen.blit(font.render('Promote pawn to:', True, 'white'), (200, 262))
    images = white_images if game.pos.turn == 'white' else black_images
    for i, kind in enumerate(PROMOTION_PIECES):
        pygame.draw.rect(screen, 'light gray', [200 + 100 * i, 300, 100, 100])
        pygame.draw.rect(screen, 'black', [200 + 100 * i, 300, 100, 100], 2)
        screen.blit(images[piece_list.index(kind)], (210 + 100 * i, 310))


def draw_game_over(game):
    pygame.draw.rect(screen, 'black', [200, 200, 400, 105])
    screen.blit(font.render(game.result, True, 'white'), (210, 210))
    screen.blit(font.render('Press ENTER to Restart!', True, 'white'), (210, 245))
    screen.blit(font.render('Press M for the Menu', True, 'white'), (210, 270))


MENU_BUTTONS = [('2 Players', '2p'), ('Computer - Easy', 'easy'), ('Computer - Hard', 'hard')]


def menu_rects():
    return [pygame.Rect(300, 320 + 120 * i, 400, 80) for i in range(len(MENU_BUTTONS))]


def draw_menu():
    screen.fill('dark gray')
    title = big_font.render('CHESS', True, 'black')
    screen.blit(title, (WIDTH // 2 - 80, 150))
    screen.blit(font.render('Choose a game mode (vs computer you play White)', True, 'black'), (270, 240))
    for rect, (label, _) in zip(menu_rects(), MENU_BUTTONS):
        pygame.draw.rect(screen, 'light gray', rect)
        pygame.draw.rect(screen, 'gold', rect, 5)
        screen.blit(medium_font.render(label, True, 'black'), (rect.x + 40, rect.y + 20))


# ==========================================================================
#  MAIN LOOP
# ==========================================================================
def main():
    global counter

    game = None  # None -> menu is shown
    ai = AIRunner()
    run = True

    while run:
        timer.tick(fps)
        counter = counter + 1 if counter < 30 else 0

        if game is None:
            draw_menu()
        else:
            screen.fill('dark gray')
            draw_board(game)
            draw_pieces(game)
            draw_captured(game)
            draw_check(game)
            draw_valid(game)
            if game.promo_choices:
                draw_promotion(game)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game is None:
                    for rect, (_, mode) in zip(menu_rects(), MENU_BUTTONS):
                        if rect.collidepoint(event.pos):
                            game = Game(mode)
                elif not game.over:
                    x_coord, y_coord = event.pos[0] // 100, event.pos[1] // 100
                    if y_coord == 8 and x_coord in (8, 9):
                        game.forfeit()
                    elif x_coord <= 7 and y_coord <= 7:
                        game.click((x_coord, y_coord))

            elif event.type == pygame.KEYDOWN and game is not None:
                if game.over and event.key == pygame.K_RETURN:
                    game = Game(game.mode)
                elif game.over and event.key == pygame.K_m:
                    game = None
                elif event.key == pygame.K_ESCAPE and game.promo_choices:
                    game.promo_choices = None

        ai.update(game)

        if game is not None and game.over:
            draw_game_over(game)

        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
