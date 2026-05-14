# Agni HDMI timing constraints - V14
# 27 MHz board oscillator.
create_clock -name I_clk -period 37.037 -waveform {0.000 18.519} [get_ports {I_clk}]

# 74.25 MHz pixel clock produced by CLKDIV from the TMDS PLL clock.
# This exact object was accepted in the previous test where only serial_clk failed.
create_clock -name pix_clk -period 13.468 -waveform {0.000 6.734} [get_pins {u_clkdiv/CLKOUT}]

# CPU/UART and HDMI pixel domains cross through explicit synchronizers and
# dual-clock framebuffer RAM. Treat them as asynchronous for timing analysis.
set_clock_groups -asynchronous -group [get_clocks {I_clk}] -group [get_clocks {pix_clk}]
