set project_name spheres_uart_demo
set root [file normalize [file join [pwd] .. ..]]
set src [file join $root src]

create_project -name $project_name -dir $project_name -pn GW5A-LV25MG121NC1/I0
set_option -top_module top
set_option -verilog_std sysv2017

add_file [file join $src top.v]
add_file [file join $src adi_uart_rx.v]
add_file [file join $src adi_uart_scene_loader.v]
add_file [file join $src adi_spi_byte_tx.v]
add_file [file join $src adi_isqrt32.v]
add_file [file join $src adi_sphere_renderer.v]
add_file [file join $src adi_lcd_st7735_stream.v]

if {[file exists [file join $root constraints pins.cst]]} {
    add_file [file join $root constraints pins.cst]
}

save_project
close_project
puts "Adi sphere raytracer 25K project created."
