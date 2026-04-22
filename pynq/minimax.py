"""
minimax.py – Tic-Tac-Toe AI
============================
AI plays as O (value 2).  Human plays as X (value 1).
board is a flat list of 9 ints: 0=empty, 1=X, 2=O.
"""

from typing import Optional

WINS = [
    (0,1,2),(3,4,5),(6,7,8),   # rows
    (0,3,6),(1,4,7),(2,5,8),   # cols
    (0,4,8),(2,4,6)            # diags
]


def check_winner(board: list[int]) -> Optional[int]:
    """Return 1 (X wins), 2 (O wins), 0 (draw), or None (ongoing)."""
    for a, b, c in WINS:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return 0          # draw
    return None


def minimax(board: list[int], is_maximizing: bool) -> int:
    """
    is_maximizing = True  → O's turn (AI, wants to maximise)
    is_maximizing = False → X's turn (human, wants to minimise)
    """
    result = check_winner(board)
    if result is not None:
        if result == 2: return  10   # O wins
        if result == 1: return -10   # X wins
        return 0                     # draw

    if is_maximizing:
        best = -100
        for i in range(9):
            if board[i] == 0:
                board[i] = 2
                score = minimax(board, False)
                board[i] = 0
                best = max(best, score)
        return best
    else:
        best = 100
        for i in range(9):
            if board[i] == 0:
                board[i] = 1
                score = minimax(board, True)
                board[i] = 0
                best = min(best, score)
        return best


def best_move(board: list[int]) -> Optional[int]:
    """
    Return the 0-based index of the best move for O (AI).
    Returns None if no move is available.
    """
    best_score = -1000
    best_idx   = None

    # Prefer center if free
    if board[4] == 0:
        return 4

    for i in range(9):
        if board[i] == 0:
            board[i] = 2
            score = minimax(board, False)
            board[i] = 0
            if score > best_score:
                best_score = score
                best_idx   = i

    return best_idx
