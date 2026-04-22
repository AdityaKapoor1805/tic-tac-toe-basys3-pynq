#!/usr/bin/env python3
import os
import sys
import time
import struct
import threading
import serial
import cv2
import minimax
import numpy as np
from pynq.overlays.base import BaseOverlay
from pynq.lib.video import VideoMode

# ── Configuration ────────────────────────────────────────────
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE   = 9600
SCREEN_W    = 1920  # Switched to 1080p
SCREEN_H    = 1080

# OpenCV uses BGR (Blue, Green, Red) instead of RGB
C_BG        = (25, 15, 15)
C_GRID      = (130, 80, 60)
C_X         = (60, 80, 220)    # Reddish
C_O         = (220, 160, 60)   # Blueish
C_HOVER     = (80, 50, 40)
C_TEXT      = (230, 220, 220)
C_BTN_BG    = (110, 60, 40)

CELL_SIZE   = 200
GRID_SIZE   = CELL_SIZE * 3
OFFSET_X    = (SCREEN_W - GRID_SIZE) // 2
OFFSET_Y    = (SCREEN_H - GRID_SIZE) // 2
LINE_W      = 8

# ── Hardware Init ────────────────────────────────────────────
print("Initializing Base Overlay and HDMI...")
base = BaseOverlay("base.bit")
hdmi_out = base.video.hdmi_out
mode = VideoMode(1920, 1080, 24)
hdmi_out.configure(mode)
hdmi_out.start()
print("HDMI Started.")

print("Connecting to mouse on /dev/input/event0...")
try:
    mouse_fd = os.open('/dev/input/event0', os.O_RDONLY | os.O_NONBLOCK)
except Exception as e:
    print("ERROR: Could not open mouse. Is it plugged in?")
    hdmi_out.stop()
    raise

EVENT_FORMAT = 'llHHi'
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

# ── Board state & UART Variables ─────────────────────────────
board       = [0] * 9  # 0=empty 1=X 2=O
game_over   = False
ai_thinking = False    # Replaced human_turn to handle 2-player logic better
status_msg  = ""

uart_lock   = threading.Lock()
ser         = None

cursor_x, cursor_y = SCREEN_W // 2, SCREEN_H // 2
click_processed = False

# ── UART helpers ─────────────────────────────────────────────
def uart_open():
    global ser
    try:
        ser = serial.Serial(port=SERIAL_PORT, baudrate=BAUD_RATE, timeout=2)
        print(f"[UART] Opened {SERIAL_PORT}")
    except serial.SerialException as e:
        print(f"[UART] Failed: {e}")
        ser = None

def uart_send_move(cell_1based: int):
    if ser and ser.is_open:
        with uart_lock:
            ser.write(bytes([ord('1') + cell_1based - 1]))
            ser.flush()

def uart_reset():
    if ser and ser.is_open:
        with uart_lock:
            ser.write(b'R')
            ser.flush()

def uart_read_state() -> dict | None:
    if not (ser and ser.is_open): return None
    with uart_lock:
        raw = ser.read_until(b'\n')
        print(f"DEBUG UART RECEIVED: {raw}")
    if len(raw) < 10: return None
    
    bd_chars = raw[:9]
    status   = chr(raw[9]) if len(raw) > 9 else 'G'

    def decode(c):
        if c == ord('X'): return 1
        if c == ord('O'): return 2
        return 0

    return {'board': [decode(c) for c in bd_chars], 'status': status}

# ── Game logic ───────────────────────────────────────────────
def update_status_for_turn():
    """Reads the physical switch on the PYNQ board to set UI text."""
    global status_msg
    if game_over: return
    
    # Read Switch 0 from the PYNQ board (1 = UP, 0 = DOWN)
    is_2player = base.switches[0].read()
    
    # Count pieces to determine whose turn it is
    turn_count = sum(1 for x in board if x != 0)
    is_x_turn = (turn_count % 2 == 0)
    
    if is_2player:
        status_msg = "Player 1's turn (X)" if is_x_turn else "Player 2's turn (O)"
    else:
        if is_x_turn:
            status_msg = "Your turn (X)"
        else:
            status_msg = "AI thinking (Python)..."

