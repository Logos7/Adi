create_clock -name tmds_clk -period 13.468 -waveform {0 6.734} [get_pins {u_clkdiv/CLKOUT}]
create_clock -name I_clk -period 37.04 -waveform {0 18.52} [get_ports {I_clk}] -add
