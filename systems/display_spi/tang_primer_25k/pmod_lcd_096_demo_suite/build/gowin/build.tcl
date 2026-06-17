set script_dir [file dirname [info script]]
cd $script_dir
open_project Tang25K.gprj
set_option -top_module display_spi_tang_primer_25k_pmod_lcd_096_demo_suite_top
set_option -output_base_name Tang25K
set_option -use_sspi_as_gpio 1
set_option -use_cpu_as_gpio 1
set_option -use_i2c_as_gpio 1
set_option -bit_format bin
set_option -bit_crc_check 1
set_option -bit_security 1
set_option -power_on_reset 1
set_option -unused_pin default
run all
