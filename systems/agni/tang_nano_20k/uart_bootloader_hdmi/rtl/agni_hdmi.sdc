// Tang Nano 20K Agni + HDMI timing constraints

// 27 MHz board clock
create_clock -name sys_clk -period 37.037 -waveform {0.000 18.519} [get_ports {I_clk}] -add

// HDMI TMDS serial clock: 27 MHz * 55 / 4 = 371.25 MHz
create_generated_clock -name tmds_serial_clk -source [get_ports {I_clk}] -master_clock sys_clk -multiply_by 55 -divide_by 4 [get_nets {serial_clk}]

// HDMI pixel clock: 371.25 MHz / 5 = 74.25 MHz
create_generated_clock -name pix_clk -source [get_nets {serial_clk}] -master_clock tmds_serial_clk -divide_by 5 [get_nets {pix_clk}]

// CPU/UART and HDMI scanout cross only through synchronizers and dual-clock framebuffer RAM.
// Keep pix_clk and tmds_serial_clk related; OSER10 needs that relationship.
set_clock_groups -asynchronous -group [get_clocks {sys_clk}] -group [get_clocks {pix_clk tmds_serial_clk}]
