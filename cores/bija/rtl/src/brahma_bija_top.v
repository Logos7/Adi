// =============================================================================
// brahma_bija_top.v
// Top-level dla procesora Brahma-Bija na Tang Nano 20K.
// Wersja Verilog-2001, bez wymagania trybu SystemVerilog w Gowin.
// =============================================================================

module brahma_bija_top (
    input wire clk_27mhz,
    output wire [5:0] led,
    input wire uart_rx,
    output wire uart_tx
);
    wire clk;
    assign clk = clk_27mhz;

    // Parametry najczęściej zmieniane przy bootloaderze/UART.
    // Dla 27 MHz i 115200 baud: 27000000 / 115200 ~= 234.
    localparam [15:0] UART_CLKS_PER_BIT = 16'd234;
    localparam [15:0] BOOT_MAX_WORDS = 16'd2048;
    localparam [15:0] BOOT_MAX_DATA_WORDS = 16'd2048;
    localparam [31:0] BOOT_BYTE_TIMEOUT_CLKS = 32'd270000000;

    // LED0 podczas oczekiwania bootloadera:
    // 4 pełne mrugnięcia/s = 8 przełączeń/s, więc pół-okres = 27 MHz / 8.
    localparam [31:0] BOOT_BLINK_HALF_PERIOD_CLKS = 32'd3375000;

    // 1 = po konfiguracji FPGA CPU czeka w bootloaderze na pierwszy upload.
    // Po udanym uploadzie program startuje. Kolejne uploady są łapane przez
    // sprzętowe podsłuchiwanie magic "ADI!" na UART RX.
    localparam BOOT_START_IN_BOOTLOADER = 1'b1;

    reg [3:0] rst_counter;
    initial begin
        rst_counter = 4'd0;
    end

    always @(posedge clk) begin
        if (rst_counter != 4'd15) begin
            rst_counter <= rst_counter + 4'd1;
        end
    end

    wire rst;
    assign rst = (rst_counter != 4'd15);

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

    wire core_rst;
    assign core_rst = rst | boot_cpu_reset;

    assign cpu_uart_tx_ready = uart_tx_ready & ~boot_busy;

    brahma_bija_core core (
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
        .boot_data_word (boot_data_word)
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

    brahma_bija_bootloader #(
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
    ) uart0 (
        .clk (clk),
        .rst (rst),
        .data (boot_uart_tx_valid ? boot_uart_tx_data : cpu_uart_tx_data),
        .valid (boot_uart_tx_valid ? 1'b1 : ((~boot_busy) & cpu_uart_tx_valid)),
        .ready (uart_tx_ready),
        .tx (uart_tx)
    );

    // LED-y aktywne niskim stanem.
    // Używamy fizycznych numerów pinów FPGA: LED0=pin15, LED1=pin16, ..., LED5=pin20.
    // LED0 podczas oczekiwania bootloadera mruga 4x/s.
    // Gdy bootloader jest bezczynny, LED0 wraca pod kontrolę programu przez @led0.
    assign led[0] = boot_waiting ? ~boot_blink_led_on : ~gpio_out[15];
    assign led[1] = ~gpio_out[16];
    assign led[2] = ~gpio_out[17];
    assign led[3] = ~gpio_out[18];
    assign led[4] = ~gpio_out[19];
    assign led[5] = ~gpio_out[20];
endmodule
