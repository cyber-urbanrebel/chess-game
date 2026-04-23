from __future__ import annotations

import math
import random

import chess

from pieces import PIECE_VALUES, positional_bonus


class ChessAI:
    DEPTH_MAP = {
        "easy": 2,
        "medium": 3,
        "hard": 4,
    }

    def __init__(self, difficulty: str = "Medium") -> None:
        self.difficulty = "medium"
        self.depth = 3
        self.set_difficulty(difficulty)

    def set_difficulty(self, difficulty: str) -> None:
        key = difficulty.strip().lower()
        if key not in self.DEPTH_MAP:
            key = "medium"
        self.difficulty = key
        self.depth = self.DEPTH_MAP[key]

    def choose_move(self, board: chess.Board) -> chess.Move | None:
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None

        alpha = -math.inf
        beta = math.inf
        best_score = -math.inf
        best_move: chess.Move | None = None

        for move in self._ordered_moves(board):
            board.push(move)
            score = -self._negamax(board, self.depth - 1, -beta, -alpha)
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move

            alpha = max(alpha, score)

        if best_move is None:
            return random.choice(legal_moves)
        return best_move

    def _negamax(self, board: chess.Board, depth: int, alpha: float, beta: float) -> float:
        if depth == 0 or board.is_game_over(claim_draw=True):
            return self._evaluate_for_side_to_move(board, depth)

        value = -math.inf
        for move in self._ordered_moves(board):
            board.push(move)
            score = -self._negamax(board, depth - 1, -beta, -alpha)
            board.pop()

            value = max(value, score)
            alpha = max(alpha, score)
            if alpha >= beta:
                break

        return value

    def _evaluate_for_side_to_move(self, board: chess.Board, depth: int) -> float:
        if board.is_checkmate():
            # Side to move is checkmated.
            return -100000 + (self.depth - depth)
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
        if board.can_claim_threefold_repetition() or board.can_claim_fifty_moves():
            return 0

        base = self._static_eval_white_minus_black(board)
        return base if board.turn == chess.WHITE else -base

    def _static_eval_white_minus_black(self, board: chess.Board) -> float:
        score = 0.0

        for square, piece in board.piece_map().items():
            material = PIECE_VALUES[piece.piece_type]
            positional = positional_bonus(piece, square)
            total = material + positional
            if piece.color == chess.WHITE:
                score += total
            else:
                score -= total

        # Mild mobility term to avoid passive play.
        mobility = board.legal_moves.count()
        if board.turn == chess.WHITE:
            score += mobility * 1.5
        else:
            score -= mobility * 1.5

        return score

    def _ordered_moves(self, board: chess.Board) -> list[chess.Move]:
        def move_score(move: chess.Move) -> int:
            score = 0
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim is not None:
                    score += 10 * PIECE_VALUES[victim.piece_type]
                if attacker is not None:
                    score -= PIECE_VALUES[attacker.piece_type]
            if move.promotion:
                score += PIECE_VALUES.get(move.promotion, 0)
            if board.gives_check(move):
                score += 50
            return score

        return sorted(board.legal_moves, key=move_score, reverse=True)
