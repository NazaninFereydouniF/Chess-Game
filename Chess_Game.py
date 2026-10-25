"""
Chess Game (pygame) - fixed and completed version.

Requirements:
    pip install pygame requests
    pip install rembg        (optional - only used to remove image backgrounds)

Notes:
    * Piece images are downloaded once and cached in the "chess_pieces" folder
      next to this file. If the download fails (no internet), the game still
      runs and draws simple built-in pieces instead.
    * Rule used by this game: the game ends when a king is captured
      (there is no check / checkmate enforcement).
"""

import os
from io import BytesIO

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

START_WHITE_PIECES = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook',
                      'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn']
START_WHITE_LOCATIONS = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0),
                         (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)]
START_BLACK_PIECES = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook',
                      'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn', 'pawn']
START_BLACK_LOCATIONS = [(0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7),
                         (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6)]

white_pieces = list(START_WHITE_PIECES)
white_locations = list(START_WHITE_LOCATIONS)
black_pieces = list(START_BLACK_PIECES)
black_locations = list(START_BLACK_LOCATIONS)

captured_pieces_white = []
captured_pieces_black = []

# 0 - white's turn, no selection; 1 - white's turn, piece selected;
# 2 - black's turn, no selection; 3 - black's turn, piece selected
turn_step = 0
selection = 100
valid_moves = []

piece_list = ['pawn', 'queen', 'king', 'knight', 'rook', 'bishop']

# --------------------------------------------------------------------------
# Loading piece images
# --------------------------------------------------------------------------
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
    """Download one piece image (and remove its background if rembg is installed)."""
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
        image = pygame.image.load(path)
        image = image.convert_alpha()
    except Exception as error:  # no internet, missing packages, bad file...
        print(f'Could not load image for {name} ({error}); using a simple piece instead.')
        image = fallback_piece(color, kind)
    return image


def build_images(color):
    big, small = [], []
    for kind in piece_list:  # same order as piece_list: pawn, queen, king, knight, rook, bishop
        image = load_piece(color, kind)
        size = 65 if kind == 'pawn' else 80
        big.append(pygame.transform.smoothscale(image, (size, size)))
        small.append(pygame.transform.smoothscale(image, (45, 45)))
    return big, small


white_images, small_white_images = build_images('white')
black_images, small_black_images = build_images('black')

counter = 0
winner = ''
game_over = False


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------
def draw_board():
    # light squares
    for i in range(32):
        column = i % 4
        row = i // 4
        if row % 2 == 0:
            pygame.draw.rect(screen, 'light gray', [600 - (column * 200), row * 100, 100, 100])
        else:
            pygame.draw.rect(screen, 'light gray', [700 - (column * 200), row * 100, 100, 100])

    # bottom status bar and side panel
    pygame.draw.rect(screen, 'gray', [0, 800, WIDTH, 100])
    pygame.draw.rect(screen, 'gold', [0, 800, WIDTH, 100], 5)
    pygame.draw.rect(screen, 'gold', [800, 0, 200, HEIGHT], 5)

    status_text = ['White: Select a Piece to Move!', 'White: Select a Destination!',
                   'Black: Select a Piece to Move!', 'Black: Select a Destination!']
    screen.blit(big_font.render(status_text[turn_step], True, 'black'), (20, 820))

    # grid lines
    for i in range(9):
        pygame.draw.line(screen, 'black', (0, 100 * i), (800, 100 * i), 2)
        pygame.draw.line(screen, 'black', (100 * i, 0), (100 * i, 800), 2)

    screen.blit(medium_font.render('FORFEIT', True, 'black'), (810, 830))


def draw_pieces():
    for i in range(len(white_pieces)):
        index = piece_list.index(white_pieces[i])
        if white_pieces[i] == 'pawn':
            screen.blit(white_images[0], (white_locations[i][0] * 100 + 22, white_locations[i][1] * 100 + 30))
        else:
            screen.blit(white_images[index], (white_locations[i][0] * 100 + 10, white_locations[i][1] * 100 + 10))

        if turn_step < 2 and selection == i:
            pygame.draw.rect(screen, 'red', [white_locations[i][0] * 100 + 1, white_locations[i][1] * 100 + 1, 100, 100], 2)

    for i in range(len(black_pieces)):
        index = piece_list.index(black_pieces[i])
        if black_pieces[i] == 'pawn':
            screen.blit(black_images[0], (black_locations[i][0] * 100 + 22, black_locations[i][1] * 100 + 30))
        else:
            screen.blit(black_images[index], (black_locations[i][0] * 100 + 10, black_locations[i][1] * 100 + 10))

        if turn_step >= 2 and selection == i:
            pygame.draw.rect(screen, 'blue', [black_locations[i][0] * 100 + 1, black_locations[i][1] * 100 + 1, 100, 100], 2)


