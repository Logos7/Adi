module top(
    input wire clk,
    input wire rst,
    input wire ser_rx,
    output wire ser_tx,
    output wire lcd_clk,
    output wire lcd_data,
    output wire lcd_cs,
    output wire lcd_dc,
    output wire lcd_resetn
);
    assign ser_tx = 1'b1;

    wire clear_scene;
    wire sphere_we;
    wire [2:0] sphere_slot;
    wire sphere_active;
    wire signed [15:0] sphere_cx;
    wire signed [15:0] sphere_cy;
    wire signed [15:0] sphere_cz;
    wire [15:0] sphere_r;
    wire [15:0] sphere_color;
    wire render_pulse;

    wire pixel_req;
    wire pixel_valid;
    wire [15:0] pixel_rgb565;

    adi_uart_scene_loader #(
        .CLK_HZ(50000000),
        .BAUD(115200)
    ) scene_loader0 (
        .clk(clk),
        .rst(rst),
        .uart_rx(ser_rx),
        .clear_scene(clear_scene),
        .sphere_we(sphere_we),
        .sphere_slot(sphere_slot),
        .sphere_active(sphere_active),
        .sphere_cx(sphere_cx),
        .sphere_cy(sphere_cy),
        .sphere_cz(sphere_cz),
        .sphere_r(sphere_r),
        .sphere_color(sphere_color),
        .render_pulse(render_pulse)
    );

    adi_sphere_renderer #(
        .WIDTH(160),
        .HEIGHT(80),
        .MAX_SPHERES(8),
        .PIXEL_SCALE_Q8(8)
    ) renderer0 (
        .clk(clk),
        .rst(rst),
        .pixel_req(pixel_req),
        .pixel_valid(pixel_valid),
        .pixel_rgb565(pixel_rgb565),
        .render_restart(render_pulse),
        .clear_scene(clear_scene),
        .sphere_we(sphere_we),
        .sphere_slot(sphere_slot),
        .sphere_active(sphere_active),
        .sphere_cx(sphere_cx),
        .sphere_cy(sphere_cy),
        .sphere_cz(sphere_cz),
        .sphere_r(sphere_r),
        .sphere_color(sphere_color)
    );

    adi_lcd_st7735_stream #(
        .WIDTH(160),
        .HEIGHT(80),
        .X_OFFSET(0),
        .Y_OFFSET(24),
        .MADCTL(8'h60),
        .SPI_CLK_DIV(2),
        .CLK_HZ(50000000)
    ) lcd0 (
        .clk(clk),
        .rst(rst),
        .lcd_sck(lcd_clk),
        .lcd_mosi(lcd_data),
        .lcd_cs(lcd_cs),
        .lcd_dc(lcd_dc),
        .lcd_rst(lcd_resetn),
        .pixel_req(pixel_req),
        .pixel_valid(pixel_valid),
        .pixel_rgb565(pixel_rgb565)
    );
endmodule
