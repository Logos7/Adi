module nada_tang_primer_25k_pmod_audio_internal_buzz_top (
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

wire play_0 = ~button_0_stable;
wire play_1 = ~button_1_stable;
wire play_2 = ~button_2_stable;
wire play_3 = ~button_3_stable;

localparam integer C4_HALF_PERIOD = 4013;
localparam integer E4_HALF_PERIOD = 3185;
localparam integer G4_HALF_PERIOD = 2679;
localparam integer C5_HALF_PERIOD = 2007;

reg [12:0] note_0_counter = 13'd0;
reg [12:0] note_1_counter = 13'd0;
reg [12:0] note_2_counter = 13'd0;
reg [12:0] note_3_counter = 13'd0;

reg note_0 = 1'b0;
reg note_1 = 1'b0;
reg note_2 = 1'b0;
reg note_3 = 1'b0;

always @(posedge osc_clk) begin
    if (!play_0) begin
        note_0_counter <= 13'd0;
        note_0 <= 1'b0;
    end else if (note_0_counter == C4_HALF_PERIOD - 1) begin
        note_0_counter <= 13'd0;
        note_0 <= ~note_0;
    end else begin
        note_0_counter <= note_0_counter + 1'b1;
    end

    if (!play_1) begin
        note_1_counter <= 13'd0;
        note_1 <= 1'b0;
    end else if (note_1_counter == E4_HALF_PERIOD - 1) begin
        note_1_counter <= 13'd0;
        note_1 <= ~note_1;
    end else begin
        note_1_counter <= note_1_counter + 1'b1;
    end

    if (!play_2) begin
        note_2_counter <= 13'd0;
        note_2 <= 1'b0;
    end else if (note_2_counter == G4_HALF_PERIOD - 1) begin
        note_2_counter <= 13'd0;
        note_2 <= ~note_2;
    end else begin
        note_2_counter <= note_2_counter + 1'b1;
    end

    if (!play_3) begin
        note_3_counter <= 13'd0;
        note_3 <= 1'b0;
    end else if (note_3_counter == C5_HALF_PERIOD - 1) begin
        note_3_counter <= 13'd0;
        note_3 <= ~note_3;
    end else begin
        note_3_counter <= note_3_counter + 1'b1;
    end
end

wire any_play = play_0 | play_1 | play_2 | play_3;

wire signed [5:0] voice_0 =
    play_0 ? (note_0 ? 6'sd1 : -6'sd1) : 6'sd0;

wire signed [5:0] voice_1 =
    play_1 ? (note_1 ? 6'sd1 : -6'sd1) : 6'sd0;

wire signed [5:0] voice_2 =
    play_2 ? (note_2 ? 6'sd1 : -6'sd1) : 6'sd0;

wire signed [5:0] voice_3 =
    play_3 ? (note_3 ? 6'sd1 : -6'sd1) : 6'sd0;

wire signed [5:0] mixed =
    voice_0 + voice_1 + voice_2 + voice_3;

wire signed [7:0] mixed_wide =
    {{2{mixed[5]}}, mixed};

wire signed [7:0] pwm_level_signed =
    8'sd16 + (mixed_wide <<< 1) + mixed_wide;

wire [5:0] pwm_level =
    pwm_level_signed[5:0];

reg [4:0] pwm_counter = 5'd0;

always @(posedge osc_clk) begin
    pwm_counter <= pwm_counter + 1'b1;
end

wire audio_mix =
    any_play &&
    ({1'b0, pwm_counter} < pwm_level);

assign audio_row_a_1 = audio_mix;
assign audio_row_a_2 = audio_mix;
assign audio_row_b_1 = audio_mix;
assign audio_row_b_2 = audio_mix;

endmodule
