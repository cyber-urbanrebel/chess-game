from __future__ import annotations

import pygame
import chess

from ai import ChessAI
from board import ChessBoard
from pieces import piece_unicode, symbol_unicode


class ChessUI:
    def __init__(self, board_state: ChessBoard, ai_engine: ChessAI) -> None:
        pygame.init()
        pygame.display.set_caption("Python Chess: Player vs AI")

        self.board_state = board_state
        self.ai_engine = ai_engine

        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

        self.board_x = 20
        self.board_y = 20
        self.square_size = 60
        self.board_size = self.square_size * 8

        self.panel_rect = pygame.Rect(520, 20, 260, 560)
        self.status_rect = pygame.Rect(20, 520, 760, 60)
        self.restart_rect = pygame.Rect(540, 530, 110, 34)

        self.diff_buttons = {
            "easy": pygame.Rect(660, 530, 36, 34),
            "medium": pygame.Rect(702, 530, 36, 34),
            "hard": pygame.Rect(744, 530, 36, 34),
        }

        self.colors = {
            "bg": (34, 30, 24),
            "panel": (242, 233, 214),
            "status": (237, 227, 206),
            "light": (240, 217, 181),
            "dark": (181, 136, 99),
            "sel": (255, 220, 90),
            "move": (66, 150, 66),
            "text": (32, 24, 18),
            "muted": (96, 78, 63),
            "white": (250, 250, 250),
            "black": (20, 20, 20),
            "overlay": (15, 15, 15, 170),
        }

        self.font_piece = pygame.font.SysFont("Segoe UI Symbol", 44)
        self.font_small = pygame.font.SysFont("Consolas", 16)
        self.font_status = pygame.font.SysFont("Segoe UI", 20, bold=True)
        self.font_title = pygame.font.SysFont("Segoe UI", 18, bold=True)

        self.human_color = chess.WHITE
        self.ai_color = chess.BLACK

        self.selected_square: chess.Square | None = None
        self.legal_moves: list[chess.Move] = []

        self.promotion_choices: list[chess.Move] = []
        self.promotion_rects: list[tuple[chess.Move, pygame.Rect]] = []

        self.running = True

    def run(self) -> None:
        clock = pygame.time.Clock()
        while self.running:
            for event in pygame.event.get():
                self._handle_event(event)

            if self._should_ai_move():
                self._perform_ai_move()

            self._draw_frame()
            pygame.display.flip()
            clock.tick(60)

        pygame.quit()

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self._undo_last_move()
            if event.key == pygame.K_r:
                self._restart_game()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse = event.pos
            self._handle_mouse_click(mouse)

    def _handle_mouse_click(self, mouse: tuple[int, int]) -> None:
        if self.restart_rect.collidepoint(mouse):
            self._restart_game()
            return

        for difficulty, rect in self.diff_buttons.items():
            if rect.collidepoint(mouse):
                self.ai_engine.set_difficulty(difficulty)
                return

        if self.promotion_choices:
            for move, rect in self.promotion_rects:
                if rect.collidepoint(mouse):
                    self._execute_move(move)
                    self.promotion_choices = []
                    self.promotion_rects = []
                    return
            return

        board_square = self._mouse_to_square(mouse)
        if board_square is None:
            self.selected_square = None
            self.legal_moves = []
            return

        board = self.board_state.board
        if board.turn != self.human_color or self.board_state.is_game_over():
            return

        if self.selected_square is not None:
            candidates = [m for m in self.legal_moves if m.to_square == board_square]
            if candidates:
                if len(candidates) == 1:
                    self._execute_move(candidates[0])
                else:
                    # Promotion choices (Q, R, B, N)
                    self.promotion_choices = candidates
                    self._build_promotion_menu()
                return

        piece = board.piece_at(board_square)
        if piece and piece.color == self.human_color:
            self.selected_square = board_square
            self.legal_moves = self.board_state.legal_moves_from(board_square)
        else:
            self.selected_square = None
            self.legal_moves = []

    def _should_ai_move(self) -> bool:
        board = self.board_state.board
        return (
            not self.board_state.is_game_over()
            and board.turn == self.ai_color
            and not self.promotion_choices
        )

    def _perform_ai_move(self) -> None:
        move = self.ai_engine.choose_move(self.board_state.board)
        if move is not None:
            self.board_state.push_move(move)
        self.selected_square = None
        self.legal_moves = []

    def _execute_move(self, move: chess.Move) -> None:
        ok, _ = self.board_state.push_move(move)
        if ok:
            self.selected_square = None
            self.legal_moves = []

    def _undo_last_move(self) -> None:
        if not self.board_state.board.move_stack:
            return

        self.board_state.undo_last_move()
        # In PvE, undo the paired move so user can re-choose.
        if self.board_state.board.turn != self.human_color and self.board_state.board.move_stack:
            self.board_state.undo_last_move()

        self.selected_square = None
        self.legal_moves = []
        self.promotion_choices = []
        self.promotion_rects = []

    def _restart_game(self) -> None:
        self.board_state.reset()
        self.selected_square = None
        self.legal_moves = []
        self.promotion_choices = []
        self.promotion_rects = []

    def _mouse_to_square(self, mouse: tuple[int, int]) -> chess.Square | None:
        mx, my = mouse
        if not (self.board_x <= mx < self.board_x + self.board_size):
            return None
        if not (self.board_y <= my < self.board_y + self.board_size):
            return None

        file_index = (mx - self.board_x) // self.square_size
        rank_index = 7 - ((my - self.board_y) // self.square_size)
        return chess.square(file_index, rank_index)

    def _square_to_rect(self, square: chess.Square) -> pygame.Rect:
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)
        x = self.board_x + file_index * self.square_size
        y = self.board_y + (7 - rank_index) * self.square_size
        return pygame.Rect(x, y, self.square_size, self.square_size)

    def _build_promotion_menu(self) -> None:
        self.promotion_rects = []
        if not self.promotion_choices:
            return

        start_x = 560
        start_y = 300
        width = 50
        height = 40
        gap = 6

        for idx, move in enumerate(self.promotion_choices):
            rect = pygame.Rect(start_x, start_y + idx * (height + gap), width, height)
            self.promotion_rects.append((move, rect))

    def _draw_frame(self) -> None:
        self.screen.fill(self.colors["bg"])
        self._draw_board()
        self._draw_panel()
        self._draw_status_bar()

        if self.promotion_choices:
            self._draw_promotion_menu()

        if self.board_state.is_game_over():
            self._draw_game_over_overlay()

    def _draw_board(self) -> None:
        # Squares
        for rank in range(8):
            for file_index in range(8):
                x = self.board_x + file_index * self.square_size
                y = self.board_y + rank * self.square_size
                is_light = (rank + file_index) % 2 == 0
                color = self.colors["light"] if is_light else self.colors["dark"]
                pygame.draw.rect(self.screen, color, (x, y, self.square_size, self.square_size))

        # Selected piece highlight
        if self.selected_square is not None:
            rect = self._square_to_rect(self.selected_square)
            pygame.draw.rect(self.screen, self.colors["sel"], rect, 4)

        # Legal moves hint
        for move in self.legal_moves:
            rect = self._square_to_rect(move.to_square)
            center = rect.center
            if self.board_state.board.is_capture(move):
                pygame.draw.circle(self.screen, self.colors["move"], center, 20, width=3)
            else:
                pygame.draw.circle(self.screen, self.colors["move"], center, 8)

        # Pieces
        for square, piece in self.board_state.board.piece_map().items():
            char = piece_unicode(piece)
            if not char:
                continue
            rect = self._square_to_rect(square)
            text = self.font_piece.render(char, True, self.colors["text"])
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

        # Border
        pygame.draw.rect(
            self.screen,
            self.colors["black"],
            (self.board_x, self.board_y, self.board_size, self.board_size),
            width=2,
        )

    def _draw_panel(self) -> None:
        pygame.draw.rect(self.screen, self.colors["panel"], self.panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, self.colors["muted"], self.panel_rect, width=1, border_radius=8)

        title = self.font_title.render("Move History", True, self.colors["text"])
        self.screen.blit(title, (536, 32))

        history = self.board_state.formatted_move_history()
        start_y = 60
        line_height = 20
        max_lines = 16
        visible = history[-max_lines:]

        for idx, line in enumerate(visible):
            txt = self.font_small.render(line, True, self.colors["text"])
            self.screen.blit(txt, (536, start_y + idx * line_height))

        cap_title = self.font_title.render("Captured", True, self.colors["text"])
        self.screen.blit(cap_title, (536, 400))

        white_cap = "".join(symbol_unicode(s) for s in self.board_state.captured_white)
        black_cap = "".join(symbol_unicode(s) for s in self.board_state.captured_black)

        line1 = self.font_small.render(f"White lost: {white_cap or '-'}", True, self.colors["text"])
        line2 = self.font_small.render(f"Black lost: {black_cap or '-'}", True, self.colors["text"])
        self.screen.blit(line1, (536, 430))
        self.screen.blit(line2, (536, 455))

        help_text = [
            "Controls:",
            "Click piece to see legal moves",
            "Ctrl+Z: Undo move",
            "R: Restart",
        ]
        for idx, msg in enumerate(help_text):
            txt = self.font_small.render(msg, True, self.colors["muted"])
            self.screen.blit(txt, (536, 485 + idx * 18))

    def _draw_status_bar(self) -> None:
        pygame.draw.rect(self.screen, self.colors["status"], self.status_rect, border_radius=8)
        pygame.draw.rect(self.screen, self.colors["muted"], self.status_rect, width=1, border_radius=8)

        status = self.board_state.status_text()
        status_text = self.font_status.render(status, True, self.colors["text"])
        self.screen.blit(status_text, (32, 540))

        pygame.draw.rect(self.screen, (198, 160, 112), self.restart_rect, border_radius=6)
        restart = self.font_small.render("Restart", True, self.colors["black"])
        self.screen.blit(restart, (self.restart_rect.x + 24, self.restart_rect.y + 9))

        diff_label = self.font_small.render("AI", True, self.colors["text"])
        self.screen.blit(diff_label, (660, 510))

        for key, rect in self.diff_buttons.items():
            active = self.ai_engine.difficulty == key
            color = (84, 166, 96) if active else (214, 196, 160)
            pygame.draw.rect(self.screen, color, rect, border_radius=5)
            txt = self.font_small.render(key[0].upper(), True, self.colors["black"])
            self.screen.blit(txt, (rect.x + 13, rect.y + 9))

    def _draw_promotion_menu(self) -> None:
        panel = pygame.Rect(548, 258, 120, 230)
        pygame.draw.rect(self.screen, (232, 221, 198), panel, border_radius=8)
        pygame.draw.rect(self.screen, self.colors["muted"], panel, width=1, border_radius=8)

        caption = self.font_small.render("Promote to", True, self.colors["text"])
        self.screen.blit(caption, (566, 270))

        for move, rect in self.promotion_rects:
            pygame.draw.rect(self.screen, (205, 185, 153), rect, border_radius=6)
            symbol = chess.Piece(move.promotion, self.human_color).symbol()
            glyph = symbol_unicode(symbol)
            txt = self.font_piece.render(glyph, True, self.colors["text"])
            txt_rect = txt.get_rect(center=rect.center)
            self.screen.blit(txt, txt_rect)

    def _draw_game_over_overlay(self) -> None:
        overlay = pygame.Surface((self.board_size, self.board_size), pygame.SRCALPHA)
        overlay.fill(self.colors["overlay"])
        self.screen.blit(overlay, (self.board_x, self.board_y))

        message = self.board_state.game_over_text()
        text = self.font_status.render(message, True, self.colors["white"])
        rect = text.get_rect(center=(self.board_x + self.board_size // 2, self.board_y + self.board_size // 2 - 20))
        self.screen.blit(text, rect)

        sub = self.font_small.render("Click Restart or press R", True, self.colors["white"])
        sub_rect = sub.get_rect(center=(self.board_x + self.board_size // 2, self.board_y + self.board_size // 2 + 12))
        self.screen.blit(sub, sub_rect)
