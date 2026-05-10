module video_top (
    input I_clk,
    input I_rst,
    input I_key,
    output [4:0] O_led,
    output running,
    output O_tmds_clk_p,
    output O_tmds_clk_n,
    output [2:0] O_tmds_data_p,
    output [2:0] O_tmds_data_n
);

wire I_rst_n = ~I_rst;

reg [31:0] run_cnt;

always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n)
        run_cnt <= 32'd0;
    else if (run_cnt >= 32'd27_000_000)
        run_cnt <= 32'd0;
    else
        run_cnt <= run_cnt + 32'd1;
end

assign running = (run_cnt < 32'd14_000_000);

wire serial_clk;
wire pll_lock;
wire pix_clk;
wire hdmi_rst_n = I_rst_n & pll_lock;

TMDS_rPLL u_tmds_rpll (
    .clkin(I_clk),
    .clkout(serial_clk),
    .lock(pll_lock)
);

CLKDIV u_clkdiv (
    .RESETN(hdmi_rst_n),
    .HCLKIN(serial_clk),
    .CLKOUT(pix_clk),
    .CALIB(1'b1)
);

defparam u_clkdiv.DIV_MODE = "5";
defparam u_clkdiv.GSREN = "false";

reg [1:0] key_sync;
reg [2:0] mode_reg;

always @(posedge pix_clk or negedge hdmi_rst_n) begin
    if (!hdmi_rst_n)
        key_sync <= 2'b00;
    else
        key_sync <= {key_sync[0], I_key};
end

wire key_pressed = key_sync[0] & ~key_sync[1];

always @(posedge pix_clk or negedge hdmi_rst_n) begin
    if (!hdmi_rst_n)
        mode_reg <= 3'd0;
    else if (key_pressed)
        mode_reg <= mode_reg + 3'd1;
end

wire video_vs;
wire video_hs;
wire video_de;
wire [7:0] video_r;
wire [7:0] video_g;
wire [7:0] video_b;

pattern_320x200_1bpp u_pattern (
    .I_pxl_clk(pix_clk),
    .I_rst_n(hdmi_rst_n),
    .I_mode(mode_reg),
    .I_single_r(8'd0),
    .I_single_g(8'd255),
    .I_single_b(8'd0),
    .I_h_total(12'd1650),
    .I_h_sync(12'd40),
    .I_h_bporch(12'd220),
    .I_h_res(12'd1280),
    .I_v_total(12'd750),
    .I_v_sync(12'd5),
    .I_v_bporch(12'd20),
    .I_v_res(12'd720),
    .I_hs_pol(1'b1),
    .I_vs_pol(1'b1),
    .O_de(video_de),
    .O_hs(video_hs),
    .O_vs(video_vs),
    .O_data_r(video_r),
    .O_data_g(video_g),
    .O_data_b(video_b)
);

DVI_TX_Top u_dvi_tx (
    .I_rst_n(hdmi_rst_n),
    .I_serial_clk(serial_clk),
    .I_rgb_clk(pix_clk),
    .I_rgb_vs(video_vs),
    .I_rgb_hs(video_hs),
    .I_rgb_de(video_de),
    .I_rgb_r(video_r),
    .I_rgb_g(video_g),
    .I_rgb_b(video_b),
    .O_tmds_clk_p(O_tmds_clk_p),
    .O_tmds_clk_n(O_tmds_clk_n),
    .O_tmds_data_p(O_tmds_data_p),
    .O_tmds_data_n(O_tmds_data_n)
);

key_led_ctrl u_key_led_ctrl (
    .I_rst_n(hdmi_rst_n),
    .I_clk(pix_clk),
    .I_key(I_key),
    .O_led(O_led)
);

endmodule
