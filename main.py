"""
Chess Game – main entry point.

Usage:
    python main.py

Controls:
    • Click a piece to select it (legal destination squares are highlighted).
    • Click a highlighted square to move.
    • Press 'R' to restart at any time.
    • Press 'ESC' to return to the main menu.

Requirements:
    pip install pygame python-chess
"""

import math
import sys
import threading
import chess
import pygame
from ai import get_ai_move

# ---------------------------------------------------------------------------
# Layout / colour constants
# ---------------------------------------------------------------------------
SQUARE_SIZE   = 72          # pixels per board square
BOARD_OFFSET_X = 20         # left margin for the board
BOARD_OFFSET_Y = 60         # top margin for the board
BOARD_PX      = SQUARE_SIZE * 8   # 576

PANEL_X       = BOARD_OFFSET_X + BOARD_PX + 20   # right-panel left edge
PANEL_WIDTH   = 220
PANEL_HEIGHT  = BOARD_PX + 40

WIN_WIDTH     = PANEL_X + PANEL_WIDTH + 10
WIN_HEIGHT    = BOARD_OFFSET_Y + BOARD_PX + 80

# Colours
C_LIGHT       = (240, 217, 181)
C_DARK        = (181, 136, 99)
C_HIGHLIGHT   = (106, 168, 79, 180)   # legal-move green (RGBA)
C_SELECTED    = (255, 215,   0, 200)  # selected square gold (RGBA)
C_LAST_MOVE   = (205, 210,  80, 140)  # last-move tint (RGBA)
C_CHECK       = (220,  50,  50, 160)  # king in check
C_CAPTURE_RING = (200, 60, 60)        # ring drawn on capturable pieces
C_BG          = ( 40,  40,  40)
C_PANEL_BG    = ( 55,  55,  55)
C_TEXT        = (230, 230, 230)
C_TEXT_DARK   = ( 30,  30,  30)
C_BUTTON      = ( 80, 130, 200)
C_BUTTON_HOV  = (100, 155, 230)

PIECE_NAMES = {
    chess.PAWN:   "Pawn",
    chess.KNIGHT: "Knight",
    chess.BISHOP: "Bishop",
    chess.ROOK:   "Rook",
    chess.QUEEN:  "Queen",
    chess.KING:   "King",
}

# ---------------------------------------------------------------------------
# Programmatic piece drawing
# ---------------------------------------------------------------------------

def _poly(surf, fill, outline, lw, pts):
    pygame.draw.polygon(surf, fill, pts)
    pygame.draw.polygon(surf, outline, pts, lw)


def _circ(surf, fill, outline, lw, center, radius):
    pygame.draw.circle(surf, fill, center, radius)
    pygame.draw.circle(surf, outline, center, radius, lw)


def _box(surf, fill, outline, lw, rect):
    pygame.draw.rect(surf, fill, rect)
    pygame.draw.rect(surf, outline, rect, lw)


