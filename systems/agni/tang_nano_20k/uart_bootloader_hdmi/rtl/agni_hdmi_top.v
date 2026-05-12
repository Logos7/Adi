// =============================================================================
// agni_hdmi_top.v
// Agni UART bootloader + HDMI 1bpp framebuffer system for Tang Nano 20K.
//
// The legacy UART frame output remains available. In parallel, Agni framebuffer
// helpers mirror their writes into an external dual-clock RAM scanned by HDMI.
// Button cycles display modes:
//   0 = Agni framebuffer
//   1..7 = built-in HDMI patterns
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
    assign clk = I_clk;

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
        if (I_rst) begin
            rst_counter <= 4'd0;
        end else if (rst_counter != 4'd15) begin
            rst_counter <= rst_counter + 4'd1;
        end
    end

    wire rst = I_rst | (rst_counter != 4'd15);
    wire [127:0] gpio_out;

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
    wire [10:0] fb_cpu_addr;
    wire [31:0] fb_cpu_wdata;
    wire [31:0] fb_cpu_rdata;
    wire [8:0] fb_width;
    wire [7:0] fb_height;

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
        .clk (clk),
        .rst (core_rst),
        .gpio_out (gpio_out),

        .uart_tx_ready (cpu_uart_tx_ready),
        .uart_tx_valid (cpu_uart_tx_valid),
        .uart_tx_data (cpu_uart_tx_data),

        .uart_rx_valid (rx_valid & ~boot_busy & ~boot_cpu_reset),
        .uart_rx_data (rx_data),

        .boot_we (boot_we),
        .boot_addr (boot_addr),
        .boot_data (boot_data),

        .boot_data_we (boot_data_we),
        .boot_data_addr (boot_data_addr),
        .boot_data_word (boot_data_word),

        .fb_ext_we (fb_cpu_we),
        .fb_ext_addr (fb_cpu_addr),
        .fb_ext_wdata (fb_cpu_wdata),
        .fb_ext_rdata (fb_cpu_rdata),
        .fb_ext_width (fb_width),
        .fb_ext_height (fb_height)
    );

    uart_rx #(
        .CLKS_PER_BIT(UART_CLKS_PER_BIT)
    ) uart_rx0 (
        .clk (clk),
        .rst (rst),
        .rx (uart_rx),
        .data (rx_data),
        .valid (rx_valid)
    );

    agni_bootloader #(
        .MAX_WORDS(BOOT_MAX_WORDS),
        .MAX_DATA_WORDS(BOOT_MAX_DATA_WORDS),
        .BYTE_TIMEOUT_CLKS(BOOT_BYTE_TIMEOUT_CLKS),
        .START_IN_BOOTLOADER(BOOT_START_IN_BOOTLOADER)
    ) boot0 (
        .clk (clk),
        .rst (rst),
        .rx_data (rx_data),
        .rx_valid (rx_valid),

        .tx_ready (uart_tx_ready),
        .tx_data (boot_uart_tx_data),
        .tx_valid (boot_uart_tx_valid),

        .boot_we (boot_we),
        .boot_addr (boot_addr),
        .boot_data (boot_data),

        .boot_data_we (boot_data_we),
        .boot_data_addr (boot_data_addr),
        .boot_data_word (boot_data_word),

        .cpu_reset (boot_cpu_reset),
        .busy (boot_busy),
        .waiting (boot_waiting)
    );

    uart_tx #(
        .CLKS_PER_BIT(UART_CLKS_PER_BIT)
    ) uart_tx0 (
        .clk (clk),
        .rst (rst),
        .data (boot_uart_tx_valid ? boot_uart_tx_data : cpu_uart_tx_data),
        .valid (boot_uart_tx_valid ? 1'b1 : ((~boot_busy) & cpu_uart_tx_valid)),
        .ready (uart_tx_ready),
        .tx (uart_tx)
    );

    wire serial_clk;
    wire pll_lock;
    wire pix_clk;
    wire hdmi_rst_n = (~rst) & pll_lock;

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

    reg [31:0] run_cnt;

    always @(posedge I_clk or posedge rst) begin
        if (rst)
            run_cnt <= 32'd0;
        else if (run_cnt >= 32'd27_000_000)
            run_cnt <= 32'd0;
        else
            run_cnt <= run_cnt + 32'd1;
    end

    assign running = (run_cnt < 32'd14_000_000);

    wire [10:0] fb_video_addr;
    wire [31:0] fb_video_data;

    framebuffer_1bpp_dual_clock u_framebuffer (
        .cpu_clk (clk),
        .cpu_we (fb_cpu_we),
        .cpu_addr (fb_cpu_addr),
        .cpu_wdata (fb_cpu_wdata),
        .cpu_rdata (fb_cpu_rdata),

        .video_clk (pix_clk),
        .video_addr (fb_video_addr),
        .video_rdata (fb_video_data)
    );

    wire video_vs;
    wire video_hs;
    wire video_de;
    wire [7:0] video_r;
    wire [7:0] video_g;
    wire [7:0] video_b;

    hdmi_scanout_1bpp_patterns #(
        .FB_WIDTH(320),
        .FB_HEIGHT(200),
        .FB_SCALE(2),
        .FB_SCALE_SHIFT(1),
        .FB_WORDS_PER_ROW(10)
    ) u_scanout (
        .I_pxl_clk(pix_clk),
        .I_rst_n(hdmi_rst_n),
        .I_mode(mode_reg),
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
        .O_data_b(video_b),
        .O_fb_addr(fb_video_addr),
        .I_fb_data(fb_video_data)
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

    assign O_led[0] = ~gpio_out[15];
    assign O_led[1] = ~gpio_out[16];
    assign O_led[2] = ~mode_reg[0];
    assign O_led[3] = ~mode_reg[1];
    assign O_led[4] = boot_waiting ? ~boot_blink_led_on : ~mode_reg[2];
endmodule
