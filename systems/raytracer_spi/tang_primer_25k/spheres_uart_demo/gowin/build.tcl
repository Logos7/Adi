set script_dir [file dirname [file normalize [info script]]]
set root [file normalize [file join $script_dir ..]]
set project_file [file join $root spheres_uart_demo.gprj]

puts "Opening Gowin project: $project_file"
open_project $project_file

set_option -synthesis_tool gowinsynthesis
set_option -top_module top
set_option -output_base_name spheres_uart_demo

set_option -use_cpu_as_gpio 1
set_option -use_sspi_as_gpio 1
set_option -use_mspi_as_gpio 1
set_option -use_ready_as_gpio 1
set_option -use_done_as_gpio 1
set_option -use_i2c_as_gpio 1
set_option -use_jtag_as_gpio 1
set_option -bit_format bin
set_option -bit_crc_check 1
set_option -bg_programming off

foreach file {
    src/top.v
    src/adi_uart_rx.v
    src/adi_uart_scene_loader.v
    src/adi_spi_byte_tx.v
    src/adi_isqrt32.v
    src/adi_sphere_renderer.v
    src/adi_lcd_st7735_stream.v
    constraints/pins.cst
    constraints/timing.sdc
} {
    set full [file join $root $file]
    catch {remove_file $full}
    add_file $full
}

save_project
puts "Dual-purpose pins enabled before PnR: CPU/SSPI/MSPI/READY/DONE/I2C/JTAG as GPIO."
run all
save_project
catch {close_project}
puts "Adi sphere raytracer 25K build finished."
