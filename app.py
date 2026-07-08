from flask import Flask, render_template, request, jsonify
import random

app = Flask(__name__)

def check_win(board, player):
    """Checks if the specified player has won the game."""
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8], # Columns
        [0, 4, 8], [2, 4, 6]             # Diagonals
    ]
    for cond in win_conditions:
        if board[cond[0]] == board[cond[1]] == board[cond[2]] == player:
            return True
    return False

def get_computer_move(board, computer_char, player_char):
    """
    Computes a move for the computer using a basic rule-based AI:
    1. Win if possible.
    2. Block player from winning.
    3. Take center if available.
    4. Take a corner if available.
    5. Take any remaining spot.
    """
    # Get empty indices (cells that are not 'X' or 'O')
    empty_cells = [i for i, cell in enumerate(board) if cell not in ["X", "O"]]
    
    if not empty_cells:
        return None

    # 1. Win if possible
    for cell in empty_cells:
        board_copy = list(board)
        board_copy[cell] = computer_char
        if check_win(board_copy, computer_char):
            return cell

    # 2. Block player from winning
    for cell in empty_cells:
        board_copy = list(board)
        board_copy[cell] = player_char
        if check_win(board_copy, player_char):
            return cell

    # 3. Take center (index 4) if empty
    if 4 in empty_cells:
        return 4

    # 4. Take corners (0, 2, 6, 8)
    corners = [c for c in [0, 2, 6, 8] if c in empty_cells]
    if corners:
        return random.choice(corners)

    # 5. Take sides (1, 3, 5, 7)
    sides = [s for s in [1, 3, 5, 7] if s in empty_cells]
    if sides:
        return random.choice(sides)

    # Default to any empty cell
    return random.choice(empty_cells)

@app.route('/')
def index():
    """Renders the main Tic-Tac-Toe page."""
    return render_template('index.html')

@app.route('/api/computer-move', methods=['POST'])
def api_computer_move():
    """API endpoint to request a computer move."""
    data = request.json or {}
    board = data.get('board')
    computer_char = data.get('computer_char', 'O')
    player_char = data.get('player_char', 'X')

    if not board or len(board) != 9:
        return jsonify({'error': 'Invalid board state'}), 400

    move = get_computer_move(board, computer_char, player_char)
    return jsonify({'move': move})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
