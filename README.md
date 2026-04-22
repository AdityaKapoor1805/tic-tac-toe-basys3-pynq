# 🎮 AI-Powered Tic-Tac-Toe on Dual FPGAs (Basys 3 + PYNQ-Z2)

> A hardware-software co-design system implementing a real-time, AI-powered Tic-Tac-Toe game across two heterogeneous FPGA platforms, communicating over a UART bridge.

**Authors:** Aditya Kapoor, Suyash Pandey, Samyak Maity  
**Institution:** Department of Electrical Engineering, Shiv Nadar Institution of Eminence, Greater Noida, India

---

## 📌 Project Overview

This project implements a fully interactive Tic-Tac-Toe system using a **distributed dual-FPGA architecture**:

- **Basys 3 (Artix-7)** — Hardware game-state manager and rule enforcer, written in Verilog (RTL)
- **PYNQ-Z2 (Zynq-7000 SoC)** — Application layer: Minimax AI, 1080p HDMI GUI, USB mouse input, and mode switching
- **FT232 USB-TTL Adapter** — UART bridge connecting both boards at 9600 baud via Pmod headers

The system supports both **1-Player (Human vs Unbeatable AI)** and **2-Player (Human vs Human)** modes, switchable in real-time via a hardware slide switch on the PYNQ-Z2.

---

## 🏗️ System Architecture

```
┌─────────────────────┐      UART / FT232       ┌──────────────────────────┐
│     Basys 3         │ ◄──────────────────────► │       PYNQ-Z2            │
│  (Artix-7 FPGA)     │    ASCII Protocol        │   (Zynq-7000 SoC)        │
│                     │    9600 baud             │                          │
│  • Game State FSM   │                          │  • Minimax AI (Python)   │
│  • Rule Enforcement │                          │  • HDMI 1080p GUI        │
│  • Win Detection    │                          │  • USB Mouse (evdev)     │
│  • UART Transceiver │                          │  • HW Switch Polling     │
└─────────────────────┘                          └──────────────────────────┘
         ▲                                                    ▲
    7-Seg Display                                      HDMI Monitor
    LEDs / Buttons                                     USB Mouse
```

---

## 📁 Repository Structure

```
.
├── basys3/
│   ├── game_ctrl.v       # Core FSM: game state, rule enforcement, win detection
│   ├── uart_rx.v         # UART Receiver module (9600 baud, center-sampling)
│   ├── uart_tx.v         # UART Transmitter module
│   ├── top.v             # Top-level Verilog wrapper
│   └── basys3.xdc        # Xilinx Design Constraints (pin mapping)
│
├── pynq/
│   ├── main3.py          # Main application: GUI, mouse input, UART, threading
│   └── minimax.py        # Minimax AI algorithm (unbeatable O player)
│
└── README.md
```

---

## ⚙️ Hardware Requirements

| Component | Details |
|-----------|---------|
| Basys 3 FPGA Board | Digilent, Artix-7 XC7A35T |
| PYNQ-Z2 Board | TUL, Zynq-7000 XC7Z020 |
| FT232 USB-TTL Adapter | 3.3V logic, connected via Pmod JA |
| USB Mouse | Standard HID, plugged into PYNQ-Z2 USB Host |
| HDMI Monitor | 1920×1080 @ 60Hz |
| Jumper Wires | For TX/RX/GND connections between FT232 and Pmod |

---

## 🔌 Wiring / Pin Connections

### FT232 ↔ Basys 3 Pmod (JA Header)

| FT232 Pin | Basys 3 Pmod Pin | Signal |
|-----------|-----------------|--------|
| TX | JA[0] (Pin 1) | UART RX into Basys 3 |
| RX | JA[1] (Pin 2) | UART TX out of Basys 3 |
| GND | GND | Common Ground |

The FT232's USB end connects to the **USB Host port of the PYNQ-Z2**, where Linux mounts it as `/dev/ttyUSB0`.

---

## 🚀 Getting Started