def draw_piece(surf, piece_type: int, color: chess.Color, cx: int, cy: int):
    """Draw a chess piece centred at pixel (cx, cy)."""
    is_white = color == chess.WHITE
    fill    = (252, 248, 228) if is_white else (38, 28, 18)
    outline = (70,  50,  18) if is_white else (210, 195, 160)
    lw = 2

    sc = SQUARE_SIZE / 72  # scale factor

    def s(v):
        return max(1, int(round(v * sc)))

    if piece_type == chess.PAWN:
        _circ(surf, fill, outline, lw, (cx, cy - s(14)), s(10))
        body = [
            (cx - s(8),  cy - s(4)),
            (cx + s(8),  cy - s(4)),
            (cx + s(11), cy + s(12)),
            (cx - s(11), cy + s(12)),
        ]
        _poly(surf, fill, outline, lw, body)
        _box(surf, fill, outline, lw,
             pygame.Rect(cx - s(14), cy + s(10), s(28), s(9)))

    elif piece_type == chess.ROOK:
        _box(surf, fill, outline, lw,
             pygame.Rect(cx - s(12), cy - s(14), s(24), s(30)))
        for dx in (-s(8), 0, s(8)):
            _box(surf, fill, outline, lw,
                 pygame.Rect(cx + dx - s(4), cy - s(22), s(8), s(10)))
        _box(surf, fill, outline, lw,
             pygame.Rect(cx - s(14), cy + s(14), s(28), s(9)))

    elif piece_type == chess.KNIGHT:
        pts = [
            (cx - s(10), cy + s(22)),
            (cx + s(12), cy + s(22)),
            (cx + s(12), cy + s(4)),
            (cx + s(16), cy - s(4)),
            (cx + s(8),  cy - s(16)),
            (cx + s(4),  cy - s(8)),
            (cx - s(4),  cy - s(20)),
            (cx - s(12), cy - s(12)),
            (cx - s(14), cy + s(2)),
        ]
        _poly(surf, fill, outline, lw, pts)
        pygame.draw.circle(surf, outline,
                           (cx + s(4), cy - s(10)), s(3))

    elif piece_type == chess.BISHOP:
        head = [
            (cx,        cy - s(24)),
            (cx - s(7), cy - s(8)),
            (cx + s(7), cy - s(8)),
        ]
        _poly(surf, fill, outline, lw, head)
        _circ(surf, fill, outline, lw, (cx, cy - s(22)), s(4))
        body = [
            (cx - s(8),  cy - s(8)),
            (cx + s(8),  cy - s(8)),
            (cx + s(11), cy + s(12)),
            (cx - s(11), cy + s(12)),
        ]
        _poly(surf, fill, outline, lw, body)
        _box(surf, fill, outline, lw,
             pygame.Rect(cx - s(14), cy + s(10), s(28), s(9)))

    elif piece_type == chess.QUEEN:
        crown = []
        for i in range(5):
            angle = math.pi / 2 + i * 2 * math.pi / 5
            r = s(12) if i % 2 == 0 else s(6)
            crown.append((cx + int(r * math.cos(angle)),
                          cy - s(14) + int(r * math.sin(angle))))
        crown += [(cx + s(12), cy - s(4)), (cx - s(12), cy - s(4))]
        _poly(surf, fill, outline, lw, crown)
        body = [
            (cx - s(12), cy - s(4)),
            (cx + s(12), cy - s(4)),
            (cx + s(12), cy + s(12)),
            (cx - s(12), cy + s(12)),
        ]
        _poly(surf, fill, outline, lw, body)
        _box(surf, fill, outline, lw,
             pygame.Rect(cx - s(14), cy + s(10), s(28), s(9)))

    elif piece_type == chess.KING:
        # Cross
        _box(surf, fill, outline, lw,
             pygame.Rect(cx - s(3), cy - s(24), s(6), s(16)))
        _box(surf, fill, outline, lw,
             pygame.Rect(cx - s(9), cy - s(22), s(18), s(6)))
        body = [
            (cx - s(10), cy - s(8)),
            (cx + s(10), cy - s(8)),
            (cx + s(12), cy + s(12)),
            (cx - s(12), cy + s(12)),
        ]
        _poly(surf, fill, outline, lw, body)
        _box(surf, fill, outline, lw,
             pygame.Rect(cx - s(14), cy + s(10), s(28), s(9)))

AI_COLOR = chess.BLACK    # human always plays White

# Piece abbreviations used in the captured-pieces display
PIECE_LETTER = {
    chess.PAWN:   "P",
    chess.KNIGHT: "N",
    chess.BISHOP: "B",
    chess.ROOK:   "R",
    chess.QUEEN:  "Q",
    chess.KING:   "K",
}

# ---------------------------------------------------------------------------
# Pygame helpers
# ---------------------------------------------------------------------------

def load_fonts():
    """Return a dict of size → Font."""
    fonts = {}
    for size in (20, 22, 24, 28, 36, 48, 56, 64):
        try:
            f = pygame.font.SysFont("dejavusans", size)
        except Exception:
            f = pygame.font.Font(None, size)
        fonts[size] = f
    return fonts


