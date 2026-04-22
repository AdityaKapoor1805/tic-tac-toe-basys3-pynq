## =============================================================
##  Basys 3 Constraints - Tic-Tac-Toe (Headless)
##  Targeting Artix-7 xc7a35tcpg236-1
## =============================================================

## Clock (100 MHz)
set_property PACKAGE_PIN W5      [get_ports clk]
set_property IOSTANDARD  LVCMOS33 [get_ports clk]
create_clock -add -name sys_clk_pin -period 10.00 -waveform {0 5} [get_ports clk]

## UART - Pmod JA pins (use JA1 = TX, JA2 = RX)
##  JA1 = JA[0] = FPGA TX  → FT232 RX
##  JA2 = JA[1] = FPGA RX  ← FT232 TX
set_property PACKAGE_PIN J1  [get_ports uart_tx]
set_property IOSTANDARD LVCMOS33 [get_ports uart_tx]

set_property PACKAGE_PIN L2  [get_ports uart_rx]
set_property IOSTANDARD LVCMOS33 [get_ports uart_rx]