# --------------------------------------------------------------------------
# Move generation
# --------------------------------------------------------------------------
def get_lists(color):
    if color == 'white':
        return white_locations, black_locations  # friends, enemies
    return black_locations, white_locations


def on_board(square):
    return 0 <= square[0] <= 7 and 0 <= square[1] <= 7


def check_options(pieces, locations, turn):
    """Valid moves of every piece of one side (same order as `pieces`)."""
    all_moves_list = []
    for i in range(len(pieces)):
        location = locations[i]
        piece = pieces[i]
        moves_list = []

        if piece == 'pawn':
            moves_list = check_pawn(location, turn)
        elif piece == 'rook':
            moves_list = check_rook(location, turn)
        elif piece == 'knight':
            moves_list = check_knight(location, turn)
        elif piece == 'bishop':
            moves_list = check_bishop(location, turn)
        elif piece == 'queen':
            moves_list = check_queen(location, turn)
        elif piece == 'king':
            moves_list = check_king(location, turn)

        all_moves_list.append(moves_list)
    return all_moves_list


def check_king(position, color):
    moves_list = []
    friends_list, _ = get_lists(color)
    targets = [(1, 0), (1, 1), (1, -1), (-1, 0), (-1, 1), (-1, -1), (0, 1), (0, -1)]
    for dx, dy in targets:
        target = (position[0] + dx, position[1] + dy)
        if target not in friends_list and on_board(target):
            moves_list.append(target)
    return moves_list


def slide(position, color, directions):
    """Shared logic for rook / bishop / queen (sliding pieces)."""
    moves_list = []
    friends_list, enemies_list = get_lists(color)
    for dx, dy in directions:
        chain = 1
        while True:
            target = (position[0] + chain * dx, position[1] + chain * dy)
            if target in friends_list or not on_board(target):
                break
            moves_list.append(target)
            if target in enemies_list:
                break
            chain += 1
    return moves_list


def check_queen(position, color):
    return check_bishop(position, color) + check_rook(position, color)


def check_bishop(position, color):
    return slide(position, color, [(1, -1), (-1, -1), (1, 1), (-1, 1)])


def check_rook(position, color):
    return slide(position, color, [(0, 1), (0, -1), (1, 0), (-1, 0)])


def check_pawn(position, color):
    moves_list = []
    friends_list, enemies_list = get_lists(color)
    occupied = white_locations + black_locations

    direction = 1 if color == 'white' else -1
    start_row = 1 if color == 'white' else 6

    one_step = (position[0], position[1] + direction)
    two_step = (position[0], position[1] + 2 * direction)

    if on_board(one_step) and one_step not in occupied:
        moves_list.append(one_step)
        # two squares only from the start row, and only if both squares are empty
        if position[1] == start_row and two_step not in occupied:
            moves_list.append(two_step)

    for dx in (1, -1):
        target = (position[0] + dx, position[1] + direction)
        if target in enemies_list:
            moves_list.append(target)
    return moves_list


def check_knight(position, color):
    moves_list = []
    friends_list, _ = get_lists(color)
    targets = [(1, 2), (1, -2), (2, 1), (2, -1), (-1, 2), (-1, -2), (-2, 1), (-2, -1)]
    for dx, dy in targets:
        target = (position[0] + dx, position[1] + dy)
        if target not in friends_list and on_board(target):
            moves_list.append(target)
    return moves_list


def check_valid_moves():
    options_list = white_options if turn_step < 2 else black_options
    if 0 <= selection < len(options_list):
        return options_list[selection]
    return []


def draw_valid(moves):
    color = 'red' if turn_step < 2 else 'blue'
    for move in moves:
        pygame.draw.circle(screen, color, (move[0] * 100 + 50, move[1] * 100 + 50), 5)


def draw_captured():
    for i in range(len(captured_pieces_white)):
        index = piece_list.index(captured_pieces_white[i])
        screen.blit(small_black_images[index], (825, 5 + 50 * i))

    for i in range(len(captured_pieces_black)):
        index = piece_list.index(captured_pieces_black[i])
        screen.blit(small_white_images[index], (925, 5 + 50 * i))