def square_to_pixel(square: int, flipped=False):
    """Return the top-left pixel (x, y) of a board square."""
    col = chess.square_file(square)   # 0=a … 7=h
    row = chess.square_rank(square)   # 0=rank1 … 7=rank8
    if flipped:
        col = 7 - col
        row = 7 - row
    x = BOARD_OFFSET_X + col * SQUARE_SIZE
    y = BOARD_OFFSET_Y + (7 - row) * SQUARE_SIZE
    return x, y


def pixel_to_square(x, y, flipped=False):
    """Return the chess square index for pixel position (x, y), or None."""
    col = (x - BOARD_OFFSET_X) // SQUARE_SIZE
    row = (y - BOARD_OFFSET_Y) // SQUARE_SIZE
    if not (0 <= col <= 7 and 0 <= row <= 7):
        return None
    if flipped:
        col = 7 - col
        row = 7 - row
    return chess.square(col, 7 - row)


def draw_rounded_rect(surface, colour, rect, radius=8):
    pygame.draw.rect(surface, colour, rect, border_radius=radius)


def draw_button(surface, font, text, rect, hover=False):
    colour = C_BUTTON_HOV if hover else C_BUTTON
    draw_rounded_rect(surface, colour, rect, radius=10)
    label = font.render(text, True, C_TEXT)
    lx = rect[0] + (rect[2] - label.get_width()) // 2
    ly = rect[1] + (rect[3] - label.get_height()) // 2
    surface.blit(label, (lx, ly))


# ---------------------------------------------------------------------------
# Menu screen
# ---------------------------------------------------------------------------