### 1. Basys 3 — Synthesize and Program

1. Open **Xilinx Vivado** (tested on 2020.x / 2022.x)
2. Create a new RTL project and add all files from `basys3/`
3. Set `top.v` as the top module
4. Add `basys3.xdc` as the constraints file
5. Run **Synthesis → Implementation → Generate Bitstream**
6. Connect Basys 3 via USB and click **Program Device**

### 2. PYNQ-Z2 — Deploy Python Application

SSH into or use the Jupyter interface on your PYNQ-Z2 (default IP: `192.168.2.99`).

```bash
# Copy files to the PYNQ board (from your PC)
scp pynq/main3.py pynq/minimax.py xilinx@192.168.2.99:/home/xilinx/

# On the PYNQ board, install dependencies
pip install pyserial opencv-python

# Run the application (requires root for HDMI/evdev access)
sudo python3 main3.py
```

> **Note:** The PYNQ base overlay (`base.bit`) must be present and accessible. It is pre-installed on standard PYNQ-Z2 SD card images.

### 3. Play!

- **Left-click** a cell on the monitor to place your piece
- **Right-click** anywhere to reset the game
- **SW0 on PYNQ-Z2**: UP = 2-Player mode | DOWN = 1-Player (vs AI) mode

---

## 🧠 UART Communication Protocol

The two boards communicate via a fixed ASCII protocol:

**PYNQ → Basys 3 (1 byte):**
- `'1'`–`'9'` : Place a piece on cell 1–9 (row-major order)
- `'R'` : Hard reset the game

**Basys 3 → PYNQ (10 bytes + newline):**
- Bytes 0–8: Board state — `'X'` (Player 1), `'O'` (Player 2/AI), `'0'` (empty)
- Byte 9: Status flag — `'G'` (ongoing), `'W'` (X wins), `'L'` (O wins), `'D'` (draw)

Example response: `X00OX000O W\n`

---

## 🤖 AI — Minimax Algorithm

The AI (`minimax.py`) plays as **O** and is theoretically unbeatable. It uses a recursive depth-first **Minimax** search over the full game tree (max ~986,410 nodes at game start).

**Optimizations:**
- Center-first heuristic: always plays cell 4 (index) if free
- Board copy isolation: passes `board.copy()` to prevent GUI hallucination
- Daemon thread + 100ms sleep: allows the UI to render "AI thinking..." before locking the GIL

---

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| Hardware validation latency (Basys 3 FSM) | ~30 ns (3 clock cycles @ 100 MHz) |
| UART transfer latency (1 byte) | ~1.04 ms |
| UART full 10-byte response | ~10.41 ms |
| AI Minimax execution (worst case, move 1) | ~18.5 ms |
| Total worst-case system reaction time | < 30 ms |
| HDMI output resolution | 1920 × 1080 @ 60 Hz |
| UART baud rate | 9600 bps |

---

## 🔬 Key Design Decisions

- **Metastability mitigation**: All async inputs (UART RX, buttons) pass through a 2-stage D flip-flop synchronizer
- **Thread safety**: All UART reads/writes are wrapped in a `threading.Lock()` (`uart_lock`) to prevent packet collisions
- **GIL management**: AI runs in a daemon thread; `time.sleep(0.1)` explicitly yields CPU to the render loop before Minimax executes
- **Hardware rule enforcement**: The Basys 3 FSM rejects illegal/duplicate moves at the gate level — Python cannot cheat the board

---

## 📄 Report

A full IEEE-format paper detailing the architecture, implementation, and results is included in `FPGA_REPORT.pdf`.

---

## 🙏 Acknowledgements

Thanks to **Ms. Sonal Singhal** and **Mr. Rohit Singh**, Department of Electrical Engineering, Shiv Nadar University, for their guidance. Hardware provided by the EE Laboratory, SNU Delhi NCR.

---

## 📜 License

This project was developed for academic purposes at Shiv Nadar Institution of Eminence. Feel free to fork and build upon it with attribution.
