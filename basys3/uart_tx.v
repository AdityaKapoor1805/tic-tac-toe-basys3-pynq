// =============================================================
//  UART Transmitter
// =============================================================
module uart_tx #(
    parameter CLK_FREQ  = 100_000_000,
    parameter BAUD_RATE = 9600
)(
    input  wire       clk,
    input  wire [7:0] data_in,
    input  wire       start,
    output reg        tx,
    output reg        busy
);

localparam CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;

localparam S_IDLE  = 2'd0;
localparam S_START = 2'd1;
localparam S_DATA  = 2'd2;
localparam S_STOP  = 2'd3;

reg [1:0]  state     = S_IDLE;
reg [15:0] clk_cnt   = 0;
reg [2:0]  bit_idx   = 0;
reg [7:0]  shift_reg = 0;

initial tx = 1'b1;    // UART idle-high

always @(posedge clk) begin
    case (state)
        S_IDLE: begin
            tx   <= 1'b1;
            busy <= 1'b0;
            if (start) begin
                state     <= S_START;
                shift_reg <= data_in;
                clk_cnt   <= 0;
                busy      <= 1'b1;
            end
        end

        S_START: begin
            tx <= 1'b0;
            if (clk_cnt == CLKS_PER_BIT - 1) begin
                state   <= S_DATA;
                clk_cnt <= 0;
                bit_idx <= 0;
            end else begin
                clk_cnt <= clk_cnt + 1;
            end
        end

        S_DATA: begin
            tx <= shift_reg[bit_idx];
            if (clk_cnt == CLKS_PER_BIT - 1) begin
                clk_cnt <= 0;
                if (bit_idx == 7) begin
                    state <= S_STOP;
                end else begin
                    bit_idx <= bit_idx + 1;
                end
            end else begin
                clk_cnt <= clk_cnt + 1;
            end
        end

        S_STOP: begin
            tx <= 1'b1;
            if (clk_cnt == CLKS_PER_BIT - 1) begin
                state   <= S_IDLE;
                clk_cnt <= 0;
                busy    <= 1'b0;
            end else begin
                clk_cnt <= clk_cnt + 1;
            end
        end
    endcase
end

endmodule