def show_menu(screen, fonts):
    """Show the difficulty-selection menu. Returns 'easy'|'medium'|'hard'."""
    clock = pygame.time.Clock()
    w, h = screen.get_size()

    title_font  = fonts.get(56, fonts[max(fonts)])
    button_font = fonts.get(28, fonts[max(fonts)])
    sub_font    = fonts.get(22, fonts[max(fonts)])

    buttons = {
        "easy":   pygame.Rect(w // 2 - 110, h // 2 - 80, 220, 52),
        "medium": pygame.Rect(w // 2 - 110, h // 2 -  8, 220, 52),
        "hard":   pygame.Rect(w // 2 - 110, h // 2 + 64, 220, 52),
    }
    labels = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
    descriptions = {
        "easy":   "AI plays random moves",
        "medium": "Minimax depth 3 (alpha-beta)",
        "hard":   "Minimax depth 5 + heuristics",
    }

    while True:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for diff, rect in buttons.items():
                    if rect.collidepoint(mx, my):
                        return diff

        screen.fill(C_BG)

        # Title
        title = title_font.render("Chess", True, C_TEXT)
        screen.blit(title, (w // 2 - title.get_width() // 2, h // 4 - 30))

        subtitle = sub_font.render("Select difficulty to start", True, (160, 160, 160))
        screen.blit(subtitle, (w // 2 - subtitle.get_width() // 2, h // 4 + 40))

        # Buttons
        hovered = None
        for diff, rect in buttons.items():
            hover = rect.collidepoint(mx, my)
            if hover:
                hovered = diff
            draw_button(screen, button_font, labels[diff], rect, hover)

        # Description of hovered button
        if hovered:
            desc = sub_font.render(descriptions[hovered], True, (180, 210, 180))
            screen.blit(desc, (w // 2 - desc.get_width() // 2, h // 2 + 140))

        pygame.display.flip()
        clock.tick(60)


# ---------------------------------------------------------------------------
# Promotion dialog
# ---------------------------------------------------------------------------

def show_promotion_dialog(screen, fonts, color):
    """Show pawn-promotion choice. Returns the chosen chess piece type."""
    clock = pygame.time.Clock()
    w, h = screen.get_size()
    choices = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
    names_str  = ["Queen", "Rook", "Bishop", "Knight"]

    box_w, box_h = 380, 130
    box_x = (w - box_w) // 2
    box_y = (h - box_h) // 2

    name_font  = fonts.get(20, fonts[max(fonts)])

    while True:
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, pt in enumerate(choices):
                    cell_x = box_x + i * 95 + 5
                    cell_y = box_y + 20
                    cell_r = pygame.Rect(cell_x, cell_y, 88, 95)
                    if cell_r.collidepoint(mx, my):
                        return pt

        # Overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, C_PANEL_BG, (box_x, box_y, box_w, box_h), border_radius=12)
        pygame.draw.rect(screen, C_TEXT, (box_x, box_y, box_w, box_h), 2, border_radius=12)

        title = name_font.render("Promote pawn to:", True, C_TEXT)
        screen.blit(title, (box_x + (box_w - title.get_width()) // 2, box_y + 2))

        for i, (name, pt) in enumerate(zip(names_str, choices)):
            cell_x = box_x + i * 95 + 5
            cell_y = box_y + 20
            cell_r = pygame.Rect(cell_x, cell_y, 88, 95)
            hover  = cell_r.collidepoint(mx, my)
            bg_col = (80, 80, 120) if hover else (65, 65, 90)
            pygame.draw.rect(screen, bg_col, cell_r, border_radius=8)
            draw_piece(screen, pt, color,
                       cell_x + 44, cell_y + 42)
            name_surf = name_font.render(name, True, C_TEXT)
            screen.blit(name_surf, (cell_x + (88 - name_surf.get_width()) // 2, cell_y + 70))

        pygame.display.flip()
        clock.tick(60)


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

class GameState:
    def __init__(self, difficulty: str):
        self.board      = chess.Board()
        self.difficulty = difficulty
        self.selected   = None          # selected square (int | None)
        self.legal_dsts = set()         # legal destination squares
        self.move_history: list[str] = []   # SAN strings
        self.captured_white: list[chess.PieceType] = []  # captured by Black
        self.captured_black: list[chess.PieceType] = []  # captured by White
        self.last_move: chess.Move | None = None
        self.promotion_pending: chess.Move | None = None
        self.ai_thinking = False
        self.ai_move_ready: chess.Move | None = None
        self.history_scroll = 0         # scroll offset for move history panel

    # ------------------------------------------------------------------
    def status_text(self) -> str:
        b = self.board
        if b.is_checkmate():
            winner = "Black" if b.turn == chess.WHITE else "White"
            return f"Checkmate – {winner} wins!"
        if b.is_stalemate():
            return "Stalemate – Draw!"
        if b.is_insufficient_material():
            return "Draw – insufficient material"
        if b.is_seventyfive_moves():
            return "Draw – 75-move rule"
        if b.is_fivefold_repetition():
            return "Draw – fivefold repetition"
        if b.is_check():
            side = "White" if b.turn == chess.WHITE else "Black"
            return f"{side} is in check!"
        side = "White" if b.turn == chess.WHITE else "Black"
        return f"{side}'s turn  [Difficulty: {self.difficulty.capitalize()}]"

    def is_game_over(self) -> bool:
        return self.board.is_game_over()

    def select(self, square: int):
        """Handle user clicking on *square*."""
        piece = self.board.piece_at(square)
        if self.selected is None:
            # Select a piece belonging to the human
            if piece and piece.color != AI_COLOR:
                self.selected  = square
                self.legal_dsts = {
                    m.to_square for m in self.board.legal_moves
                    if m.from_square == square
                }
        else:
            if square == self.selected:
                # Deselect
                self.selected   = None
                self.legal_dsts = set()
            elif square in self.legal_dsts:
                # Execute the move
                self._make_human_move(square)
            elif piece and piece.color != AI_COLOR:
                # Switch selection to another own piece
                self.selected  = square
                self.legal_dsts = {
                    m.to_square for m in self.board.legal_moves
                    if m.from_square == square
                }
            else:
                self.selected   = None
                self.legal_dsts = set()

    def _make_human_move(self, to_sq: int):
        from_sq = self.selected
        self.selected   = None
        self.legal_dsts = set()

        # Check for pawn promotion
        piece = self.board.piece_at(from_sq)
        needs_promo = (
            piece and piece.piece_type == chess.PAWN
            and chess.square_rank(to_sq) in (0, 7)
        )
        move = chess.Move(from_sq, to_sq,
                          promotion=chess.QUEEN if needs_promo else None)
        if needs_promo:
            self.promotion_pending = move
            return

        self._apply_move(move)

    def apply_promotion(self, piece_type: chess.PieceType):
        if self.promotion_pending:
            move = chess.Move(
                self.promotion_pending.from_square,
                self.promotion_pending.to_square,
                promotion=piece_type,
            )
            self.promotion_pending = None
            self._apply_move(move)

    def _apply_move(self, move: chess.Move):
        if move not in self.board.legal_moves:
            return
        # Track captures
        captured = self.board.piece_at(move.to_square)
        if self.board.is_en_passant(move):
            ep_sq = chess.square(chess.square_file(move.to_square),
                                 chess.square_rank(move.from_square))
            captured = self.board.piece_at(ep_sq)

        san = self.board.san(move)
        if captured:
            if captured.color == chess.BLACK:
                self.captured_black.append(captured.piece_type)
            else:
                self.captured_white.append(captured.piece_type)

        self.board.push(move)
        self.last_move = move
        self.move_history.append(san)

    # ------------------------------------------------------------------
    # AI turn
    # ------------------------------------------------------------------
    def trigger_ai(self, callback):
        """Start AI computation in a background thread."""
        if self.board.turn != AI_COLOR or self.is_game_over():
            return
        self.ai_thinking = True

        def _worker():
            mv = get_ai_move(self.board, self.difficulty)
            callback(mv)

        threading.Thread(target=_worker, daemon=True).start()

    def apply_ai_move(self, move: chess.Move | None):
        self.ai_thinking = False
        if move and move in self.board.legal_moves:
            self._apply_move(move)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_board(screen, state: GameState, fonts):
    label_font = fonts.get(20, fonts[max(fonts)])

    for sq in chess.SQUARES:
        col = chess.square_file(sq)
        row = chess.square_rank(sq)
        x   = BOARD_OFFSET_X + col * SQUARE_SIZE
        y   = BOARD_OFFSET_Y + (7 - row) * SQUARE_SIZE
        rect = pygame.Rect(x, y, SQUARE_SIZE, SQUARE_SIZE)

        is_light = (col + row) % 2 == 1
        colour = C_LIGHT if is_light else C_DARK
        pygame.draw.rect(screen, colour, rect)

    # Last-move tint
    if state.last_move:
        for sq in (state.last_move.from_square, state.last_move.to_square):
            x, y = square_to_pixel(sq)
            surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            surf.fill(C_LAST_MOVE)
            screen.blit(surf, (x, y))

    # Selected square
    if state.selected is not None:
        x, y = square_to_pixel(state.selected)
        surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        surf.fill(C_SELECTED)
        screen.blit(surf, (x, y))

    # Legal destination highlights
    for sq in state.legal_dsts:
        x, y = square_to_pixel(sq)
        surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        surf.fill(C_HIGHLIGHT)
        screen.blit(surf, (x, y))
        # Draw a small dot if the square is empty, else a ring
        if state.board.piece_at(sq) is None:
            cx, cy = x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2
            pygame.draw.circle(screen, C_HIGHLIGHT[:3], (cx, cy), 12)
        else:
            pygame.draw.rect(screen, C_CAPTURE_RING, (x, y, SQUARE_SIZE, SQUARE_SIZE), 3)

    # King in check
    if state.board.is_check():
        king_sq = state.board.king(state.board.turn)
        if king_sq is not None:
            x, y = square_to_pixel(king_sq)
            surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            surf.fill(C_CHECK)
            screen.blit(surf, (x, y))

    # Pieces
    for sq in chess.SQUARES:
        piece = state.board.piece_at(sq)
        if piece is None:
            continue
        x, y = square_to_pixel(sq)
        draw_piece(screen, piece.piece_type, piece.color,
                   x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2)

    # Rank / file labels
    ranks = "12345678"
    files = "abcdefgh"
    for i in range(8):
        # Rank labels (left edge)
        lbl = label_font.render(ranks[7 - i], True, C_TEXT_DARK)
        screen.blit(lbl, (BOARD_OFFSET_X + 2,
                          BOARD_OFFSET_Y + i * SQUARE_SIZE + 2))
        # File labels (bottom edge)
        lbl = label_font.render(files[i], True, C_TEXT_DARK)
        screen.blit(lbl, (BOARD_OFFSET_X + i * SQUARE_SIZE + SQUARE_SIZE - 14,
                          BOARD_OFFSET_Y + BOARD_PX - 18))


def render_captured(screen, state: GameState, fonts):
    """Draw captured-piece counts above and below the board."""
    small_font = fonts.get(20, fonts[max(fonts)])

    def _draw_row(pieces, y, label):
        lbl = small_font.render(label, True, (160, 160, 160))
        screen.blit(lbl, (BOARD_OFFSET_X, y - 20))
        piece_counts: dict = {}
        for pt in pieces:
            piece_counts[pt] = piece_counts.get(pt, 0) + 1
        x = BOARD_OFFSET_X
        for pt in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN]:
            cnt = piece_counts.get(pt, 0)
            if cnt == 0:
                continue
            txt = f"{PIECE_LETTER[pt]}x{cnt}  "
            s = small_font.render(txt, True, C_TEXT)
            screen.blit(s, (x, y))
            x += s.get_width()

    _draw_row(state.captured_white, BOARD_OFFSET_Y - 42, "Captured from White:")
    _draw_row(state.captured_black,
              BOARD_OFFSET_Y + BOARD_PX + 6, "Captured from Black:")


def render_move_history(screen, state: GameState, fonts):
    """Render the scrollable move history panel on the right."""
    panel_rect = pygame.Rect(PANEL_X, BOARD_OFFSET_Y - 20,
                             PANEL_WIDTH, PANEL_HEIGHT)
    draw_rounded_rect(screen, C_PANEL_BG, panel_rect, radius=8)

    title_font = fonts.get(22, fonts[max(fonts)])
    move_font  = fonts.get(20, fonts[max(fonts)])

    title = title_font.render("Move History", True, (200, 200, 200))
    screen.blit(title, (PANEL_X + 8, BOARD_OFFSET_Y - 16))

    # Pair up moves
    history = state.move_history
    pair_count = (len(history) + 1) // 2
    line_h = 22
    visible_lines = (PANEL_HEIGHT - 30) // line_h

    # Auto-scroll to bottom
    max_scroll = max(0, pair_count - visible_lines)
    state.history_scroll = max_scroll

    clip_rect = pygame.Rect(PANEL_X + 2, BOARD_OFFSET_Y + 6,
                            PANEL_WIDTH - 4, PANEL_HEIGHT - 30)
    screen.set_clip(clip_rect)

    for i in range(pair_count):
        if i < state.history_scroll:
            continue
        draw_i = i - state.history_scroll
        y = BOARD_OFFSET_Y + 8 + draw_i * line_h
        if y > BOARD_OFFSET_Y + PANEL_HEIGHT - 30:
            break

        w_move = history[i * 2] if i * 2 < len(history) else ""
        b_move = history[i * 2 + 1] if i * 2 + 1 < len(history) else ""

        num_s = move_font.render(f"{i + 1}.", True, (140, 140, 140))
        w_s   = move_font.render(w_move, True, C_TEXT)
        b_s   = move_font.render(b_move, True, (180, 180, 220))

        screen.blit(num_s, (PANEL_X + 4, y))
        screen.blit(w_s,   (PANEL_X + 38, y))
        screen.blit(b_s,   (PANEL_X + 110, y))

    screen.set_clip(None)


def render_status(screen, state: GameState, fonts):
    """Draw the status bar at the bottom."""
    status_font = fonts.get(22, fonts[max(fonts)])
    txt = state.status_text()
    if state.ai_thinking:
        txt = "AI is thinking…"
    s = status_font.render(txt, True, C_TEXT)
    screen.blit(s, (BOARD_OFFSET_X, BOARD_OFFSET_Y + BOARD_PX + 52))


def render_ai_thinking(screen, fonts):
    """Small indicator while AI calculates."""
    f = fonts.get(20, fonts[max(fonts)])
    s = f.render("AI thinking...", True, (200, 200, 100))
    screen.blit(s, (PANEL_X + 10, BOARD_OFFSET_Y + PANEL_HEIGHT - 25))


def render_game_over(screen, state: GameState, fonts):
    """Semi-transparent overlay with game result and restart prompt."""
    if not state.is_game_over():
        return
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))

    big_font   = fonts.get(48, fonts[max(fonts)])
    small_font = fonts.get(24, fonts[max(fonts)])

    result = state.status_text()
    rs = big_font.render(result, True, (255, 220, 50))
    w, h = screen.get_size()
    screen.blit(rs, (w // 2 - rs.get_width() // 2, h // 2 - 60))

    hint = small_font.render("Press R to restart  |  ESC for menu", True, C_TEXT)
    screen.blit(hint, (w // 2 - hint.get_width() // 2, h // 2 + 20))


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

def run_game(screen, fonts, difficulty: str):
    clock  = pygame.time.Clock()
    state  = GameState(difficulty)

    def ai_callback(move):
        state.ai_move_ready = move

    # If AI moves first (AI is Black – it never starts, human is White)
    # so no initial trigger needed.

    while True:
        clock.tick(60)

        # ---- Handle AI move delivery from background thread ----
        if state.ai_move_ready is not None:
            state.apply_ai_move(state.ai_move_ready)
            state.ai_move_ready = None

        # Trigger AI when it is Black's turn
        if (state.board.turn == AI_COLOR
                and not state.ai_thinking
                and not state.is_game_over()
                and state.promotion_pending is None
                and state.ai_move_ready is None):
            state.trigger_ai(ai_callback)

        # ---- Events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "menu"
                if event.key == pygame.K_r:
                    return "restart"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if (state.board.turn != AI_COLOR
                        and not state.ai_thinking
                        and not state.is_game_over()
                        and state.promotion_pending is None):
                    sq = pixel_to_square(*event.pos)
                    if sq is not None:
                        state.select(sq)

        # ---- Promotion dialog ----
        if state.promotion_pending is not None:
            screen.fill(C_BG)
            render_board(screen, state, fonts)
            render_captured(screen, state, fonts)
            render_move_history(screen, state, fonts)
            render_status(screen, state, fonts)
            pygame.display.flip()
            pt = show_promotion_dialog(screen, fonts, chess.WHITE)
            state.apply_promotion(pt)
            continue

        # ---- Draw ----
        screen.fill(C_BG)
        render_board(screen, state, fonts)
        render_captured(screen, state, fonts)
        render_move_history(screen, state, fonts)
        if state.ai_thinking:
            render_ai_thinking(screen, fonts)
        render_status(screen, state, fonts)
        render_game_over(screen, state, fonts)
        pygame.display.flip()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
    pygame.display.set_caption("Chess – AI Opponent")
    fonts  = load_fonts()

    while True:
        difficulty = show_menu(screen, fonts)
        result     = run_game(screen, fonts, difficulty)
        if result == "menu":
            continue   # go back to menu
        # 'restart' → show menu again with same difficulty (let user choose)


if __name__ == "__main__":
    main()
