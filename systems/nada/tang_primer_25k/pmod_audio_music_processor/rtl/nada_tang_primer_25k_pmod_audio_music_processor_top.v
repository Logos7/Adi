module nada_tang_primer_25k_pmod_audio_music_processor_top (
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

reg [11:0] millisecond_counter = 12'd0;
wire tick_1ms = millisecond_counter == 12'd2099;

always @(posedge osc_clk) begin
    if (tick_1ms) begin
        millisecond_counter <= 12'd0;
    end else begin
        millisecond_counter <= millisecond_counter + 1'b1;
    end
end

wire button_patch_previous;
wire button_patch_next;
wire button_song_next;
wire button_play_stop;

nada_button_panel button_panel (
    .clk(osc_clk),
    .button_0_n(button_0_n),
    .button_1_n(button_1_n),
    .button_2_n(button_2_n),
    .button_3_n(button_3_n),
    .button_0_pressed(button_patch_previous),
    .button_1_pressed(button_patch_next),
    .button_2_pressed(button_song_next),
    .button_3_pressed(button_play_stop)
);

wire note_on_0;
wire note_off_0;
wire [7:0] note_0;
wire [7:0] velocity_0;
wire [2:0] patch_0;

wire note_on_1;
wire note_off_1;
wire [7:0] note_1;
wire [7:0] velocity_1;
wire [2:0] patch_1;

wire note_on_2;
wire note_off_2;
wire [7:0] note_2;
wire [7:0] velocity_2;
wire [2:0] patch_2;

wire note_on_3;
wire note_off_3;
wire [7:0] note_3;
wire [7:0] velocity_3;
wire [2:0] patch_3;

wire [2:0] selected_patch;
wire [1:0] selected_song;
wire running;

nada_music_processor processor (
    .clk(osc_clk),
    .button_patch_previous(button_patch_previous),
    .button_patch_next(button_patch_next),
    .button_song_next(button_song_next),
    .button_play_stop(button_play_stop),

    .note_on_0(note_on_0),
    .note_off_0(note_off_0),
    .note_0(note_0),
    .velocity_0(velocity_0),
    .patch_0(patch_0),

    .note_on_1(note_on_1),
    .note_off_1(note_off_1),
    .note_1(note_1),
    .velocity_1(velocity_1),
    .patch_1(patch_1),

    .note_on_2(note_on_2),
    .note_off_2(note_off_2),
    .note_2(note_2),
    .velocity_2(velocity_2),
    .patch_2(patch_2),

    .note_on_3(note_on_3),
    .note_off_3(note_off_3),
    .note_3(note_3),
    .velocity_3(velocity_3),
    .patch_3(patch_3),

    .selected_patch(selected_patch),
    .selected_song(selected_song),
    .running(running)
);

wire signed [10:0] voice_sample_0;
wire signed [10:0] voice_sample_1;
wire signed [10:0] voice_sample_2;
wire signed [10:0] voice_sample_3;

nada_music_voice voice_0 (
    .clk(osc_clk),
    .tick_1ms(tick_1ms),
    .note_on(note_on_0),
    .note_off(note_off_0),
    .note(note_0),
    .velocity(velocity_0),
    .patch(patch_0),
    .sample(voice_sample_0)
);

nada_music_voice voice_1 (
    .clk(osc_clk),
    .tick_1ms(tick_1ms),
    .note_on(note_on_1),
    .note_off(note_off_1),
    .note(note_1),
    .velocity(velocity_1),
    .patch(patch_1),
    .sample(voice_sample_1)
);

nada_music_voice voice_2 (
    .clk(osc_clk),
    .tick_1ms(tick_1ms),
    .note_on(note_on_2),
    .note_off(note_off_2),
    .note(note_2),
    .velocity(velocity_2),
    .patch(patch_2),
    .sample(voice_sample_2)
);

nada_music_voice voice_3 (
    .clk(osc_clk),
    .tick_1ms(tick_1ms),
    .note_on(note_on_3),
    .note_off(note_off_3),
    .note(note_3),
    .velocity(velocity_3),
    .patch(patch_3),
    .sample(voice_sample_3)
);

wire signed [12:0] extended_voice_0 =
    {{2{voice_sample_0[10]}}, voice_sample_0};

wire signed [12:0] extended_voice_1 =
    {{2{voice_sample_1[10]}}, voice_sample_1};

wire signed [12:0] extended_voice_2 =
    {{2{voice_sample_2[10]}}, voice_sample_2};

wire signed [12:0] extended_voice_3 =
    {{2{voice_sample_3[10]}}, voice_sample_3};

wire signed [12:0] mixed_voices =
    extended_voice_0 +
    extended_voice_1 +
    extended_voice_2 +
    extended_voice_3;

wire signed [12:0] normalized_mix = mixed_voices >>> 1;
reg [9:0] audio_sample;
wire audio_bit;

always @* begin
    if (normalized_mix < -13'sd512) begin
        audio_sample = 10'd0;
    end else if (normalized_mix > 13'sd511) begin
        audio_sample = 10'd1023;
    end else begin
        audio_sample = normalized_mix + 13'sd512;
    end
end

nada_sigma_delta_dac dac (
    .clk(osc_clk),
    .sample(audio_sample),
    .audio_bit(audio_bit)
);

assign audio_row_a_1 = audio_bit;
assign audio_row_a_2 = audio_bit;
assign audio_row_b_1 = audio_bit;
assign audio_row_b_2 = audio_bit;

endmodule