def apply_state(state: dict):
    global board, game_over, status_msg
    board = state['board']
    s = state['status']
    if s == 'W':
        game_over = True; status_msg = "X WINS! (Right-click reset)"
    elif s == 'L':
        game_over = True; status_msg = "O WINS! (Right-click reset)"
    elif s == 'D':
        game_over = True; status_msg = "DRAW! (Right-click reset)"
    else:
        game_over = False
        update_status_for_turn() # Fixes the stuck text bug!

def ai_move_thread():
    global board, status_msg, ai_thinking
    ai_thinking = True
    update_status_for_turn() 

    # Yield the CPU for just a moment (100ms) so the UI 
    # has a chance to physically render the "AI thinking..." text to the screen.
    time.sleep(0.1)

    # Pass a COPY of the board so the Minimax algorithm 
    # doesn't visually mutate the real board during its search.
    best_move = minimax.best_move(board.copy())

    # Tell the FPGA about the AI's move
    uart_send_move(best_move + 1) 

    # Refresh local state
    state = uart_read_state()
    if state:
        apply_state(state)

    ai_thinking = False
    if not game_over:
        update_status_for_turn() # Reset text back to human turn

def do_human_move(idx: int):
    global status_msg, ai_thinking
    if board[idx] != 0 or game_over or ai_thinking:
        return

    is_2player = base.switches[0].read()
    turn_count = sum(1 for x in board if x != 0)
    is_x_turn = (turn_count % 2 == 0)

    # In single-player, ignore clicks if it's the AI's turn
    if not is_2player and not is_x_turn:
        return

    # Optimistic local update
    board[idx] = 1 if is_x_turn else 2 
    status_msg = "Sending move..."
    
    uart_send_move(idx + 1)
    
    # Wait for initial board update
    state = uart_read_state()
    if state:
        apply_state(state)
    
    if not game_over:
        if not is_2player:
            # Single-player: Trigger AI
            t = threading.Thread(target=ai_move_thread, daemon=True)
            t.start()
        else:
            # Two-player: Just update text for the next human
            update_status_for_turn()

def reset_game():
    global board, game_over, status_msg, ai_thinking
    board       = [0] * 9
    game_over   = False
    ai_thinking = False
    uart_reset()
    uart_read_state() 
    update_status_for_turn() # Initialize the correct text based on the switch

