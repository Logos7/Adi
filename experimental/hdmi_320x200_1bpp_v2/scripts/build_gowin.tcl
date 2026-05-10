set_device -name GW2AR-18C GW2AR-LV18QN88C8/I7
add_file src/dvi_tx/dvi_tx.v
add_file src/gowin_rpll/TMDS_rPLL.v
add_file src/key_led_ctrl.v
add_file src/pattern_320x200_1bpp.v
add_file src/video_top.v
add_file src/hdmi.cst
add_file src/nano_20k_video.sdc
set_option -top_module video_top
run all
