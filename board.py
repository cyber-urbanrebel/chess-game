from __future__ import annotations

import chess


class ChessBoard:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.board = chess.Board()
        self.move_history_san: list[str] = []
        self.captured_white: list[str] = []
        self.captured_black: list[str] = []
        self._undo_stack: list[dict[str, str | None]] = []

    def legal_moves_from(self, square: chess.Square) -> list[chess.Move]:
        return [move for move in self.board.legal_moves if move.from_square == square]

    def push_move(self, move: chess.Move) -> tuple[bool, str | None]:
        if move not in self.board.legal_moves:
            return False, None

        san = self.board.san(move)
        captured_piece = self._captured_piece_for_move(move)

        self.board.push(move)
        self.move_history_san.append(san)

        captured_symbol = None
        if captured_piece is not None:
            captured_symbol = captured_piece.symbol()
            if captured_piece.color == chess.WHITE:
                self.captured_white.append(captured_symbol)
            else:
                self.captured_black.append(captured_symbol)

        self._undo_stack.append({"captured": captured_symbol})
        return True, san

    def undo_last_move(self) -> bool:
        if not self.board.move_stack:
            return False

        self.board.pop()
        if self.move_history_san:
            self.move_history_san.pop()

        if self._undo_stack:
            data = self._undo_stack.pop()
            symbol = data.get("captured")
            if symbol:
                if symbol.isupper() and self.captured_white:
                    self.captured_white.pop()
                elif symbol.islower() and self.captured_black:
                    self.captured_black.pop()

        return True

    def is_game_over(self) -> bool:
        return self.board.is_game_over(claim_draw=True)

    def status_text(self) -> str:
        if self.board.is_checkmate():
            winner = "White" if self.board.turn == chess.BLACK else "Black"
            return f"Checkmate! {winner} wins."
        if self.board.is_stalemate():
            return "Stalemate. Draw game."
        if self.board.is_insufficient_material():
            return "Draw by insufficient material."
        if self.board.can_claim_threefold_repetition():
            return "Threefold repetition can be claimed."
        if self.board.can_claim_fifty_moves():
            return "Fifty-move rule can be claimed."

        turn = "White" if self.board.turn == chess.WHITE else "Black"
        suffix = " - Check!" if self.board.is_check() else ""
        return f"{turn} to move{suffix}"

    def game_over_text(self) -> str:
        if not self.is_game_over():
            return ""
        if self.board.is_checkmate():
            winner = "White" if self.board.turn == chess.BLACK else "Black"
            return f"Checkmate - {winner} wins"
        if self.board.is_stalemate():
            return "Stalemate"
        if self.board.is_insufficient_material():
            return "Draw: insufficient material"
        if self.board.is_fivefold_repetition() or self.board.can_claim_threefold_repetition():
            return "Draw: repetition"
        if self.board.is_seventyfive_moves() or self.board.can_claim_fifty_moves():
            return "Draw: 50-move rule"
        return "Draw"

    def formatted_move_history(self) -> list[str]:
        lines: list[str] = []
        for index, san in enumerate(self.move_history_san):
            if index % 2 == 0:
                lines.append(f"{index // 2 + 1}. {san}")
            else:
                lines[-1] += f" {san}"
        return lines

    def _captured_piece_for_move(self, move: chess.Move) -> chess.Piece | None:
        if self.board.is_en_passant(move):
            capture_square = move.to_square - 8 if self.board.turn == chess.WHITE else move.to_square + 8
            return self.board.piece_at(capture_square)
        return self.board.piece_at(move.to_square)
