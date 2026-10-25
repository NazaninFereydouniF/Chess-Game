<h1 align="center">♟️ Chess Game v2 — Pygame</h1>

<p align="center">
  A complete chess game in Python and Pygame — with <b>full rules</b>, <b>checkmate detection</b>, <b>castling</b>, <b>en passant</b>, and a built-in <b>AI opponent</b>.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white">
  <img alt="Pygame" src="https://img.shields.io/badge/Pygame-2.x-green?logo=pygame&logoColor=white">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey">
</p>

---

## ✨ About the Project

This is a fully playable chess game built with **Python** and **Pygame**. Version 2 moves beyond "capture the king" and implements the *real* rules of chess: legal move validation, check and checkmate, castling, en passant, pawn promotion with a piece choice, and every standard draw condition. It also ships with a **built-in computer opponent** that plays at two difficulty levels.

The engine is written as a pure, self-contained logic layer with no Pygame dependency, making it easy to read, test, and extend. The UI layer on top renders the board, handles mouse input, and animates highlights and status messages.

---

## 🆕 What's New in v2

- ✅ **Full legal-move rules** — the king can never move into (or stay in) an attacked square, and pinned pieces cannot expose their king.
- ✅ **Check, checkmate & stalemate detection.**
- ✅ **Castling** (king-side and queen-side) and **en passant**.
- ✅ **Pawn promotion** with a choice of piece (queen / rook / bishop / knight).
- ✅ **Draw rules** — stalemate, threefold repetition, 50-move rule, insufficient material.
- 🤖 **Computer opponent** in Easy or Hard mode (you play White).
- 🧭 **Start menu**, last-move highlight, and quick restart / back-to-menu.

> Upgrading from v1? The old version is preserved as tag `v1.0` in this repository's history.

---

## 🎮 Features

| Feature | Description |
|---|---|
| 🖱️ Full mouse control | Click a piece, then click a destination square |
| 🟢 Legal move hints | Valid moves show as dots; captures show as rings |
| ⚔️ Check highlight | The king's square flashes when in check |
| 👑 Pawn promotion | Choose queen, rook, bishop, or knight |
| 🏰 Castling & en passant | Fully supported and legally validated |
| 🤖 AI opponent | Negamax search with quiescence, in Easy / Hard |
| 🎲 Three draw rules | Threefold repetition, 50-move rule, insufficient material |
| 🧩 Cached piece graphics | Downloaded once; falls back to built-in pieces offline |
| 📊 Captured-piece panel | Captured pieces shown per side |

---

## 🚀 Getting Started

### Requirements

- Python 3.8 or newer
- Packages: `pygame`, `requests`

```bash

pip install pygame requests  

pip install rembg
```

---

### 🕹️ How to Play
Starting a Game
When the game launches you'll see a start menu:

Play vs Computer (Easy) — the engine searches 1 ply ahead.
Play vs Computer (Hard) — the engine searches 3 plies ahead with quiescence search.
Play vs Player — two people share the same board.
Quit — close the game.
In computer mode you play White; the computer plays Black.

---

### 🎮 In-Game Controls
```basg
|     Action     |     How     |  
|----------------|-------------|  
| Select a piece | Left-click on one of your own pieces |  
|       Move     | Click one of the highlighted destination squares |  
| Promote a pawn | Choose Queen / Rook / Bishop / Knight from the popup |  
|     New game   | Press `ENTER` |  
|   Back to menu | Press `M` |  
|     Resign     | Click the **FORFEIT** button in the bottom panel |  
```
Reading the Board
Green dots mark squares where the selected piece can legally move.
A red box outlines your currently selected piece.
The king's square flashes when the king is in check.
Yellow squares show the last move that was played.

---

### 🧠 Engine & Code Structure
The project separates rules from presentation: a pure chess engine decides legality and evaluates moves, while a separate layer handles drawing and input.
```bash
Chess_Game.py
│
├── Position & state        ← board layout, side to move, castling rights,
│                             en passant square, halfmove clock
├── Attack detection        ← attacked()  — pawn, knight, king, rook, bishop, queen attacks
├── Check detection         ← in_check()
├── Move generation         ← gen_moves() — pseudo-legal moves incl. double pawn
│                             pushes, captures, promotions & castling
├── Move application        ← apply_move() — updates board, en passant, castling
│                             rights, en passant target and halfmove clock
├── Legality filter         ← legal_moves() — discards moves that leave your
│                             own king in check
├── Draw detection          ← insufficient_material(), threefold repetition,
│                             50-move rule, stalemate
├── AI search               ← negamax with alpha-beta pruning and quiescence
├── Rendering               ← board, pieces, highlights, check, side panel
└── Main loop               ← event handling and game state machine
```
---

### 🛹 Key design ideas

Pseudo-legal → legal: gen_moves() produces candidate moves, then legal_moves() filters out any move that would leave your own king attacked. This one step makes pins, checks and illegal king moves "just work".
Explicit state: castling rights, the en passant square and the halfmove clock are stored in the position, so repetition and the 50-move rule are straightforward to detect.
Cached graphics: piece images are downloaded and stored once, and a fallback renderer draws lettered circular pieces when no image is available.

---

### 🤖 AI Difficulty
```basg
|   Level  |     Search    | Notes |  
|----------|---------------|---|  
| **Easy** | Depth 1 (α-β) | Makes immediate captures, quick to respond |  
| **Hard** | Depth 3 + quiescence | Looks a few moves ahead and avoids tactical blunders |  
```
The engine uses negamax with alpha-beta pruning. Quiescence search extends capture sequences so the AI doesn't stop in the middle of an exchange.

---

### ⚠️ Known Limitations
The engine follows standard chess rules but is intended for learning and casual play, not tournament strength. In particular:

Search is shallow, so Hard is challenging but far from a strong engine; it can still miss deep combinations.
The AI may be slow on very low-end machines at the Hard setting.
There is no opening book, no transposition table, and no endgame tablebase.
Graphics are functional and lightweight rather than highly polished.
These are natural directions for future improvements. 🌱

### 🤝 Contributing
Ideas and improvements are welcome! Fork the project, make your changes, and open a Pull Request. You can also open an Issue to report a bug or suggest a feature.

---

<p align="center">
  <i>Built with Python and Pygame — have fun playing! ♟️</i>
</p>
