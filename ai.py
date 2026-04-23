"""
Chess AI engine with three difficulty levels.

- Easy  : Random legal move.
- Medium: Minimax with alpha-beta pruning, search depth 3.
- Hard  : Minimax with alpha-beta pruning, search depth 5,
          piece-square tables, and move ordering.
"""

import random
import chess

# ---------------------------------------------------------------------------
# Piece material values (centipawns)
# ---------------------------------------------------------------------------
PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}

# ---------------------------------------------------------------------------
# Piece-square tables (White's perspective, rank 8 at index 0, rank 1 at 56)
# Each table is 64 integers, row-major from rank 8 → rank 1.
# ---------------------------------------------------------------------------
_PST_PAWN = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]

_PST_KNIGHT = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

_PST_BISHOP = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20,
]

_PST_ROOK = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]

_PST_QUEEN = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20,
]

_PST_KING_MID = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20,
]

_PST_KING_END = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50,
]

_PST = {
    chess.PAWN:   _PST_PAWN,
    chess.KNIGHT: _PST_KNIGHT,
    chess.BISHOP: _PST_BISHOP,
    chess.ROOK:   _PST_ROOK,
    chess.QUEEN:  _PST_QUEEN,
    chess.KING:   _PST_KING_MID,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pst_index(square: int, color: chess.Color) -> int:
    """Map a python-chess square to a piece-square table index.

    The PST is stored rank 8→1 (index 0 = a8, 7 = h8, 56 = a1, 63 = h1).
    python-chess square a1=0 … h8=63.

    For White we read the table normally (top = opponent's side).
    For Black we mirror vertically (flip rank).
    """
    rank = chess.square_rank(square)   # 0=rank1 … 7=rank8
    file = chess.square_file(square)   # 0=a … 7=h
    if color == chess.WHITE:
        return (7 - rank) * 8 + file
    else:
        return rank * 8 + file


def _is_endgame(board: chess.Board) -> bool:
    """Return True when few major pieces remain (endgame heuristic)."""
    queens = (
        len(board.pieces(chess.QUEEN, chess.WHITE))
        + len(board.pieces(chess.QUEEN, chess.BLACK))
    )
    rooks = (
        len(board.pieces(chess.ROOK, chess.WHITE))
        + len(board.pieces(chess.ROOK, chess.BLACK))
    )
    return queens == 0 or (queens <= 2 and rooks <= 2)


# ---------------------------------------------------------------------------
# Static evaluation
# ---------------------------------------------------------------------------

def evaluate(board: chess.Board) -> int:
    """Static evaluation function.

    Returns a score in centipawns:
      positive  → good for White
      negative  → good for Black
    """
    if board.is_checkmate():
        # The side *to move* is in checkmate → that side loses
        return -100_000 if board.turn == chess.WHITE else 100_000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    endgame = _is_endgame(board)
    score = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        material = PIECE_VALUES[piece.piece_type]

        if endgame and piece.piece_type == chess.KING:
            pst_bonus = _PST_KING_END[_pst_index(square, piece.color)]
        else:
            pst_bonus = _PST[piece.piece_type][_pst_index(square, piece.color)]

        if piece.color == chess.WHITE:
            score += material + pst_bonus
        else:
            score -= material + pst_bonus

    # Small mobility bonus
    score += len(list(board.legal_moves)) * (5 if board.turn == chess.WHITE else -5)

    return score


# ---------------------------------------------------------------------------
# Move ordering (improves alpha-beta cut-offs)
# ---------------------------------------------------------------------------

def _order_moves(board: chess.Board, moves):
    """Return moves sorted so captures / promotions come first."""

    def priority(move):
        score = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                # MVV-LVA: most valuable victim, least valuable attacker
                score += 10 * PIECE_VALUES[victim.piece_type] - PIECE_VALUES[attacker.piece_type]
        if move.promotion:
            score += PIECE_VALUES.get(move.promotion, 0)
        return -score  # descending

    return sorted(moves, key=priority)


# ---------------------------------------------------------------------------
# Minimax with alpha-beta pruning
# ---------------------------------------------------------------------------

def _minimax(board: chess.Board, depth: int, alpha: int, beta: int, maximizing: bool):
    """Return (score, best_move)."""
    if depth == 0 or board.is_game_over():
        return evaluate(board), None

    best_move = None
    moves = _order_moves(board, list(board.legal_moves))

    if maximizing:
        best_score = -10_000_000
        for move in moves:
            board.push(move)
            score, _ = _minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)
            if beta <= alpha:
                break
        return best_score, best_move
    else:
        best_score = 10_000_000
        for move in moves:
            board.push(move)
            score, _ = _minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            if score < best_score:
                best_score = score
                best_move = move
            beta = min(beta, score)
            if beta <= alpha:
                break
        return best_score, best_move


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_ai_move(board: chess.Board, difficulty: str):
    """Return the AI's chosen move for the given board state.

    Parameters
    ----------
    board      : current chess.Board (AI plays the side whose turn it is)
    difficulty : 'easy' | 'medium' | 'hard'
    """
    legal = list(board.legal_moves)
    if not legal:
        return None

    if difficulty == "easy":
        return random.choice(legal)

    maximizing = board.turn == chess.WHITE

    if difficulty == "medium":
        depth = 3
    else:  # hard
        depth = 5

    _, move = _minimax(board, depth, -10_000_000, 10_000_000, maximizing)
    return move if move is not None else random.choice(legal)
