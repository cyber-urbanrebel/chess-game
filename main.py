from ai import ChessAI
from board import ChessBoard
from ui import ChessUI


def main() -> None:
    board_state = ChessBoard()
    ai_engine = ChessAI("Medium")
    app = ChessUI(board_state, ai_engine)
    app.run()


if __name__ == "__main__":
    main()
