module nada_music_voice (
    input wire clk,
    input wire tick_1ms,
    input wire note_on,
    input wire note_off,
    input wire [7:0] note,
    input wire [7:0] velocity,
    input wire [2:0] patch,
    output wire signed [10:0] sample
);

localparam [2:0] ENVELOPE_IDLE = 3'd0;
localparam [2:0] ENVELOPE_ATTACK = 3'd1;
localparam [2:0] ENVELOPE_DECAY = 3'd2;
localparam [2:0] ENVELOPE_SUSTAIN = 3'd3;
localparam [2:0] ENVELOPE_RELEASE = 3'd4;

reg [31:0] phase_a = 32'd0;
reg [31:0] phase_b = 32'd0;
reg [31:0] phase_increment = 32'd535082;
reg [7:0] velocity_register = 8'd0;
reg [7:0] envelope = 8'd0;
reg [2:0] envelope_state = ENVELOPE_IDLE;
reg gate = 1'b0;
reg [15:0] noise_lfsr = 16'hace1;

wire [31:0] secondary_phase_increment =
    secondary_increment_for(phase_increment, patch);

wire [7:0] triangle_a_unsigned =
    phase_a[31] ? ~phase_a[30:23] : phase_a[30:23];

wire [7:0] triangle_b_unsigned =
    phase_b[31] ? ~phase_b[30:23] : phase_b[30:23];