def draw_check():
    """Flashing square around a king that is under attack."""
    if counter >= 15:
        return
    if turn_step < 2:
        if 'king' in white_pieces:
            king_index = white_pieces.index('king')
            king_location = white_locations[king_index]
            for moves in black_options:
                if king_location in moves:
                    pygame.draw.rect(screen, 'dark red', [king_location[0] * 100 + 1, king_location[1] * 100 + 1, 100, 100], 5)
                    break
    else:
        if 'king' in black_pieces:
            king_index = black_pieces.index('king')
            king_location = black_locations[king_index]
            for moves in white_options:
                if king_location in moves:
                    pygame.draw.rect(screen, 'dark blue', [king_location[0] * 100 + 1, king_location[1] * 100 + 1, 100, 100], 5)
                    break


def draw_game_over():
    pygame.draw.rect(screen, 'black', [200, 200, 400, 70])
    screen.blit(font.render(f'{winner} won the game!', True, 'white'), (210, 210))
    screen.blit(font.render('Press ENTER to Restart!', True, 'white'), (210, 240))


# --------------------------------------------------------------------------
# Game state helpers
# --------------------------------------------------------------------------
black_options = check_options(black_pieces, black_locations, 'black')
white_options = check_options(white_pieces, white_locations, 'white')


def update_options():
    global black_options, white_options
    black_options = check_options(black_pieces, black_locations, 'black')
    white_options = check_options(white_pieces, white_locations, 'white')


def reset_game():
    global winner, game_over, turn_step, selection, valid_moves
    global captured_pieces_white, captured_pieces_black
    game_over = False
    winner = ''
    white_pieces[:] = START_WHITE_PIECES
    white_locations[:] = START_WHITE_LOCATIONS
    black_pieces[:] = START_BLACK_PIECES
    black_locations[:] = START_BLACK_LOCATIONS
    captured_pieces_white = []
    captured_pieces_black = []
    turn_step = 0
    selection = 100
    valid_moves = []
    update_options()


def handle_click(click_coords):
    """Process a click on a board square (or on the FORFEIT button)."""
    global winner, turn_step, selection, valid_moves

    is_white = turn_step <= 1
    if is_white:
        my_pieces, my_locations = white_pieces, white_locations
        enemy_pieces, enemy_locations = black_pieces, black_locations
        captured, enemy_name, my_name = captured_pieces_white, 'black', 'white'
        selected_step, next_turn, last_row = 1, 2, 7
    else:
        my_pieces, my_locations = black_pieces, black_locations
        enemy_pieces, enemy_locations = white_pieces, white_locations
        captured, enemy_name, my_name = captured_pieces_black, 'white', 'black'
        selected_step, next_turn, last_row = 3, 0, 0

    # FORFEIT button: the player whose turn it is gives up
    if click_coords in ((8, 8), (9, 8)):
        winner = enemy_name
        return

    # select one of your own pieces
    if click_coords in my_locations:
        selection = my_locations.index(click_coords)
        turn_step = selected_step
        return

    # move the selected piece
    if selection != 100 and click_coords in valid_moves:
        my_locations[selection] = click_coords

        # pawn promotion
        if my_pieces[selection] == 'pawn' and click_coords[1] == last_row:
            my_pieces[selection] = 'queen'

        # capture
        if click_coords in enemy_locations:
            index = enemy_locations.index(click_coords)
            captured.append(enemy_pieces[index])
            if enemy_pieces[index] == 'king':
                winner = my_name
            enemy_pieces.pop(index)
            enemy_locations.pop(index)

        update_options()
        turn_step = next_turn
        selection = 100
        valid_moves = []


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
def main():
    global counter, game_over, selection, valid_moves

    run = True
    while run:
        timer.tick(fps)

        counter = counter + 1 if counter < 30 else 0

        screen.fill('dark gray')
        draw_board()
        draw_pieces()
        draw_captured()
        draw_check()

        if selection != 100:
            valid_moves = check_valid_moves()
            draw_valid(valid_moves)

        # event handling (must be INSIDE the loop)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not game_over:
                click_coords = (event.pos[0] // 100, event.pos[1] // 100)
                handle_click(click_coords)

            if event.type == pygame.KEYDOWN and game_over:
                if event.key == pygame.K_RETURN:
                    reset_game()

        if winner != '':
            game_over = True
            draw_game_over()

        pygame.display.flip()  # without this nothing is shown on screen

    pygame.quit()


if __name__ == '__main__':
    main()
