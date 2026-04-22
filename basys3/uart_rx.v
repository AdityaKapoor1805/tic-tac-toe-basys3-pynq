// =============================================================
//  UART Receiver 
// =============================================================
module uart_rx #(
    parameter CLK_FREQ  = 100_000_000,
    parameter BAUD_RATE = 9600
)(
    input  wire       clk,
    input  wire       rx,
    output reg  [7:0] data_out,
    output reg        valid
);

localparam CLKS_PER_BIT = CLK_FREQ / BAUD_RATE;


reg rx_d1, rx_d2;
always @(posedge clk) begin
    rx_d1 <= rx;
    rx_d2 <= rx_d1;
end

localparam S_IDLE  = 2'd0;
localparam S_START = 2'd1;
localparam S_DATA  = 2'd2;
localparam S_STOP  = 2'd3;

reg [1:0]  state     = S_IDLE;
reg [15:0] clk_cnt   = 0;
reg [2:0]  bit_idx   = 0;
reg [7:0]  shift_reg = 0;

always @(posedge clk) begin
    valid <= 1'b0;

    case (state)
        S_IDLE: begin
            if (rx_d2 == 1'b0) begin          // falling edge = start bit
                state   <= S_START;
                clk_cnt <= 0;
            end
        end

        S_START: begin
            if (clk_cnt == (CLKS_PER_BIT/2 - 1)) begin
                if (rx_d2 == 1'b0) begin      // still low: valid start bit
                    state   <= S_DATA;
                    clk_cnt <= 0;
                    bit_idx <= 0;
                end else begin
                    state <= S_IDLE;          // glitch – abort
                end
            end else begin
                clk_cnt <= clk_cnt + 1;
            end
        end

        S_DATA: begin
            if (clk_cnt == CLKS_PER_BIT - 1) begin
                clk_cnt            <= 0;
                shift_reg[bit_idx] <= rx_d2;
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
            if (clk_cnt == CLKS_PER_BIT - 1) begin
                state    <= S_IDLE;
                clk_cnt  <= 0;
                if (rx_d2 == 1'b1) begin     // stop bit OK
                    data_out <= shift_reg;
                    valid    <= 1'b1;
                end
            end else begin
                clk_cnt <= clk_cnt + 1;
            end
        end
    endcase
end

endmodule