wire signed [8:0] triangle_a =
    $signed({1'b0, triangle_a_unsigned}) - 9'sd128;

wire signed [8:0] triangle_b =
    $signed({1'b0, triangle_b_unsigned}) - 9'sd128;

wire signed [8:0] saw_a =
    $signed({1'b0, phase_a[31:24]}) - 9'sd128;

wire signed [8:0] saw_b =
    $signed({1'b0, phase_b[31:24]}) - 9'sd128;

wire signed [8:0] square_a =
    phase_a[31] ? -9'sd120 : 9'sd120;

wire signed [8:0] square_b =
    phase_b[31] ? -9'sd120 : 9'sd120;

wire signed [8:0] pulse_a =
    phase_a[31:30] == 2'b00 ? 9'sd120 : -9'sd120;

wire signed [8:0] noise_wave =
    $signed({1'b0, noise_lfsr[7:0]}) - 9'sd128;

wire signed [10:0] triangle_a_wide = {{2{triangle_a[8]}}, triangle_a};
wire signed [10:0] triangle_b_wide = {{2{triangle_b[8]}}, triangle_b};
wire signed [10:0] saw_a_wide = {{2{saw_a[8]}}, saw_a};
wire signed [10:0] saw_b_wide = {{2{saw_b[8]}}, saw_b};
wire signed [10:0] square_a_wide = {{2{square_a[8]}}, square_a};
wire signed [10:0] square_b_wide = {{2{square_b[8]}}, square_b};
wire signed [10:0] pulse_a_wide = {{2{pulse_a[8]}}, pulse_a};
wire signed [10:0] noise_wave_wide = {{2{noise_wave[8]}}, noise_wave};

wire signed [17:0] ring_product = triangle_a * triangle_b;
wire signed [10:0] ring_wave = ring_product >>> 7;

reg signed [10:0] waveform_mix;

wire [15:0] gain = envelope * velocity_register;
wire signed [16:0] signed_gain = $signed({1'b0, gain});
wire signed [27:0] sample_product = waveform_mix * signed_gain;
wire signed [11:0] scaled_sample = sample_product >>> 16;

assign sample = scaled_sample[10:0];

always @(posedge clk) begin
    phase_a <= phase_a + phase_increment;
    phase_b <= phase_b + secondary_phase_increment;

    noise_lfsr <= {
        noise_lfsr[14:0],
        noise_lfsr[15] ^ noise_lfsr[13] ^ noise_lfsr[12] ^ noise_lfsr[10]
    };

    if (note_on) begin
        phase_increment <= note_to_phase_increment(note);
        phase_a <= 32'd0;
        phase_b <= 32'd0;
        velocity_register <= velocity;
        gate <= 1'b1;
        envelope_state <= ENVELOPE_ATTACK;
    end else if (note_off) begin
        gate <= 1'b0;
        envelope_state <= ENVELOPE_RELEASE;
    end else if (tick_1ms) begin
        case (envelope_state)
            ENVELOPE_IDLE: begin
                envelope <= 8'd0;
            end

            ENVELOPE_ATTACK: begin
                if (envelope >= 8'd255 - attack_step_for(patch)) begin
                    envelope <= 8'd255;
                    envelope_state <= ENVELOPE_DECAY;
                end else begin
                    envelope <= envelope + attack_step_for(patch);
                end
            end

            ENVELOPE_DECAY: begin
                if (envelope <= sustain_level_for(patch) + decay_step_for(patch)) begin
                    envelope <= sustain_level_for(patch);
                    envelope_state <= ENVELOPE_SUSTAIN;
                end else begin
                    envelope <= envelope - decay_step_for(patch);
                end
            end

            ENVELOPE_SUSTAIN: begin
                envelope <= sustain_level_for(patch);
                if (!gate) begin
                    envelope_state <= ENVELOPE_RELEASE;
                end
            end

            ENVELOPE_RELEASE: begin
                if (envelope <= release_step_for(patch)) begin
                    envelope <= 8'd0;
                    envelope_state <= ENVELOPE_IDLE;
                end else begin
                    envelope <= envelope - release_step_for(patch);
                end
            end

            default: begin
                envelope <= 8'd0;
                envelope_state <= ENVELOPE_IDLE;
            end
        endcase
    end
end

always @* begin
    case (patch)
        3'd0: waveform_mix = triangle_a_wide + (triangle_b_wide >>> 2);
        3'd1: waveform_mix = (saw_a_wide >>> 1) + (saw_b_wide >>> 1);
        3'd2: waveform_mix = square_a_wide + (square_b_wide >>> 1);
        3'd3: waveform_mix = pulse_a_wide + (square_b_wide >>> 1);
        3'd4: waveform_mix = ring_wave + (triangle_a_wide >>> 2);
        3'd5: waveform_mix = triangle_a_wide + (square_b_wide >>> 2);
        3'd6: waveform_mix = (noise_wave_wide >>> 1) + (triangle_a_wide >>> 2);
        3'd7: waveform_mix = triangle_a_wide + (ring_wave >>> 2);
        default: waveform_mix = triangle_a_wide;
    endcase
end

function [31:0] note_to_phase_increment;
    input [7:0] midi_note;
    begin
        case (midi_note)
            8'd36: note_to_phase_increment = 32'd133771;
            8'd37: note_to_phase_increment = 32'd141725;
            8'd38: note_to_phase_increment = 32'd150152;
            8'd39: note_to_phase_increment = 32'd159081;
            8'd40: note_to_phase_increment = 32'd168540;
            8'd41: note_to_phase_increment = 32'd178562;
            8'd42: note_to_phase_increment = 32'd189180;
            8'd43: note_to_phase_increment = 32'd200429;
            8'd44: note_to_phase_increment = 32'd212348;
            8'd45: note_to_phase_increment = 32'd224974;
            8'd46: note_to_phase_increment = 32'd238352;
            8'd47: note_to_phase_increment = 32'd252525;
            8'd48: note_to_phase_increment = 32'd267541;
            8'd49: note_to_phase_increment = 32'd283450;
            8'd50: note_to_phase_increment = 32'd300305;
            8'd51: note_to_phase_increment = 32'd318162;
            8'd52: note_to_phase_increment = 32'd337081;
            8'd53: note_to_phase_increment = 32'd357125;
            8'd54: note_to_phase_increment = 32'd378360;
            8'd55: note_to_phase_increment = 32'd400859;
            8'd56: note_to_phase_increment = 32'd424695;
            8'd57: note_to_phase_increment = 32'd449949;
            8'd58: note_to_phase_increment = 32'd476704;
            8'd59: note_to_phase_increment = 32'd505051;
            8'd60: note_to_phase_increment = 32'd535082;
            8'd61: note_to_phase_increment = 32'd566900;
            8'd62: note_to_phase_increment = 32'd600610;
            8'd63: note_to_phase_increment = 32'd636324;
            8'd64: note_to_phase_increment = 32'd674162;
            8'd65: note_to_phase_increment = 32'd714249;
            8'd66: note_to_phase_increment = 32'd756721;
            8'd67: note_to_phase_increment = 32'd801718;
            8'd68: note_to_phase_increment = 32'd849391;
            8'd69: note_to_phase_increment = 32'd899898;
            8'd70: note_to_phase_increment = 32'd953409;
            8'd71: note_to_phase_increment = 32'd1010101;
            8'd72: note_to_phase_increment = 32'd1070165;
            8'd73: note_to_phase_increment = 32'd1133800;
            8'd74: note_to_phase_increment = 32'd1201220;
            8'd75: note_to_phase_increment = 32'd1272648;
            8'd76: note_to_phase_increment = 32'd1348323;
            8'd77: note_to_phase_increment = 32'd1428499;
            8'd78: note_to_phase_increment = 32'd1513442;
            8'd79: note_to_phase_increment = 32'd1603436;
            8'd80: note_to_phase_increment = 32'd1698781;
            8'd81: note_to_phase_increment = 32'd1799796;
            8'd82: note_to_phase_increment = 32'd1906817;
            8'd83: note_to_phase_increment = 32'd2020203;
            8'd84: note_to_phase_increment = 32'd2140330;
            default: note_to_phase_increment = 32'd535082;
        endcase
    end
endfunction

function [31:0] secondary_increment_for;
    input [31:0] primary_increment;
    input [2:0] patch_id;
    begin
        case (patch_id)
            3'd0: secondary_increment_for = primary_increment << 1;
            3'd1: secondary_increment_for = primary_increment + (primary_increment >> 7);
            3'd2: secondary_increment_for = primary_increment >> 1;
            3'd3: secondary_increment_for = primary_increment << 1;
            3'd4: secondary_increment_for = (primary_increment << 1) + (primary_increment >> 1);
            3'd5: secondary_increment_for = primary_increment << 1;
            3'd6: secondary_increment_for = primary_increment + (primary_increment >> 4);
            3'd7: secondary_increment_for = primary_increment + (primary_increment >> 1);
            default: secondary_increment_for = primary_increment;
        endcase
    end
endfunction

function [7:0] attack_step_for;
    input [2:0] patch_id;
    begin
        case (patch_id)
            3'd0: attack_step_for = 8'd4;
            3'd1: attack_step_for = 8'd1;
            3'd2: attack_step_for = 8'd16;
            3'd3: attack_step_for = 8'd8;
            3'd4: attack_step_for = 8'd32;
            3'd5: attack_step_for = 8'd8;
            3'd6: attack_step_for = 8'd32;
            3'd7: attack_step_for = 8'd2;
            default: attack_step_for = 8'd4;
        endcase
    end
endfunction

function [7:0] decay_step_for;
    input [2:0] patch_id;
    begin
        case (patch_id)
            3'd0: decay_step_for = 8'd1;
            3'd1: decay_step_for = 8'd1;
            3'd2: decay_step_for = 8'd4;
            3'd3: decay_step_for = 8'd2;
            3'd4: decay_step_for = 8'd2;
            3'd5: decay_step_for = 8'd1;
            3'd6: decay_step_for = 8'd4;
            3'd7: decay_step_for = 8'd1;
            default: decay_step_for = 8'd1;
        endcase
    end
endfunction

function [7:0] sustain_level_for;
    input [2:0] patch_id;
    begin
        case (patch_id)
            3'd0: sustain_level_for = 8'd105;
            3'd1: sustain_level_for = 8'd210;
            3'd2: sustain_level_for = 8'd180;
            3'd3: sustain_level_for = 8'd200;
            3'd4: sustain_level_for = 8'd0;
            3'd5: sustain_level_for = 8'd245;
            3'd6: sustain_level_for = 8'd0;
            3'd7: sustain_level_for = 8'd150;
            default: sustain_level_for = 8'd128;
        endcase
    end
endfunction

function [7:0] release_step_for;
    input [2:0] patch_id;
    begin
        case (patch_id)
            3'd0: release_step_for = 8'd2;
            3'd1: release_step_for = 8'd1;
            3'd2: release_step_for = 8'd4;
            3'd3: release_step_for = 8'd3;
            3'd4: release_step_for = 8'd2;
            3'd5: release_step_for = 8'd2;
            3'd6: release_step_for = 8'd8;
            3'd7: release_step_for = 8'd1;
            default: release_step_for = 8'd2;
        endcase
    end
endfunction

endmodule
