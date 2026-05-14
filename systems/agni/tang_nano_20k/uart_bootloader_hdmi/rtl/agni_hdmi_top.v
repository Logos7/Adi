// =============================================================================
// agni_hdmi_top.v
// Agni UART bootloader + 480x270 1bpp double-buffered HDMI framebuffer system.
// V19: hidden-bank read gating plus a registered input pipeline and custom Adi DVI/TMDS TX.
// The CPU requests a front bank with @127; HDMI applies it only at a frame boundary.
// Demos poll @125 instead of using a long fixed delay. Only the displayed bank is read by scanout.
//
// 480x270 scales exactly x4 to 1920x1080. The existing 74.25 MHz pixel clock is
// kept, so the generated timing is a 1080p30-style mode. The board clock is
// explicitly routed through a BUFG before feeding CPU logic and the TMDS PLL.
//
// GPIO protocol:
//   @124 = HDMI frame toggle status, read-only
//   @125 = active/front bank status, read-only
//   @126 = draw bank
//   @127 = requested front bank
//
// The scanout module intentionally keeps the legacy hdmi_scanout_1bpp_patterns
// module name so old Gowin project files still compile, but it no longer
// generates local patterns; HDMI is framebuffer-only.
// =============================================================================

module agni_hdmi_top (
    input wire I_clk,
    input wire I_rst,
    input wire I_key,
    input wire uart_rx,
    output wire uart_tx,
    output wire [4:0] O_led,
    output wire running,
    output wire O_tmds_clk_p,
    output wire O_tmds_clk_n,
    output wire [2:0] O_tmds_data_p,
    output wire [2:0] O_tmds_data_n
);
    wire clk;
    BUFG u_input_clk_buf (
        .O(clk),
        .I(I_clk)
    );

    localparam [15:0] UART_CLKS_PER_BIT = 16'd234;
    localparam [15:0] BOOT_MAX_WORDS = 16'd2048;
    localparam [15:0] BOOT_MAX_DATA_WORDS = 16'd2048;
    localparam [31:0] BOOT_BYTE_TIMEOUT_CLKS = 32'd270000000;
    localparam [31:0] BOOT_BLINK_HALF_PERIOD_CLKS = 32'd3375000;
    localparam BOOT_START_IN_BOOTLOADER = 1'b1;

    reg [3:0] rst_counter;
    initial begin
        rst_counter = 4'd0;
    end

    always @(posedge clk or posedge I_rst) begin
        if (I_rst)
            rst_counter <= 4'd0;
        else if (rst_counter != 4'd15)
            rst_counter <= rst_counter + 4'd1;
    end

    wire rst = I_rst | (rst_counter != 4'd15);
    wire [127:0] gpio_out;
    wire hdmi_frame_toggle_cpu;
    wire hdmi_front_bank_cpu;

    wire uart_tx_ready;
    wire cpu_uart_tx_ready;
    wire cpu_uart_tx_valid;
    wire [7:0] cpu_uart_tx_data;
    wire [7:0] rx_data;
    wire rx_valid;
    wire boot_uart_tx_valid;
    wire [7:0] boot_uart_tx_data;
    wire boot_we;
    wire [10:0] boot_addr;
    wire [31:0] boot_data;
    wire boot_data_we;
    wire [10:0] boot_data_addr;
    wire [31:0] boot_data_word;
    wire boot_cpu_reset;
    wire boot_busy;
    wire boot_waiting;
    wire fb_cpu_we;
    wire [16:0] fb_cpu_addr;
    wire [31:0] fb_cpu_wdata;
    wire [8:0] fb_width;
    wire [8:0] fb_height;

    reg [31:0] boot_blink_counter;
    reg boot_blink_led_on;
    initial begin
        boot_blink_counter = 32'd0;
        boot_blink_led_on = 1'b1;
    end

    always @(posedge clk) begin
        if (rst || !boot_waiting) begin
            boot_blink_counter <= 32'd0;
            boot_blink_led_on <= 1'b1;
        end else if (boot_blink_counter >= (BOOT_BLINK_HALF_PERIOD_CLKS - 32'd1)) begin
            boot_blink_counter <= 32'd0;
            boot_blink_led_on <= ~boot_blink_led_on;
        end else begin
            boot_blink_counter <= boot_blink_counter + 32'd1;
        end
    end

    wire core_rst = rst | boot_cpu_reset;
    assign cpu_uart_tx_ready = uart_tx_ready & ~boot_busy;

    agni_core core (
        .clk(clk),
        .rst(core_rst),
        .gpio_out(gpio_out),
        .fb_ext_frame_toggle(hdmi_frame_toggle_cpu),
        .fb_ext_front_bank(hdmi_front_bank_cpu),
        .uart_tx_ready(cpu_uart_tx_ready),
        .uart_tx_valid(cpu_uart_tx_valid),
        .uart_tx_data(cpu_uart_tx_data),
        .uart_rx_valid(rx_valid & ~boot_busy & ~boot_cpu_reset),
        .uart_rx_data(rx_data),
        .boot_we(boot_we),
        .boot_addr(boot_addr),
        .boot_data(boot_data),
        .boot_data_we(boot_data_we),
        .boot_data_addr(boot_data_addr),
        .boot_data_word(boot_data_word),
        .fb_ext_we(fb_cpu_we),
        .fb_ext_addr(fb_cpu_addr),
        .fb_ext_wdata(fb_cpu_wdata),
        .fb_ext_rdata(32'd0),
        .fb_ext_width(fb_width),
        .fb_ext_height(fb_height)
    );

    uart_rx #(.CLKS_PER_BIT(UART_CLKS_PER_BIT)) uart_rx0 (
        .clk(clk), .rst(rst), .rx(uart_rx), .data(rx_data), .valid(rx_valid)
    );

    agni_bootloader #(
        .MAX_WORDS(BOOT_MAX_WORDS),
        .MAX_DATA_WORDS(BOOT_MAX_DATA_WORDS),
        .BYTE_TIMEOUT_CLKS(BOOT_BYTE_TIMEOUT_CLKS),
        .START_IN_BOOTLOADER(BOOT_START_IN_BOOTLOADER)
    ) boot0 (
        .clk(clk), .rst(rst), .rx_data(rx_data), .rx_valid(rx_valid),
        .tx_ready(uart_tx_ready), .tx_data(boot_uart_tx_data), .tx_valid(boot_uart_tx_valid),
        .boot_we(boot_we), .boot_addr(boot_addr), .boot_data(boot_data),
        .boot_data_we(boot_data_we), .boot_data_addr(boot_data_addr), .boot_data_word(boot_data_word),
        .cpu_reset(boot_cpu_reset), .busy(boot_busy), .waiting(boot_waiting)
    );

    uart_tx #(.CLKS_PER_BIT(UART_CLKS_PER_BIT)) uart_tx0 (
        .clk(clk), .rst(rst),
        .data(boot_uart_tx_valid ? boot_uart_tx_data : cpu_uart_tx_data),
        .valid(boot_uart_tx_valid ? 1'b1 : ((~boot_busy) & cpu_uart_tx_valid)),
        .ready(uart_tx_ready), .tx(uart_tx)
    );

    wire serial_clk;
    wire pll_lock;
    wire pix_clk;
    wire hdmi_rst_n = (~rst) & pll_lock;

    TMDS_rPLL u_tmds_rpll (.clkin(clk), .clkout(serial_clk), .lock(pll_lock));
    CLKDIV u_clkdiv (.RESETN(hdmi_rst_n), .HCLKIN(serial_clk), .CLKOUT(pix_clk), .CALIB(1'b1));
    defparam u_clkdiv.DIV_MODE = "5";
    defparam u_clkdiv.GSREN = "false";

    reg [31:0] run_cnt;
    always @(posedge clk or posedge rst) begin
        if (rst)
            run_cnt <= 32'd0;
        else if (run_cnt >= 32'd27_000_000)
            run_cnt <= 32'd0;
        else
            run_cnt <= run_cnt + 32'd1;
    end
    assign running = (run_cnt < 32'd14_000_000);

    wire draw_bank = gpio_out[126];
    wire front_bank_cpu = gpio_out[127];
    wire video_frame_start;

    reg [1:0] front_bank_req_sync;
    reg front_bank_active;
    reg hdmi_frame_toggle_px;
    always @(posedge pix_clk or negedge hdmi_rst_n) begin
        if (!hdmi_rst_n) begin
            front_bank_req_sync <= 2'b00;
            front_bank_active <= 1'b0;
            hdmi_frame_toggle_px <= 1'b0;
        end else begin
            front_bank_req_sync <= {front_bank_req_sync[0], front_bank_cpu};
            if (video_frame_start) begin
                front_bank_active <= front_bank_req_sync[1];
                hdmi_frame_toggle_px <= ~hdmi_frame_toggle_px;
            end
        end
    end
    wire front_bank = front_bank_active;

    reg [2:0] hdmi_frame_toggle_sync;
    reg [2:0] hdmi_front_bank_sync;
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            hdmi_frame_toggle_sync <= 3'b000;
            hdmi_front_bank_sync <= 3'b000;
        end else begin
            hdmi_frame_toggle_sync <= {hdmi_frame_toggle_sync[1:0], hdmi_frame_toggle_px};
            hdmi_front_bank_sync <= {hdmi_front_bank_sync[1:0], front_bank_active};
        end
    end
    assign hdmi_frame_toggle_cpu = hdmi_frame_toggle_sync[2];
    assign hdmi_front_bank_cpu = hdmi_front_bank_sync[2];

    wire [16:0] fb_video_addr;
    wire fb_video_data;
    wire fb0_video_data;
    wire fb1_video_data;

    // Read only the bank that is currently displayed.
    // The hidden bank may be cleared/redrawn aggressively by the CPU. Keeping its
    // video-side address parked at zero removes unnecessary BRAM/mux activity and
    // avoids sampling undefined dual-clock RAM output from a bank that is being
    // written at the same time.
    wire [16:0] fb0_video_addr = front_bank ? 17'd0 : fb_video_addr;
    wire [16:0] fb1_video_addr = front_bank ? fb_video_addr : 17'd0;

    assign fb_video_data = front_bank ? fb1_video_data : fb0_video_data;

    framebuffer_1bpp_dual_clock #(.ADDR_BITS(17), .PIXELS(131072)) u_framebuffer0 (
        .cpu_clk(clk), .cpu_we(fb_cpu_we & ~draw_bank), .cpu_addr(fb_cpu_addr), .cpu_wdata(fb_cpu_wdata[0]),
        .video_clk(pix_clk), .video_addr(fb0_video_addr), .video_rdata(fb0_video_data)
    );

    framebuffer_1bpp_dual_clock #(.ADDR_BITS(17), .PIXELS(131072)) u_framebuffer1 (
        .cpu_clk(clk), .cpu_we(fb_cpu_we & draw_bank), .cpu_addr(fb_cpu_addr), .cpu_wdata(fb_cpu_wdata[0]),
        .video_clk(pix_clk), .video_addr(fb1_video_addr), .video_rdata(fb1_video_data)
    );

    wire video_vs;
    wire video_hs;
    wire video_de;
    wire [7:0] video_r;
    wire [7:0] video_g;
    wire [7:0] video_b;

    hdmi_scanout_1bpp_patterns #(
        .FB_WIDTH(480), .FB_HEIGHT(270), .FB_SCALE(4), .FB_SCALE_SHIFT(2), .FB_ADDR_BITS(17)
    ) u_scanout (
        .I_pxl_clk(pix_clk), .I_rst_n(hdmi_rst_n), .I_mode(3'd0),
        .I_h_total(12'd2200), .I_h_sync(12'd44), .I_h_bporch(12'd148), .I_h_res(12'd1920),
        .I_v_total(12'd1125), .I_v_sync(12'd5), .I_v_bporch(12'd36), .I_v_res(12'd1080),
        .I_hs_pol(1'b1), .I_vs_pol(1'b1),
        .O_de(video_de), .O_hs(video_hs), .O_vs(video_vs),
        .O_data_r(video_r), .O_data_g(video_g), .O_data_b(video_b),
        .O_fb_addr(fb_video_addr), .O_frame_start(video_frame_start), .I_fb_data(fb_video_data)
    );

    // Register the full RGB/control bundle right before the custom Adi DVI/TMDS transmitter.
    // This cuts the scanout/framebuffer combinational path at the DVI boundary and
    // gives P&R a much cleaner 74.25 MHz timing target. It does not change the
    // visible geometry; HS/VS/DE/RGB stay aligned because the whole bundle is
    // delayed by exactly one pixel clock.
    reg dvi_vs;
    reg dvi_hs;
    reg dvi_de;
    reg [7:0] dvi_r;
    reg [7:0] dvi_g;
    reg [7:0] dvi_b;

    always @(posedge pix_clk or negedge hdmi_rst_n) begin
        if (!hdmi_rst_n) begin
            dvi_vs <= 1'b0;
            dvi_hs <= 1'b0;
            dvi_de <= 1'b0;
            dvi_r <= 8'd0;
            dvi_g <= 8'd0;
            dvi_b <= 8'd0;
        end else begin
            dvi_vs <= video_vs;
            dvi_hs <= video_hs;
            dvi_de <= video_de;
            dvi_r <= video_r;
            dvi_g <= video_g;
            dvi_b <= video_b;
        end
    end

    DVI_TX_Top u_dvi_tx (
        .I_rst_n(hdmi_rst_n), .I_serial_clk(serial_clk), .I_rgb_clk(pix_clk),
        .I_rgb_vs(dvi_vs), .I_rgb_hs(dvi_hs), .I_rgb_de(dvi_de),
        .I_rgb_r(dvi_r), .I_rgb_g(dvi_g), .I_rgb_b(dvi_b),
        .O_tmds_clk_p(O_tmds_clk_p), .O_tmds_clk_n(O_tmds_clk_n),
        .O_tmds_data_p(O_tmds_data_p), .O_tmds_data_n(O_tmds_data_n)
    );

    assign O_led[0] = ~gpio_out[15];
    assign O_led[1] = ~gpio_out[16];
    assign O_led[2] = ~draw_bank;
    assign O_led[3] = ~front_bank_active;
    assign O_led[4] = boot_waiting ? ~boot_blink_led_on : ~(draw_bank ^ front_bank_cpu ^ I_key);
endmodule
