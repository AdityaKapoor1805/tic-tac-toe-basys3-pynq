
module game_ctrl (
    input  wire        clk,
    input  wire        rx_valid,
    input  wire [7:0]  rx_data,

    input  wire        tx_busy,
    output reg         tx_start,
    output reg  [7:0]  tx_data,

    output wire [17:0] board_out,
    output reg  [1:0]  winner,
    output reg         game_over
);

reg [1:0] board [0:8];
integer   i;
reg [3:0] cell_idx;

assign board_out[ 1: 0] = board[0];
assign board_out[ 3: 2] = board[1];
assign board_out[ 5: 4] = board[2];
assign board_out[ 7: 6] = board[3];
assign board_out[ 9: 8] = board[4];
assign board_out[11:10] = board[5];
assign board_out[13:12] = board[6];
assign board_out[15:14] = board[7];
assign board_out[17:16] = board[8];

reg x_turn;

// Win check 
reg [1:0] w;
always @(*) begin
    w = 2'd0;
    if (board[0]!=0 && board[0]==board[1] && board[1]==board[2]) w=board[0];
    if (board[3]!=0 && board[3]==board[4] && board[4]==board[5]) w=board[3];
    if (board[6]!=0 && board[6]==board[7] && board[7]==board[8]) w=board[6];
    if (board[0]!=0 && board[0]==board[3] && board[3]==board[6]) w=board[0];
    if (board[1]!=0 && board[1]==board[4] && board[4]==board[7]) w=board[1];
    if (board[2]!=0 && board[2]==board[5] && board[5]==board[8]) w=board[2];
    if (board[0]!=0 && board[0]==board[4] && board[4]==board[8]) w=board[0];
    if (board[2]!=0 && board[2]==board[4] && board[4]==board[6]) w=board[2];
end

reg draw_comb;
always @(*) begin
    draw_comb = (w == 0) ? 1'b1 : 1'b0;
    for (i = 0; i < 9; i = i + 1)
        if (board[i] == 0) draw_comb = 1'b0;
end

function [7:0] cell_char;
    input [1:0] v;
    case (v)
        2'd1:    cell_char = 8'h58; // 'X'
        2'd2:    cell_char = 8'h4F; // 'O'
        default: cell_char = 8'h2E; // '.'
    endcase
endfunction

function [7:0] status_char;
    input [1:0] wnr;
    input       drw;
    if      (wnr == 2'd1) status_char = 8'h57; // 'W'
    else if (wnr == 2'd2) status_char = 8'h4C; // 'L'
    else if (drw)         status_char = 8'h44; // 'D'
    else                  status_char = 8'h47; // 'G'
endfunction

//  TX FSM 
localparam TX_IDLE = 2'd0;
localparam TX_SEND = 2'd1;
localparam TX_WAIT = 2'd2;

reg [1:0]  tx_state = TX_IDLE;
reg [3:0]  tx_idx   = 0;
reg [87:0] tx_buf;
reg        send_trigger = 0;

// Game logic 
reg [1:0] update_state = 0;

always @(posedge clk) begin
    send_trigger <= 1'b0;

    case (update_state)
        0: begin // Stage 1: Receive move and update board registers
            if (rx_valid) begin
                if (rx_data == 8'h52) begin             // 'R' reset
                    for (i = 0; i < 9; i = i + 1)
                        board[i] <= 2'd0;
                    x_turn       <= 1'b1;
                    update_state <= 1;                  // Move to wait cycle
                end else if (rx_data >= 8'h31 && rx_data <= 8'h39 && !game_over) begin
                    cell_idx = rx_data - 8'h31;         // 0-based, blocking assign OK
                    if (board[cell_idx] == 2'd0) begin
                        board[cell_idx] <= x_turn ? 2'd1 : 2'd2;
                        x_turn          <= ~x_turn;
                        update_state    <= 1;           // Move to wait cycle
                    end
                end
            end
        end
        
        1: begin // Stage 2: Allow combinational logic to settle, then send
            // Because 1 clock cycle has passed, board[] now holds the new move.
            // w and draw_comb now accurately reflect the updated board.
            winner       <= w;
            game_over    <= (w != 0) || draw_comb;
            send_trigger <= 1'b1; // Trigger the TX sequencer with the fresh data
            update_state <= 0;    // Go back to idle
        end
    endcase
end

// ---- TX sequencer ----
always @(posedge clk) begin
    tx_start <= 1'b0;
    case (tx_state)
        TX_IDLE: begin
            if (send_trigger) begin
                tx_buf <= {
                    cell_char(board[0]), cell_char(board[1]), cell_char(board[2]),
                    cell_char(board[3]), cell_char(board[4]), cell_char(board[5]),
                    cell_char(board[6]), cell_char(board[7]), cell_char(board[8]),
                    status_char(w, draw_comb),
                    8'h0A
                };
                tx_idx   <= 0;
                tx_state <= TX_SEND;
            end
        end
        TX_SEND: begin
            if (!tx_busy) begin
                tx_data  <= tx_buf[87:80];
                tx_buf   <= {tx_buf[79:0], 8'h00};
                tx_start <= 1'b1;
                tx_state <= TX_WAIT;
            end
        end
        TX_WAIT: begin
            if (!tx_busy && !tx_start) begin
                if (tx_idx == 10)
                    tx_state <= TX_IDLE;
                else begin
                    tx_idx   <= tx_idx + 1;
                    tx_state <= TX_SEND;
                end
            end
        end
    endcase
end

endmodule