# ── Drawing (OpenCV) ─────────────────────────────────────────
def draw_ui(frame):
    frame[:] = C_BG # Fill background
    
    # Draw Grid
    for i in range(1, 3):
        cv2.line(frame, (OFFSET_X + i*CELL_SIZE, OFFSET_Y), 
                 (OFFSET_X + i*CELL_SIZE, OFFSET_Y + GRID_SIZE), C_GRID, LINE_W)
        cv2.line(frame, (OFFSET_X, OFFSET_Y + i*CELL_SIZE), 
                 (OFFSET_X + GRID_SIZE, OFFSET_Y + i*CELL_SIZE), C_GRID, LINE_W)

    # Hover effect (Draws a border around cell)
    if not game_over and not ai_thinking:
        if OFFSET_X <= cursor_x <= OFFSET_X + GRID_SIZE and OFFSET_Y <= cursor_y <= OFFSET_Y + GRID_SIZE:
            col = int((cursor_x - OFFSET_X) // CELL_SIZE)
            row = int((cursor_y - OFFSET_Y) // CELL_SIZE)
            idx = row * 3 + col
            if board[idx] == 0:
                rect_x1, rect_y1 = OFFSET_X + col*CELL_SIZE, OFFSET_Y + row*CELL_SIZE
                cv2.rectangle(frame, (rect_x1+5, rect_y1+5), 
                              (rect_x1+CELL_SIZE-5, rect_y1+CELL_SIZE-5), C_HOVER, 4)

    # Draw Pieces
    for idx, val in enumerate(board):
        if val == 0: continue
        col = idx % 3
        row = idx // 3
        cx = OFFSET_X + col * CELL_SIZE + CELL_SIZE // 2
        cy = OFFSET_Y + row * CELL_SIZE + CELL_SIZE // 2
        r = CELL_SIZE // 3
        
        if val == 1: # X
            cv2.line(frame, (cx-r, cy-r), (cx+r, cy+r), C_X, LINE_W+4)
            cv2.line(frame, (cx+r, cy-r), (cx-r, cy+r), C_X, LINE_W+4)
        elif val == 2: # O
            cv2.circle(frame, (cx, cy), r, C_O, LINE_W+4)

    # Text and Cursor
    cv2.putText(frame, status_msg, (SCREEN_W//2 - 300, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, C_TEXT, 3)
    
    cv2.circle(frame, (int(cursor_x), int(cursor_y)), 10, (0, 0, 255), -1)

# ── Main loop ────────────────────────────────────────────────
# ── Main loop ────────────────────────────────────────────────
def main():
    global cursor_x, cursor_y, click_processed
    uart_open()
    reset_game()
    
    # Track the switch state before we enter the loop
    last_switch_state = base.switches[0].read()

    try:
        while True:
            # 1. Check for physical switch changes in real-time
            current_switch_state = base.switches[0].read()
            if current_switch_state != last_switch_state:
                last_switch_state = current_switch_state
                update_status_for_turn() # Instantly update the UI text
                
                # If switched to AI mode (0) AND it's O's turn, wake up the AI!
                turn_count = sum(1 for x in board if x != 0)
                is_x_turn = (turn_count % 2 == 0)
                if not current_switch_state and not is_x_turn and not game_over and not ai_thinking:
                    t = threading.Thread(target=ai_move_thread, daemon=True)
                    t.start()

            left_click = False
            right_click = False
            
            # 2. Read Mouse Inputs
            try:
                while True:
                    event_data = os.read(mouse_fd, EVENT_SIZE)
                    if len(event_data) == EVENT_SIZE:
                        _, _, e_type, e_code, e_value = struct.unpack(EVENT_FORMAT, event_data)
                        if e_type == 2: # Movement
                            if e_code == 0: cursor_x += e_value
                            elif e_code == 1: cursor_y += e_value
                        elif e_type == 1: # Clicks
                            if e_code == 272 and e_value == 1: left_click = True
                            elif e_code == 273 and e_value == 1: right_click = True
            except BlockingIOError:
                pass 

            cursor_x = max(0, min(SCREEN_W, cursor_x))
            cursor_y = max(0, min(SCREEN_H, cursor_y))

            # 3. Handle Clicks
            if right_click:
                reset_game()
                time.sleep(0.2)
                
            elif left_click and not click_processed:
                click_processed = True
                if OFFSET_X <= cursor_x <= OFFSET_X + GRID_SIZE and OFFSET_Y <= cursor_y <= OFFSET_Y + GRID_SIZE:
                    col = int((cursor_x - OFFSET_X) // CELL_SIZE)
                    row = int((cursor_y - OFFSET_Y) // CELL_SIZE)
                    idx = row * 3 + col
                    do_human_move(idx)
                    
            if not left_click:
                click_processed = False

            # 4. Render
            frame = hdmi_out.newframe()
            draw_ui(frame)
            hdmi_out.writeframe(frame)
            
            time.sleep(0.015) # ~60fps cap

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        os.close(mouse_fd)
        hdmi_out.stop()
        if ser: ser.close()
        print("Hardware resources released.")

if __name__ == "__main__":
    main()