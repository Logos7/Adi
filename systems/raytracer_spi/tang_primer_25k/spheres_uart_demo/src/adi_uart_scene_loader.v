module adi_uart_scene_loader #(
    parameter CLK_HZ = 27000000,
    parameter BAUD = 115200
)(
    input wire clk,
    input wire rst,
    input wire uart_rx,
    output reg clear_scene,
    output reg sphere_we,
    output reg [2:0] sphere_slot,
    output reg sphere_active,
    output reg signed [15:0] sphere_cx,
    output reg signed [15:0] sphere_cy,
    output reg signed [15:0] sphere_cz,
    output reg [15:0] sphere_r,
    output reg [15:0] sphere_color,
    output reg render_pulse
);
    localparam CMD_CLEAR = 8'h01;
    localparam CMD_SPHERE = 8'h02;
    localparam CMD_RENDER = 8'h03;

    wire [7:0] rx_data;
    wire rx_valid;

    adi_uart_rx #(
        .CLK_HZ(CLK_HZ),
        .BAUD(BAUD)
    ) rx0 (
        .clk(clk),
        .rst(rst),
        .rx(uart_rx),
        .data(rx_data),
        .valid(rx_valid)
    );

    reg [3:0] state;
    reg [7:0] cmd;
    reg [7:0] len;
    reg [7:0] idx;
    reg [7:0] payload [0:31];

    integer i;

    always @(posedge clk) begin
        if (rst) begin
            state <= 0;
            cmd <= 0;
            len <= 0;
            idx <= 0;
            clear_scene <= 0;
            sphere_we <= 0;
            sphere_slot <= 0;
            sphere_active <= 0;
            sphere_cx <= 0;
            sphere_cy <= 0;
            sphere_cz <= 0;
            sphere_r <= 0;
            sphere_color <= 16'hffff;
            render_pulse <= 0;
            for (i = 0; i < 32; i = i + 1) payload[i] <= 0;
        end else begin
            clear_scene <= 0;
            sphere_we <= 0;
            render_pulse <= 0;

            if (rx_valid) begin
                case (state)
                    0: begin
                        if (rx_data == 8'hAD) state <= 1;
                    end
                    1: begin
                        if (rx_data == 8'h10) state <= 2;
                        else state <= 0;
                    end
                    2: begin
                        cmd <= rx_data;
                        state <= 3;
                    end
                    3: begin
                        len <= rx_data;
                        idx <= 0;
                        if (rx_data == 0) state <= 5;
                        else state <= 4;
                    end
                    4: begin
                        payload[idx] <= rx_data;
                        if (idx == len - 1) state <= 5;
                        else idx <= idx + 1;
                    end
                    5: begin
                        if (cmd == CMD_CLEAR) begin
                            clear_scene <= 1;
                        end else if (cmd == CMD_RENDER) begin
                            render_pulse <= 1;
                        end else if (cmd == CMD_SPHERE && len >= 12) begin
                            sphere_slot <= payload[0][2:0];
                            sphere_active <= payload[1][0];
                            sphere_cx <= {payload[3], payload[2]};
                            sphere_cy <= {payload[5], payload[4]};
                            sphere_cz <= {payload[7], payload[6]};
                            sphere_r <= {payload[9], payload[8]};
                            sphere_color <= {payload[11], payload[10]};
                            sphere_we <= 1;
                        end
                        state <= 0;
                    end
                    default: state <= 0;
                endcase
            end
        end
    end
endmodule
