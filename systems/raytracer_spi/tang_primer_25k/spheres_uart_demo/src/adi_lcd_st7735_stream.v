module adi_lcd_st7735_stream #(
    parameter WIDTH = 160,
    parameter HEIGHT = 80,
    parameter X_OFFSET = 0,
    parameter Y_OFFSET = 24,
    parameter MADCTL = 8'h60,
    parameter SPI_CLK_DIV = 2,
    parameter CLK_HZ = 50000000
)(
    input wire clk,
    input wire rst,
    output wire lcd_sck,
    output wire lcd_mosi,
    output reg lcd_cs,
    output reg lcd_dc,
    output reg lcd_rst,
    output reg pixel_req,
    input wire pixel_valid,
    input wire [15:0] pixel_rgb565
);
    localparam S_RESET_LOW = 0;
    localparam S_RESET_HIGH = 1;
    localparam S_INIT_SEND = 2;
    localparam S_INIT_WAIT = 3;
    localparam S_FRAME_SEND = 4;
    localparam S_PIXEL_REQ = 5;
    localparam S_PIXEL_WAIT = 6;
    localparam S_PIXEL_HI = 7;
    localparam S_PIXEL_LO = 8;
    localparam S_BYTE_WAIT = 9;

    localparam [15:0] X0V = X_OFFSET;
    localparam [15:0] Y0V = Y_OFFSET;
    localparam [15:0] X1V = X_OFFSET + WIDTH - 1;
    localparam [15:0] Y1V = Y_OFFSET + HEIGHT - 1;
    localparam integer FRAME_PIXELS = WIDTH * HEIGHT;

    reg [3:0] state;
    reg [7:0] init_step;
    reg [7:0] frame_step;
    reg [23:0] delay_ctr;
    reg [31:0] pixel_ctr;
    reg [7:0] tx_data;
    reg tx_start;
    wire tx_busy;
    wire tx_done;
    reg [1:0] byte_context;
    reg [15:0] latched_pixel;

    adi_spi_byte_tx #(
        .CLK_DIV(SPI_CLK_DIV)
    ) spi0 (
        .clk(clk),
        .rst(rst),
        .start(tx_start),
        .data(tx_data),
        .busy(tx_busy),
        .done(tx_done),
        .sck(lcd_sck),
        .mosi(lcd_mosi)
    );

    function [7:0] init_value;
        input [7:0] s;
        begin
            case (s)
                0: init_value = 8'h01;
                1: init_value = 8'h11;
                2: init_value = 8'h3A;
                3: init_value = 8'h05;
                4: init_value = 8'h36;
                5: init_value = MADCTL;
                6: init_value = 8'h29;
                default: init_value = 8'h00;
            endcase
        end
    endfunction

    function init_is_data;
        input [7:0] s;
        begin
            case (s)
                3: init_is_data = 1'b1;
                5: init_is_data = 1'b1;
                default: init_is_data = 1'b0;
            endcase
        end
    endfunction

    function [23:0] init_delay;
        input [7:0] s;
        begin
            case (s)
                0: init_delay = CLK_HZ / 10;
                1: init_delay = CLK_HZ / 10;
                6: init_delay = CLK_HZ / 10;
                default: init_delay = 24'd0;
            endcase
        end
    endfunction

    function [7:0] frame_value;
        input [7:0] s;
        begin
            case (s)
                0: frame_value = 8'h2A;
                1: frame_value = X0V[15:8];
                2: frame_value = X0V[7:0];
                3: frame_value = X1V[15:8];
                4: frame_value = X1V[7:0];
                5: frame_value = 8'h2B;
                6: frame_value = Y0V[15:8];
                7: frame_value = Y0V[7:0];
                8: frame_value = Y1V[15:8];
                9: frame_value = Y1V[7:0];
                10: frame_value = 8'h2C;
                default: frame_value = 8'h00;
            endcase
        end
    endfunction

    function frame_is_data;
        input [7:0] s;
        begin
            case (s)
                1,2,3,4,6,7,8,9: frame_is_data = 1'b1;
                default: frame_is_data = 1'b0;
            endcase
        end
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            state <= S_RESET_LOW;
            init_step <= 0;
            frame_step <= 0;
            delay_ctr <= CLK_HZ / 10;
            pixel_ctr <= 0;
            tx_data <= 0;
            tx_start <= 0;
            lcd_cs <= 1;
            lcd_dc <= 0;
            lcd_rst <= 0;
            pixel_req <= 0;
            byte_context <= 0;
            latched_pixel <= 0;
        end else begin
            tx_start <= 0;
            pixel_req <= 0;

            case (state)
                S_RESET_LOW: begin
                    lcd_rst <= 0;
                    lcd_cs <= 1;
                    lcd_dc <= 0;
                    if (delay_ctr == 0) begin
                        delay_ctr <= CLK_HZ / 10;
                        state <= S_RESET_HIGH;
                    end else begin
                        delay_ctr <= delay_ctr - 1;
                    end
                end
                S_RESET_HIGH: begin
                    lcd_rst <= 1;
                    if (delay_ctr == 0) begin
                        init_step <= 0;
                        state <= S_INIT_SEND;
                    end else begin
                        delay_ctr <= delay_ctr - 1;
                    end
                end
                S_INIT_SEND: begin
                    if (!tx_busy) begin
                        lcd_cs <= 0;
                        lcd_dc <= init_is_data(init_step);
                        tx_data <= init_value(init_step);
                        tx_start <= 1;
                        byte_context <= 0;
                        state <= S_BYTE_WAIT;
                    end
                end
                S_INIT_WAIT: begin
                    if (delay_ctr == 0) begin
                        if (init_step == 6) begin
                            frame_step <= 0;
                            state <= S_FRAME_SEND;
                        end else begin
                            init_step <= init_step + 1;
                            state <= S_INIT_SEND;
                        end
                    end else begin
                        delay_ctr <= delay_ctr - 1;
                    end
                end
                S_FRAME_SEND: begin
                    if (!tx_busy) begin
                        lcd_cs <= 0;
                        lcd_dc <= frame_is_data(frame_step);
                        tx_data <= frame_value(frame_step);
                        tx_start <= 1;
                        byte_context <= 1;
                        state <= S_BYTE_WAIT;
                    end
                end
                S_PIXEL_REQ: begin
                    pixel_req <= 1;
                    state <= S_PIXEL_WAIT;
                end
                S_PIXEL_WAIT: begin
                    if (pixel_valid) begin
                        latched_pixel <= pixel_rgb565;
                        state <= S_PIXEL_HI;
                    end
                end
                S_PIXEL_HI: begin
                    if (!tx_busy) begin
                        lcd_cs <= 0;
                        lcd_dc <= 1;
                        tx_data <= latched_pixel[15:8];
                        tx_start <= 1;
                        byte_context <= 2;
                        state <= S_BYTE_WAIT;
                    end
                end
                S_PIXEL_LO: begin
                    if (!tx_busy) begin
                        lcd_cs <= 0;
                        lcd_dc <= 1;
                        tx_data <= latched_pixel[7:0];
                        tx_start <= 1;
                        byte_context <= 3;
                        state <= S_BYTE_WAIT;
                    end
                end
                S_BYTE_WAIT: begin
                    if (tx_done) begin
                        if (byte_context == 0) begin
                            delay_ctr <= init_delay(init_step);
                            if (init_delay(init_step) != 0) begin
                                state <= S_INIT_WAIT;
                            end else begin
                                if (init_step == 6) begin
                                    frame_step <= 0;
                                    state <= S_FRAME_SEND;
                                end else begin
                                    init_step <= init_step + 1;
                                    state <= S_INIT_SEND;
                                end
                            end
                        end else if (byte_context == 1) begin
                            if (frame_step == 10) begin
                                pixel_ctr <= 0;
                                state <= S_PIXEL_REQ;
                            end else begin
                                frame_step <= frame_step + 1;
                                state <= S_FRAME_SEND;
                            end
                        end else if (byte_context == 2) begin
                            state <= S_PIXEL_LO;
                        end else begin
                            if (pixel_ctr == FRAME_PIXELS - 1) begin
                                pixel_ctr <= 0;
                                frame_step <= 0;
                                state <= S_FRAME_SEND;
                            end else begin
                                pixel_ctr <= pixel_ctr + 1;
                                state <= S_PIXEL_REQ;
                            end
                        end
                    end
                end
                default: state <= S_RESET_LOW;
            endcase
        end
    end
endmodule
