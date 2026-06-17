module nada_tang_primer_25k_pmod_audio_dds_synth_top (
    input wire button_0_n,
    input wire button_1_n,
    input wire button_2_n,
    input wire button_3_n,
    output wire audio_row_a_1,
    output wire audio_row_a_2,
    output wire audio_row_b_1,
    output wire audio_row_b_2
);

wire osc_clk;

OSCA oscillator (
    .OSCOUT(osc_clk),
    .OSCEN(1'b1)
);

defparam oscillator.FREQ_DIV = 100;

reg [1:0] button_0_sync = 2'b11;
reg [1:0] button_1_sync = 2'b11;
reg [1:0] button_2_sync = 2'b11;
reg [1:0] button_3_sync = 2'b11;

always @(posedge osc_clk) begin
    button_0_sync <= {button_0_sync[0], button_0_n};
    button_1_sync <= {button_1_sync[0], button_1_n};
    button_2_sync <= {button_2_sync[0], button_2_n};
    button_3_sync <= {button_3_sync[0], button_3_n};
end

reg button_0_stable = 1'b1;
reg button_1_stable = 1'b1;
reg button_2_stable = 1'b1;
reg button_3_stable = 1'b1;

reg [14:0] button_0_debounce = 15'd0;
reg [14:0] button_1_debounce = 15'd0;
reg [14:0] button_2_debounce = 15'd0;
reg [14:0] button_3_debounce = 15'd0;

always @(posedge osc_clk) begin
    if (button_0_sync[1] == button_0_stable) begin
        button_0_debounce <= 15'd0;
    end else if (&button_0_debounce) begin
        button_0_stable <= button_0_sync[1];
        button_0_debounce <= 15'd0;
    end else begin
        button_0_debounce <= button_0_debounce + 1'b1;
    end

    if (button_1_sync[1] == button_1_stable) begin
        button_1_debounce <= 15'd0;
    end else if (&button_1_debounce) begin
        button_1_stable <= button_1_sync[1];
        button_1_debounce <= 15'd0;
    end else begin
        button_1_debounce <= button_1_debounce + 1'b1;
    end

    if (button_2_sync[1] == button_2_stable) begin
        button_2_debounce <= 15'd0;
    end else if (&button_2_debounce) begin
        button_2_stable <= button_2_sync[1];
        button_2_debounce <= 15'd0;
    end else begin
        button_2_debounce <= button_2_debounce + 1'b1;
    end

    if (button_3_sync[1] == button_3_stable) begin
        button_3_debounce <= 15'd0;
    end else if (&button_3_debounce) begin
        button_3_stable <= button_3_sync[1];
        button_3_debounce <= 15'd0;
    end else begin
        button_3_debounce <= button_3_debounce + 1'b1;
    end
end

wire gate_0 = ~button_0_stable;
wire gate_1 = ~button_1_stable;
wire gate_2 = ~button_2_stable;
wire gate_3 = ~button_3_stable;

localparam [31:0] C4_PHASE_INCREMENT = 32'd535082;
localparam [31:0] E4_PHASE_INCREMENT = 32'd674162;
localparam [31:0] G4_PHASE_INCREMENT = 32'd801718;
localparam [31:0] C5_PHASE_INCREMENT = 32'd1070165;

reg [31:0] phase_0 = 32'd0;
reg [31:0] phase_1 = 32'd0;
reg [31:0] phase_2 = 32'd0;
reg [31:0] phase_3 = 32'd0;

always @(posedge osc_clk) begin
    phase_0 <= phase_0 + C4_PHASE_INCREMENT;
    phase_1 <= phase_1 + E4_PHASE_INCREMENT;
    phase_2 <= phase_2 + G4_PHASE_INCREMENT;
    phase_3 <= phase_3 + C5_PHASE_INCREMENT;
end

reg [11:0] envelope_tick_counter = 12'd0;
wire envelope_tick = envelope_tick_counter == 12'd2099;

always @(posedge osc_clk) begin
    if (envelope_tick) begin
        envelope_tick_counter <= 12'd0;
    end else begin
        envelope_tick_counter <= envelope_tick_counter + 1'b1;
    end
end

reg [7:0] envelope_0 = 8'd0;
reg [7:0] envelope_1 = 8'd0;
reg [7:0] envelope_2 = 8'd0;
reg [7:0] envelope_3 = 8'd0;

always @(posedge osc_clk) begin
    if (envelope_tick) begin
        if (gate_0) begin
            envelope_0 <= envelope_0 >= 8'd251 ? 8'd255 : envelope_0 + 8'd4;
        end else begin
            envelope_0 <= envelope_0 == 8'd0 ? 8'd0 : envelope_0 - 1'b1;
        end

        if (gate_1) begin
            envelope_1 <= envelope_1 >= 8'd251 ? 8'd255 : envelope_1 + 8'd4;
        end else begin
            envelope_1 <= envelope_1 == 8'd0 ? 8'd0 : envelope_1 - 1'b1;
        end

        if (gate_2) begin
            envelope_2 <= envelope_2 >= 8'd251 ? 8'd255 : envelope_2 + 8'd4;
        end else begin
            envelope_2 <= envelope_2 == 8'd0 ? 8'd0 : envelope_2 - 1'b1;
        end

        if (gate_3) begin
            envelope_3 <= envelope_3 >= 8'd251 ? 8'd255 : envelope_3 + 8'd4;
        end else begin
            envelope_3 <= envelope_3 == 8'd0 ? 8'd0 : envelope_3 - 1'b1;
        end
    end
end

wire [7:0] triangle_0_unsigned =
    phase_0[31] ? ~phase_0[30:23] : phase_0[30:23];

wire [7:0] triangle_1_unsigned =
    phase_1[31] ? ~phase_1[30:23] : phase_1[30:23];

wire [7:0] triangle_2_unsigned =
    phase_2[31] ? ~phase_2[30:23] : phase_2[30:23];

wire [7:0] triangle_3_unsigned =
    phase_3[31] ? ~phase_3[30:23] : phase_3[30:23];

wire signed [8:0] triangle_0 =
    $signed({1'b0, triangle_0_unsigned}) - 9'sd128;

wire signed [8:0] triangle_1 =
    $signed({1'b0, triangle_1_unsigned}) - 9'sd128;

wire signed [8:0] triangle_2 =
    $signed({1'b0, triangle_2_unsigned}) - 9'sd128;

wire signed [8:0] triangle_3 =
    $signed({1'b0, triangle_3_unsigned}) - 9'sd128;

wire signed [8:0] envelope_0_signed = $signed({1'b0, envelope_0});
wire signed [8:0] envelope_1_signed = $signed({1'b0, envelope_1});
wire signed [8:0] envelope_2_signed = $signed({1'b0, envelope_2});
wire signed [8:0] envelope_3_signed = $signed({1'b0, envelope_3});

wire signed [17:0] product_0 = triangle_0 * envelope_0_signed;
wire signed [17:0] product_1 = triangle_1 * envelope_1_signed;
wire signed [17:0] product_2 = triangle_2 * envelope_2_signed;
wire signed [17:0] product_3 = triangle_3 * envelope_3_signed;

wire signed [9:0] voice_0 = product_0 >>> 8;
wire signed [9:0] voice_1 = product_1 >>> 8;
wire signed [9:0] voice_2 = product_2 >>> 8;
wire signed [9:0] voice_3 = product_3 >>> 8;

wire signed [11:0] mix =
    voice_0 + voice_1 + voice_2 + voice_3;

wire signed [11:0] normalized_mix = mix >>> 2;
wire [7:0] audio_sample = normalized_mix[7:0] + 8'd128;

reg [8:0] sigma_delta = 9'd0;

always @(posedge osc_clk) begin
    sigma_delta <= {1'b0, sigma_delta[7:0]} + {1'b0, audio_sample};
end

wire audio_bit = sigma_delta[8];

assign audio_row_a_1 = audio_bit;
assign audio_row_a_2 = audio_bit;
assign audio_row_b_1 = audio_bit;
assign audio_row_b_2 = audio_bit;

endmodule
