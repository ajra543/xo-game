// Game State variables
let board = ["", "", "", "", "", "", "", "", ""];
let currentPlayer = "X";
let gameActive = true;
let gameMode = "pvp"; // 'pvp' or 'pvc'

// Score tracking
let scores = {
    X: 0,
    O: 0,
    draws: 0
};

// Winning conditions index lookup
const WINNING_COMBINATIONS = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8], // Rows
    [0, 3, 6], [1, 4, 7], [2, 5, 8], // Columns
    [0, 4, 8], [2, 4, 6]             // Diagonals
];

// DOM elements
const cells = document.querySelectorAll(".cell");
const statusText = document.getElementById("game-status");
const scoreX = document.getElementById("score-x");
const scoreO = document.getElementById("score-o");
const scoreDraw = document.getElementById("score-draw");
const boardElement = document.getElementById("board");
const labelO = document.getElementById("label-o");

function setMode(mode) {
    if (gameMode === mode) return;
    
    gameMode = mode;
    
    // Toggle active state in buttons
    document.getElementById("btn-pvp").classList.toggle("active", mode === "pvp");
    document.getElementById("btn-pvc").classList.toggle("active", mode === "pvc");
    
    // Update Scoreboard Label for O
    if (mode === "pvc") {
        labelO.textContent = "COMPUTER";
    } else {
        labelO.textContent = "PLAYER O";
    }
    
    // Reset Scores for a fresh match mode
    scores.X = 0;
    scores.O = 0;
    scores.draws = 0;
    updateScoreboardDisplay();
    
    // Reset game board
    resetGame();
}

function makeMove(index) {
    if (board[index] !== "" || !gameActive) return;
    
    // Process Player move
    executeMove(index, currentPlayer);
    
    if (!gameActive) return;
    
    // Shift Turn
    currentPlayer = currentPlayer === "X" ? "O" : "X";
    updateStatusDisplay();
    
    // If it's VS Computer and it is O's turn, call Flask API
    if (gameMode === "pvc" && currentPlayer === "O") {
        triggerComputerMove();
    }
}

function executeMove(index, player) {
    board[index] = player;
    
    const cell = document.getElementById(`cell-${index}`);
    cell.textContent = player;
    cell.classList.add(player === "X" ? "x-val" : "o-val");
    
    // Check outcome
    const winCombo = checkWinResult(player);
    if (winCombo) {
        handleWin(player, winCombo);
        return;
    }
    
    if (checkDrawResult()) {
        handleDraw();
        return;
    }
}

async function triggerComputerMove() {
    // Disable inputs while computer is thinking
    boardElement.classList.add("disabled");
    statusText.innerHTML = `Computer thinking<span class="turn-highlight o-turn">...</span>`;
    
    // Small delay to simulate computer processing (adds immersion)
    await new Promise(resolve => setTimeout(resolve, 600));
    
    try {
        const response = await fetch("/api/computer-move", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                board: board,
                computer_char: "O",
                player_char: "X"
            })
        });
        
        if (!response.ok) throw new Error("API call failed");
        
        const data = await response.json();
        const move = data.move;
        
        if (move !== null && move !== undefined && board[move] === "") {
            executeMove(move, "O");
            
            if (gameActive) {
                currentPlayer = "X";
                updateStatusDisplay();
            }
        }
    } catch (error) {
        console.error("Error communicating with AI backend: ", error);
        // Fallback: Random move on local frontend if backend fails
        fallbackRandomMove();
    } finally {
        // Re-enable inputs
        boardElement.classList.remove("disabled");
    }
}

function fallbackRandomMove() {
    const emptyIndices = board.map((val, idx) => val === "" ? idx : null).filter(val => val !== null);
    if (emptyIndices.length > 0) {
        const randomIdx = emptyIndices[Math.floor(Math.random() * emptyIndices.length)];
        executeMove(randomIdx, "O");
        if (gameActive) {
            currentPlayer = "X";
            updateStatusDisplay();
        }
    }
}

function checkWinResult(player) {
    for (const combination of WINNING_COMBINATIONS) {
        if (
            board[combination[0]] === player &&
            board[combination[1]] === player &&
            board[combination[2]] === player
        ) {
            return combination;
        }
    }
    return null;
}

function checkDrawResult() {
    return board.every(cell => cell !== "");
}

function handleWin(winner, winCombo) {
    gameActive = false;
    
    // Highlight winning cells
    const winClass = winner === "X" ? "win-cell-x" : "win-cell-o";
    winCombo.forEach(index => {
        document.getElementById(`cell-${index}`).classList.add(winClass);
    });
    
    // Update Score
    scores[winner]++;
    updateScoreboardDisplay();
    
    // Update status text
    if (gameMode === "pvc") {
        statusText.innerHTML = winner === "X" 
            ? `<span class="turn-highlight x-turn">You Win!</span>` 
            : `<span class="turn-highlight o-turn">Computer Wins!</span>`;
    } else {
        statusText.innerHTML = `<span class="turn-highlight ${winner === 'X' ? 'x-turn' : 'o-turn'}">Player ${winner} Wins!</span>`;
    }
}

function handleDraw() {
    gameActive = false;
    scores.draws++;
    updateScoreboardDisplay();
    statusText.textContent = "It's a Draw!";
}

function updateStatusDisplay() {
    const highlightClass = currentPlayer === "X" ? "x-turn" : "o-turn";
    statusText.innerHTML = `<span class="turn-highlight ${highlightClass}">${currentPlayer}</span>'s Turn`;
}

function updateScoreboardDisplay() {
    scoreX.textContent = scores.X;
    scoreO.textContent = scores.O;
    scoreDraw.textContent = scores.draws;
}

function resetGame() {
    board = ["", "", "", "", "", "", "", "", ""];
    currentPlayer = "X";
    gameActive = true;
    
    // Update board UI
    cells.forEach(cell => {
        cell.textContent = "";
        cell.className = "cell"; // resets all classes including glows and values
    });
    
    boardElement.classList.remove("disabled");
    updateStatusDisplay();
}

// Initialize status display at load
updateStatusDisplay();
