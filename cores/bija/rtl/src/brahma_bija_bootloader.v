// =============================================================================
// brahma_bija_bootloader.v
// UART bootloader for Brahma-Bija.
//
// v1.5:
//   - uploads separate instruction memory and data_mem blob
//   - code stays code; LUTs/assets are sent as data words
//   - timeout/ERR keeps CPU held in reset
//   - magic ADI! can interrupt a running program and re-enter bootloader
//
// Protocol after ADI_BOOT_READY\n:
//   version      u8  = 2
//   code_count   u16 little-endian
//   data_count   u16 little-endian, flat data_mem[0..data_count-1]
//   checksum     u32 little-endian, sum of all code/data payload bytes
//   code words   code_count * u32 little-endian
//   data words   data_count * u32 little-endian
//
// Verilog-2001 / Gowin-safe.
// =============================================================================

module brahma_bija_bootloader #(
    parameter [15:0] MAX_WORDS = 16'd1024,
    parameter [15:0] MAX_DATA_WORDS = 16'd512,
    parameter [31:0] BYTE_TIMEOUT_CLKS = 32'd270000000,
    parameter        START_IN_BOOTLOADER = 1'b1
)(
    input  wire        clk,
    input  wire        rst,

    input  wire [7:0]  rx_data,
    input  wire        rx_valid,

    input  wire        tx_ready,
    output reg  [7:0]  tx_data,
    output reg         tx_valid,

    output reg         boot_we,
    output reg  [9:0]  boot_addr,
    output reg  [31:0] boot_data,

    output reg         boot_data_we,
    output reg  [8:0]  boot_data_addr,
    output reg  [31:0] boot_data_word,

    output wire        cpu_reset,
    output wire        busy,
    output wire        waiting
);

    localparam [4:0] S_IDLE        = 5'd0;
    localparam [4:0] S_READY_ACK   = 5'd1;
    localparam [4:0] S_VERSION     = 5'd2;
    localparam [4:0] S_CODE_COUNT0 = 5'd3;
    localparam [4:0] S_CODE_COUNT1 = 5'd4;
    localparam [4:0] S_DATA_COUNT0 = 5'd5;
    localparam [4:0] S_DATA_COUNT1 = 5'd6;
    localparam [4:0] S_CSUM0       = 5'd7;
    localparam [4:0] S_CSUM1       = 5'd8;
    localparam [4:0] S_CSUM2       = 5'd9;
    localparam [4:0] S_CSUM3       = 5'd10;
    localparam [4:0] S_CODE        = 5'd11;
    localparam [4:0] S_DATA        = 5'd12;
    localparam [4:0] S_ACK         = 5'd13;
    localparam [4:0] S_RESTART     = 5'd14;

    localparam [7:0] VERSION_V15 = 8'd2;

    reg [4:0]  state;
    reg [1:0]  magic_idx;
    reg [15:0] code_count;
    reg [15:0] data_count;
    reg [15:0] word_index;
    reg [1:0]  byte_index;
    reg [31:0] expected_checksum;
    reg [31:0] checksum_acc;
    reg [31:0] word_buf;
    reg        hold_reset;
    reg        ack_success;
    reg [3:0]  ack_index;
    reg        ack_advance_pending;
    reg [4:0]  restart_counter;
    reg [31:0] byte_timeout_counter;

    assign cpu_reset = hold_reset;
    assign busy = (state != S_IDLE) | hold_reset;
    assign waiting = hold_reset & (state != S_RESTART);

    task enter_running;
        begin
            state                <= S_IDLE;
            magic_idx            <= 2'd0;
            hold_reset           <= 1'b0;
            ack_index            <= 4'd0;
            ack_advance_pending  <= 1'b0;
            byte_timeout_counter <= 32'd0;
        end
    endtask

    task enter_waiting;
        begin
            state                <= S_IDLE;
            magic_idx            <= 2'd0;
            hold_reset           <= 1'b1;
            ack_index            <= 4'd0;
            ack_advance_pending  <= 1'b0;
            byte_timeout_counter <= 32'd0;
        end
    endtask

    task touch_timeout;
        begin
            byte_timeout_counter <= 32'd0;
        end
    endtask

    task tick_or_wait;
        begin
            if (byte_timeout_counter >= BYTE_TIMEOUT_CLKS) begin
                enter_waiting;
            end else begin
                byte_timeout_counter <= byte_timeout_counter + 32'd1;
            end
        end
    endtask

    task prepare_error_ack;
        begin
            ack_success <= 1'b0;
            ack_index <= 4'd0;
            ack_advance_pending <= 1'b0;
            state <= S_ACK;
            hold_reset <= 1'b1;
        end
    endtask

    always @(posedge clk) begin
        if (rst) begin
            state                <= S_IDLE;
            magic_idx            <= 2'd0;
            code_count           <= 16'd0;
            data_count           <= 16'd0;
            word_index           <= 16'd0;
            byte_index           <= 2'd0;
            expected_checksum    <= 32'd0;
            checksum_acc         <= 32'd0;
            word_buf             <= 32'd0;
            hold_reset           <= START_IN_BOOTLOADER;
            ack_success          <= 1'b0;
            ack_index            <= 4'd0;
            ack_advance_pending  <= 1'b0;
            restart_counter      <= 5'd0;
            byte_timeout_counter <= 32'd0;
            boot_we              <= 1'b0;
            boot_addr            <= 10'd0;
            boot_data            <= 32'd0;
            boot_data_we         <= 1'b0;
            boot_data_addr       <= 9'd0;
            boot_data_word       <= 32'd0;
            tx_data              <= 8'd0;
            tx_valid             <= 1'b0;
        end else begin
            boot_we      <= 1'b0;
            boot_data_we <= 1'b0;
            tx_valid     <= 1'b0;

            case (state)
                S_IDLE: begin
                    byte_timeout_counter <= 32'd0;
                    ack_advance_pending  <= 1'b0;
                    if (rx_valid) begin
                        case (magic_idx)
                            2'd0: begin
                                if (rx_data == 8'h41) magic_idx <= 2'd1;
                                else magic_idx <= 2'd0;
                            end
                            2'd1: begin
                                if (rx_data == 8'h44) magic_idx <= 2'd2;
                                else if (rx_data == 8'h41) magic_idx <= 2'd1;
                                else magic_idx <= 2'd0;
                            end
                            2'd2: begin
                                if (rx_data == 8'h49) magic_idx <= 2'd3;
                                else if (rx_data == 8'h41) magic_idx <= 2'd1;
                                else magic_idx <= 2'd0;
                            end
                            2'd3: begin
                                if (rx_data == 8'h21) begin
                                    magic_idx            <= 2'd0;
                                    code_count           <= 16'd0;
                                    data_count           <= 16'd0;
                                    word_index           <= 16'd0;
                                    byte_index           <= 2'd0;
                                    expected_checksum    <= 32'd0;
                                    checksum_acc         <= 32'd0;
                                    word_buf             <= 32'd0;
                                    hold_reset           <= 1'b1;
                                    ack_index            <= 4'd0;
                                    ack_advance_pending  <= 1'b0;
                                    byte_timeout_counter <= 32'd0;
                                    state                <= S_READY_ACK;
                                end else if (rx_data == 8'h41) begin
                                    magic_idx <= 2'd1;
                                end else begin
                                    magic_idx <= 2'd0;
                                end
                            end
                        endcase
                    end
                end

                S_READY_ACK: begin
                    if (ack_advance_pending) begin
                        ack_advance_pending <= 1'b0;
                        if (ack_index == 4'd14) begin
                            ack_index <= 4'd0;
                            touch_timeout;
                            state <= S_VERSION;
                        end else begin
                            ack_index <= ack_index + 4'd1;
                        end
                    end else if (tx_ready) begin
                        tx_valid <= 1'b1;
                        ack_advance_pending <= 1'b1;
                        case (ack_index)
                            4'd0:  tx_data <= 8'h41; // A
                            4'd1:  tx_data <= 8'h44; // D
                            4'd2:  tx_data <= 8'h49; // I
                            4'd3:  tx_data <= 8'h5F; // _
                            4'd4:  tx_data <= 8'h42; // B
                            4'd5:  tx_data <= 8'h4F; // O
                            4'd6:  tx_data <= 8'h4F; // O
                            4'd7:  tx_data <= 8'h54; // T
                            4'd8:  tx_data <= 8'h5F; // _
                            4'd9:  tx_data <= 8'h52; // R
                            4'd10: tx_data <= 8'h45; // E
                            4'd11: tx_data <= 8'h41; // A
                            4'd12: tx_data <= 8'h44; // D
                            4'd13: tx_data <= 8'h59; // Y
                            default: tx_data <= 8'h0A;
                        endcase
                    end
                end

                S_VERSION: begin
                    if (rx_valid) begin
                        touch_timeout;
                        if (rx_data == VERSION_V15) begin
                            magic_idx <= 2'd0;
                            state <= S_CODE_COUNT0;
                        end else if (
                            rx_data == 8'h41 ||
                            rx_data == 8'h44 ||
                            rx_data == 8'h49 ||
                            rx_data == 8'h21
                        ) begin
                            state <= S_VERSION;
                        end else begin
                            prepare_error_ack;
                        end
                    end else begin
                        tick_or_wait;
                    end
                end

                S_CODE_COUNT0: begin
                    if (rx_valid) begin
                        touch_timeout;
                        code_count[7:0] <= rx_data;
                        state <= S_CODE_COUNT1;
                    end else begin
                        tick_or_wait;
                    end
                end

                S_CODE_COUNT1: begin
                    if (rx_valid) begin
                        touch_timeout;
                        code_count[15:8] <= rx_data;
                        if ({rx_data, code_count[7:0]} == 16'd0 || {rx_data, code_count[7:0]} > MAX_WORDS) begin
                            prepare_error_ack;
                        end else begin
                            state <= S_DATA_COUNT0;
                        end
                    end else begin
                        tick_or_wait;
                    end
                end

                S_DATA_COUNT0: begin
                    if (rx_valid) begin
                        touch_timeout;
                        data_count[7:0] <= rx_data;
                        state <= S_DATA_COUNT1;
                    end else begin
                        tick_or_wait;
                    end
                end

                S_DATA_COUNT1: begin
                    if (rx_valid) begin
                        touch_timeout;
                        data_count[15:8] <= rx_data;
                        if ({rx_data, data_count[7:0]} > MAX_DATA_WORDS) begin
                            prepare_error_ack;
                        end else begin
                            state <= S_CSUM0;
                        end
                    end else begin
                        tick_or_wait;
                    end
                end

                S_CSUM0: begin
                    if (rx_valid) begin
                        touch_timeout;
                        expected_checksum[7:0] <= rx_data;
                        state <= S_CSUM1;
                    end else begin
                        tick_or_wait;
                    end
                end

                S_CSUM1: begin
                    if (rx_valid) begin
                        touch_timeout;
                        expected_checksum[15:8] <= rx_data;
                        state <= S_CSUM2;
                    end else begin
                        tick_or_wait;
                    end
                end

                S_CSUM2: begin
                    if (rx_valid) begin
                        touch_timeout;
                        expected_checksum[23:16] <= rx_data;
                        state <= S_CSUM3;
                    end else begin
                        tick_or_wait;
                    end
                end

                S_CSUM3: begin
                    if (rx_valid) begin
                        touch_timeout;
                        expected_checksum[31:24] <= rx_data;
                        checksum_acc <= 32'd0;
                        word_index   <= 16'd0;
                        byte_index   <= 2'd0;
                        word_buf     <= 32'd0;
                        state        <= S_CODE;
                    end else begin
                        tick_or_wait;
                    end
                end

                S_CODE: begin
                    if (rx_valid) begin
                        touch_timeout;
                        checksum_acc <= checksum_acc + {24'd0, rx_data};
                        case (byte_index)
                            2'd0: begin
                                word_buf[7:0] <= rx_data;
                                byte_index <= 2'd1;
                            end
                            2'd1: begin
                                word_buf[15:8] <= rx_data;
                                byte_index <= 2'd2;
                            end
                            2'd2: begin
                                word_buf[23:16] <= rx_data;
                                byte_index <= 2'd3;
                            end
                            2'd3: begin
                                boot_addr <= word_index[9:0];
                                boot_data <= {rx_data, word_buf[23:0]};
                                boot_we   <= 1'b1;
                                byte_index <= 2'd0;

                                if (word_index + 16'd1 >= code_count) begin
                                    word_index <= 16'd0;
                                    if (data_count == 16'd0) begin
                                        if ((checksum_acc + {24'd0, rx_data}) == expected_checksum) begin
                                            ack_success <= 1'b1;
                                        end else begin
                                            ack_success <= 1'b0;
                                        end
                                        ack_index <= 4'd0;
                                        ack_advance_pending <= 1'b0;
                                        state <= S_ACK;
                                        hold_reset <= 1'b1;
                                    end else begin
                                        state <= S_DATA;
                                    end
                                end else begin
                                    word_index <= word_index + 16'd1;
                                end
                            end
                        endcase
                    end else begin
                        tick_or_wait;
                    end
                end

                S_DATA: begin
                    if (rx_valid) begin
                        touch_timeout;
                        checksum_acc <= checksum_acc + {24'd0, rx_data};
                        case (byte_index)
                            2'd0: begin
                                word_buf[7:0] <= rx_data;
                                byte_index <= 2'd1;
                            end
                            2'd1: begin
                                word_buf[15:8] <= rx_data;
                                byte_index <= 2'd2;
                            end
                            2'd2: begin
                                word_buf[23:16] <= rx_data;
                                byte_index <= 2'd3;
                            end
                            2'd3: begin
                                boot_data_addr <= word_index[8:0];
                                boot_data_word <= {rx_data, word_buf[23:0]};
                                boot_data_we   <= 1'b1;
                                byte_index <= 2'd0;

                                if (word_index + 16'd1 >= data_count) begin
                                    if ((checksum_acc + {24'd0, rx_data}) == expected_checksum) begin
                                        ack_success <= 1'b1;
                                    end else begin
                                        ack_success <= 1'b0;
                                    end
                                    ack_index <= 4'd0;
                                    ack_advance_pending <= 1'b0;
                                    state <= S_ACK;
                                    hold_reset <= 1'b1;
                                end else begin
                                    word_index <= word_index + 16'd1;
                                end
                            end
                        endcase
                    end else begin
                        tick_or_wait;
                    end
                end

                S_ACK: begin
                    if (ack_advance_pending) begin
                        ack_advance_pending <= 1'b0;
                        if (ack_success) begin
                            if (ack_index == 4'd11) begin
                                ack_index <= 4'd0;
                                restart_counter <= 5'd16;
                                state <= S_RESTART;
                            end else begin
                                ack_index <= ack_index + 4'd1;
                            end
                        end else begin
                            if (ack_index == 4'd12) begin
                                ack_index <= 4'd0;
                                enter_waiting;
                            end else begin
                                ack_index <= ack_index + 4'd1;
                            end
                        end
                    end else if (tx_ready) begin
                        tx_valid <= 1'b1;
                        ack_advance_pending <= 1'b1;
                        if (ack_success) begin
                            case (ack_index)
                                4'd0:  tx_data <= 8'h41;
                                4'd1:  tx_data <= 8'h44;
                                4'd2:  tx_data <= 8'h49;
                                4'd3:  tx_data <= 8'h5F;
                                4'd4:  tx_data <= 8'h42;
                                4'd5:  tx_data <= 8'h4F;
                                4'd6:  tx_data <= 8'h4F;
                                4'd7:  tx_data <= 8'h54;
                                4'd8:  tx_data <= 8'h5F;
                                4'd9:  tx_data <= 8'h4F;
                                4'd10: tx_data <= 8'h4B;
                                default: tx_data <= 8'h0A;
                            endcase
                        end else begin
                            case (ack_index)
                                4'd0:  tx_data <= 8'h41;
                                4'd1:  tx_data <= 8'h44;
                                4'd2:  tx_data <= 8'h49;
                                4'd3:  tx_data <= 8'h5F;
                                4'd4:  tx_data <= 8'h42;
                                4'd5:  tx_data <= 8'h4F;
                                4'd6:  tx_data <= 8'h4F;
                                4'd7:  tx_data <= 8'h54;
                                4'd8:  tx_data <= 8'h5F;
                                4'd9:  tx_data <= 8'h45;
                                4'd10: tx_data <= 8'h52;
                                4'd11: tx_data <= 8'h52;
                                default: tx_data <= 8'h0A;
                            endcase
                        end
                    end
                end

                S_RESTART: begin
                    if (restart_counter == 5'd0) begin
                        enter_running;
                    end else begin
                        restart_counter <= restart_counter - 5'd1;
                    end
                end

                default: begin
                    enter_waiting;
                end
            endcase
        end
    end

endmodule
