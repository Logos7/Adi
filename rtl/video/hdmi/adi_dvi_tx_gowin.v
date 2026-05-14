// =============================================================================
// adi_dvi_tx_gowin.v
// Minimal DVI-compatible TMDS transmitter for Gowin. Verilog-2001.
//
// Reset policy:
// - I_rst_n may come from the board/PLL domain.
// - Reset assertion is asynchronous.
// - Reset release is synchronized independently into I_rgb_clk and I_serial_clk.
//
// This prevents timing paths from a slow-domain reset register directly into
// OSER10 RESET pins in the fast TMDS clock domain.
// =============================================================================

module DVI_TX_Top (
    input wire I_rst_n,
    input wire I_serial_clk,
    input wire I_rgb_clk,
    input wire I_rgb_vs,
    input wire I_rgb_hs,
    input wire I_rgb_de,
    input wire [7:0] I_rgb_r,
    input wire [7:0] I_rgb_g,
    input wire [7:0] I_rgb_b,
    output wire O_tmds_clk_p,
    output wire O_tmds_clk_n,
    output wire [2:0] O_tmds_data_p,
    output wire [2:0] O_tmds_data_n
);
    reg [2:0] rgb_rst_n_sync;
    reg [2:0] serial_rst_n_sync;

    initial begin
        rgb_rst_n_sync = 3'b000;
        serial_rst_n_sync = 3'b000;
    end

    always @(posedge I_rgb_clk or negedge I_rst_n) begin
        if (!I_rst_n)
            rgb_rst_n_sync <= 3'b000;
        else
            rgb_rst_n_sync <= {rgb_rst_n_sync[1:0], 1'b1};
    end

    always @(posedge I_serial_clk or negedge I_rst_n) begin
        if (!I_rst_n)
            serial_rst_n_sync <= 3'b000;
        else
            serial_rst_n_sync <= {serial_rst_n_sync[1:0], 1'b1};
    end

    wire rgb_rst_n = rgb_rst_n_sync[2];
    wire serial_rst = ~serial_rst_n_sync[2];

    wire [9:0] tmds_r;
    wire [9:0] tmds_g;
    wire [9:0] tmds_b;

    adi_tmds_encoder enc_b (
        .clk(I_rgb_clk),
        .rst_n(rgb_rst_n),
        .de(I_rgb_de),
        .c0(I_rgb_hs),
        .c1(I_rgb_vs),
        .data(I_rgb_b),
        .encoded(tmds_b)
    );

    adi_tmds_encoder enc_g (
        .clk(I_rgb_clk),
        .rst_n(rgb_rst_n),
        .de(I_rgb_de),
        .c0(1'b0),
        .c1(1'b0),
        .data(I_rgb_g),
        .encoded(tmds_g)
    );

    adi_tmds_encoder enc_r (
        .clk(I_rgb_clk),
        .rst_n(rgb_rst_n),
        .de(I_rgb_de),
        .c0(1'b0),
        .c1(1'b0),
        .data(I_rgb_r),
        .encoded(tmds_r)
    );

    adi_tmds_output out_b (
        .pclk(I_rgb_clk),
        .fclk(I_serial_clk),
        .rst(serial_rst),
        .data(tmds_b),
        .out_p(O_tmds_data_p[0]),
        .out_n(O_tmds_data_n[0])
    );

    adi_tmds_output out_g (
        .pclk(I_rgb_clk),
        .fclk(I_serial_clk),
        .rst(serial_rst),
        .data(tmds_g),
        .out_p(O_tmds_data_p[1]),
        .out_n(O_tmds_data_n[1])
    );

    adi_tmds_output out_r (
        .pclk(I_rgb_clk),
        .fclk(I_serial_clk),
        .rst(serial_rst),
        .data(tmds_r),
        .out_p(O_tmds_data_p[2]),
        .out_n(O_tmds_data_n[2])
    );

    adi_tmds_output out_clk (
        .pclk(I_rgb_clk),
        .fclk(I_serial_clk),
        .rst(serial_rst),
        .data(10'b0000011111),
        .out_p(O_tmds_clk_p),
        .out_n(O_tmds_clk_n)
    );
endmodule

module adi_tmds_encoder (
    input wire clk,
    input wire rst_n,
    input wire de,
    input wire c0,
    input wire c1,
    input wire [7:0] data,
    output reg [9:0] encoded
);
    reg signed [5:0] balance;
    reg [8:0] q_m;
    reg [3:0] ones_data;
    reg [3:0] ones_qm;
    reg [3:0] zeros_qm;
    reg signed [5:0] diff_qm;
    integer i;

    always @* begin
        ones_data = data[0] + data[1] + data[2] + data[3]
            + data[4] + data[5] + data[6] + data[7];

        q_m[0] = data[0];
        if ((ones_data > 4'd4) || ((ones_data == 4'd4) && (data[0] == 1'b0))) begin
            for (i = 1; i < 8; i = i + 1)
                q_m[i] = q_m[i-1] ~^ data[i];
            q_m[8] = 1'b0;
        end else begin
            for (i = 1; i < 8; i = i + 1)
                q_m[i] = q_m[i-1] ^ data[i];
            q_m[8] = 1'b1;
        end

        ones_qm = q_m[0] + q_m[1] + q_m[2] + q_m[3]
            + q_m[4] + q_m[5] + q_m[6] + q_m[7];
        zeros_qm = 4'd8 - ones_qm;
        diff_qm = $signed({2'b00, ones_qm}) - $signed({2'b00, zeros_qm});
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            encoded <= 10'b1101010100;
            balance <= 6'sd0;
        end else if (!de) begin
            balance <= 6'sd0;
            case ({c1, c0})
                2'b00: encoded <= 10'b1101010100;
                2'b01: encoded <= 10'b0010101011;
                2'b10: encoded <= 10'b0101010100;
                default: encoded <= 10'b1010101011;
            endcase
        end else begin
            if ((balance == 6'sd0) || (ones_qm == zeros_qm)) begin
                if (q_m[8]) begin
                    encoded <= {2'b01, q_m[7:0]};
                    balance <= balance + diff_qm;
                end else begin
                    encoded <= {2'b10, ~q_m[7:0]};
                    balance <= balance - diff_qm;
                end
            end else if (((balance > 6'sd0) && (ones_qm > zeros_qm)) ||
                         ((balance < 6'sd0) && (zeros_qm > ones_qm))) begin
                encoded <= {1'b1, q_m[8], ~q_m[7:0]};
                if (q_m[8])
                    balance <= balance - diff_qm + 6'sd2;
                else
                    balance <= balance - diff_qm;
            end else begin
                encoded <= {1'b0, q_m[8], q_m[7:0]};
                if (q_m[8])
                    balance <= balance + diff_qm;
                else
                    balance <= balance + diff_qm - 6'sd2;
            end
        end
    end
endmodule

module adi_tmds_output (
    input wire pclk,
    input wire fclk,
    input wire rst,
    input wire [9:0] data,
    output wire out_p,
    output wire out_n
);
    wire serial;

    OSER10 u_oser10 (
        .Q(serial),
        .D0(data[0]),
        .D1(data[1]),
        .D2(data[2]),
        .D3(data[3]),
        .D4(data[4]),
        .D5(data[5]),
        .D6(data[6]),
        .D7(data[7]),
        .D8(data[8]),
        .D9(data[9]),
        .PCLK(pclk),
        .FCLK(fclk),
        .RESET(rst)
    );
    defparam u_oser10.GSREN = "false";
    defparam u_oser10.LSREN = "true";

`ifdef ADI_HDMI_USE_TLVDS_OBUF
    TLVDS_OBUF u_obuf (
        .O(out_p),
        .OB(out_n),
        .I(serial)
    );
`else
    ELVDS_OBUF u_obuf (
        .O(out_p),
        .OB(out_n),
        .I(serial)
    );
`endif
endmodule
