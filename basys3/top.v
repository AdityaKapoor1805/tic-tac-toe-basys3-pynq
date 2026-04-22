
`timescale 1ns / 1ps

module top (
    input  wire        clk,
    input  wire        uart_rx,
    output wire        uart_tx
);

localparam CLK_FREQ  = 100_000_000;
localparam BAUD_RATE = 9600;

wire       rx_valid;
wire [7:0] rx_data;
wire       tx_busy;
wire       tx_start;
wire [7:0] tx_data;
wire [17:0] board_flat;   
wire [1:0]  winner;
wire        game_over;

// UART Receiver
uart_rx #(.CLK_FREQ(CLK_FREQ), .BAUD_RATE(BAUD_RATE)) u_rx (
    .clk(clk), .rx(uart_rx), .data_out(rx_data), .valid(rx_valid)
);

// UART Transmitter
uart_tx #(.CLK_FREQ(CLK_FREQ), .BAUD_RATE(BAUD_RATE)) u_tx (
    .clk(clk), .data_in(tx_data), .start(tx_start),
    .tx(uart_tx), .busy(tx_busy)
);

// Game Controller
game_ctrl u_game (
    .clk(clk),
    .rx_valid(rx_valid), .rx_data(rx_data),
    .tx_busy(tx_busy),   .tx_start(tx_start), .tx_data(tx_data),
    .board_out(board_flat),
    .winner(winner), .game_over(game_over)
);

endmodule