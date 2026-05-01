// =============================================================================
// brahma_bija_core.v
// Brahma-Bija multicycle CPU core.
//
// Verilog-2001 / Gowin-friendly version:
// - no SystemVerilog-only constructs,
// - data_mem is inferred as synchronous block RAM,
// - call/return use a small 16-entry hardware return stack,
// - 1-bit framebuffer helpers use caller-selected data_mem base address.
// =============================================================================

module brahma_bija_core (
    input wire clk,
    input wire rst,

    output wire [127:0] gpio_out,

    input wire uart_tx_ready,
    output reg uart_tx_valid,
    output reg [7:0] uart_tx_data,

    input wire uart_rx_valid,
    input wire [7:0] uart_rx_data,

    input wire boot_we,
    input wire [9:0] boot_addr,
    input wire [31:0] boot_data
);

    // -------------------------------------------------------------------------
    // Opcodes
    // -------------------------------------------------------------------------

    localparam [5:0] OP_NOP       = 6'h00;
    localparam [5:0] OP_ALU_R     = 6'h01;
    localparam [5:0] OP_CMP_R     = 6'h02;

    localparam [5:0] OP_LOAD_I    = 6'h10;
    localparam [5:0] OP_LOAD_L    = 6'h11;
    localparam [5:0] OP_LOAD_M    = 6'h12;
    localparam [5:0] OP_SAVE_M    = 6'h13;
    localparam [5:0] OP_LOAD_MD   = 6'h14;
    localparam [5:0] OP_SAVE_MD   = 6'h15;

    localparam [5:0] OP_SAVE_BI   = 6'h20;
    localparam [5:0] OP_LOAD_BI   = 6'h21;
    localparam [5:0] OP_BOOL_R    = 6'h22;
    localparam [5:0] OP_LOAD_BR   = 6'h23;
    localparam [5:0] OP_SAVE_BR   = 6'h24;

    localparam [5:0] OP_WAIT      = 6'h30;
    localparam [5:0] OP_FBCLEAR   = 6'h31;
    localparam [5:0] OP_FBPLOT    = 6'h32;
    localparam [5:0] OP_FBERASE   = 6'h33;
    localparam [5:0] OP_FBPRESENT = 6'h34;

    localparam [5:0] OP_JUMP      = 6'h38;
    localparam [5:0] OP_CALL      = 6'h39;
    localparam [5:0] OP_RETURN    = 6'h3A;
    localparam [5:0] OP_HALT      = 6'h3F;

    localparam [8:0] UART_TX_ADDR = 9'h0F0;
    localparam [8:0] UART_RX_ADDR = 9'h0F1;

    localparam [13:0] UART_READY_BOOL_ADDR    = 14'd128;
    localparam [13:0] UART_RX_READY_BOOL_ADDR = 14'd129;

    localparam [6:0] FUNCT_IADD = 7'h00;
    localparam [6:0] FUNCT_ISUB = 7'h01;
    localparam [6:0] FUNCT_IAND = 7'h02;
    localparam [6:0] FUNCT_IOR  = 7'h03;
    localparam [6:0] FUNCT_IXOR = 7'h04;
    localparam [6:0] FUNCT_SHL  = 7'h05;
    localparam [6:0] FUNCT_SHR  = 7'h06;
    localparam [6:0] FUNCT_SAR  = 7'h07;
    localparam [6:0] FUNCT_IMUL = 7'h08;
    localparam [6:0] FUNCT_FMUL = 7'h09;
    localparam [6:0] FUNCT_ITOF = 7'h0A;
    localparam [6:0] FUNCT_FTOI = 7'h0B;
    localparam [6:0] FUNCT_INOT = 7'h0C;
    localparam [6:0] FUNCT_FADD = 7'h0D;
    localparam [6:0] FUNCT_FSUB = 7'h0E;
    localparam [6:0] FUNCT_FABS = 7'h0F;
    localparam [6:0] FUNCT_MOV  = 7'h10;

    localparam [6:0] FUNCT_BAND = 7'h00;
    localparam [6:0] FUNCT_BOR  = 7'h01;
    localparam [6:0] FUNCT_BXOR = 7'h02;
    localparam [6:0] FUNCT_BNOT = 7'h03;
    localparam [6:0] FUNCT_BMOV = 7'h04;

    localparam [6:0] FUNCT_CMP_EQ = 7'h00;
    localparam [6:0] FUNCT_CMP_NE = 7'h01;
    localparam [6:0] FUNCT_CMP_LT = 7'h02;
    localparam [6:0] FUNCT_CMP_LE = 7'h03;
    localparam [6:0] FUNCT_CMP_GT = 7'h04;
    localparam [6:0] FUNCT_CMP_GE = 7'h05;

    // -------------------------------------------------------------------------
    // FSM states
    // -------------------------------------------------------------------------

    localparam [4:0] S_FETCH             = 5'd0;
    localparam [4:0] S_FETCH2            = 5'd1;
    localparam [4:0] S_EXECUTE           = 5'd2;
    localparam [4:0] S_WAIT              = 5'd3;
    localparam [4:0] S_HALT              = 5'd4;
    localparam [4:0] S_LOAD_WAIT         = 5'd5;
    localparam [4:0] S_LOAD_DONE         = 5'd6;
    localparam [4:0] S_FB_CLEAR          = 5'd7;
    localparam [4:0] S_FB_RMW_WAIT       = 5'd8;
    localparam [4:0] S_FB_RMW_WRITE      = 5'd9;
    localparam [4:0] S_FB_PRESENT_HEADER = 5'd10;
    localparam [4:0] S_FB_PRESENT_WAIT1  = 5'd11;
    localparam [4:0] S_FB_PRESENT_WAIT2  = 5'd12;
    localparam [4:0] S_FB_PRESENT_PIXELS = 5'd13;
    localparam [4:0] S_FB_PRESENT_TX_DRAIN = 5'd14;

    reg [4:0] state;

    // -------------------------------------------------------------------------
    // Memories / registers
    // -------------------------------------------------------------------------

    reg [31:0] imem [0:1023];

    // 512 words gives 256 old general-purpose words plus two 64x64 1bpp buffers.
    // The synchronous port below is intentionally written in a BRAM-friendly style.
    reg [31:0] data_mem [0:511] /* synthesis syn_ramstyle = "block_ram" */;

    reg [31:0] gpr [0:31];
    reg bool_regs [0:7];
    reg bool_mem [0:127];

    reg [31:0] return_stack [0:15];
    reg [4:0] return_sp;

    reg [31:0] pc;
    reg [31:0] instr;
    reg [31:0] instr2;
    reg [31:0] wait_counter;

    reg [7:0] uart_rx_buf;
    reg uart_rx_pending;

    reg data_we;
    reg [8:0] data_rd_addr;
    reg [8:0] data_wr_addr;
    reg [31:0] data_wr_data;
    reg [31:0] data_rd_q;

    reg [4:0] load_dst_reg;

    reg [8:0] fb_base;
    reg [8:0] fb_addr;
    reg [6:0] fb_word_index;
    reg [4:0] fb_bit_index;
    reg [31:0] fb_word;
    reg [31:0] fb_bit_mask;
    reg fb_set_bit;
    reg [2:0] fb_header_index;
    reg fb_tx_kind;

    reg [8:0] addr9_work;
    reg [13:0] addr14_work;
    reg [31:0] addr32_work;
    reg [11:0] fb_pixel_work;
    reg [4:0] return_index_work;

    integer i;

    initial begin
        $readmemh("src/program.hex", imem);
    end

    // The bootloader writes program memory while the core is held in reset by top-level logic.
    always @(posedge clk) begin
        if (boot_we) begin
            imem[boot_addr] <= boot_data;
        end
    end

    // Synchronous data memory port. Do not reset data_mem here; resetting RAM arrays
    // generally prevents block RAM inference on small FPGAs.
    always @(posedge clk) begin
        if (data_we) begin
            data_mem[data_wr_addr] <= data_wr_data;
        end

        data_rd_q <= data_mem[data_rd_addr];
    end

    genvar gpio_i;
    generate
        for (gpio_i = 0; gpio_i < 128; gpio_i = gpio_i + 1) begin : gpio_assign
            assign gpio_out[gpio_i] = bool_mem[gpio_i];
        end
    endgenerate

    // -------------------------------------------------------------------------
    // Instruction fields
    // -------------------------------------------------------------------------

    wire [5:0] opcode;
    wire [4:0] rd_field;
    wire [4:0] rs_field;
    wire [4:0] rt_field;
    wire [6:0] funct;
    wire [3:0] pred_field;
    wire [11:0] i_imm;
    wire [3:0] ib_bd;
    wire [3:0] ib_bs;
    wire [13:0] ib_imm;
    wire [21:0] j_offset;
    wire [16:0] md_imm;

    assign opcode     = instr[31:26];
    assign rd_field   = instr[25:21];
    assign rs_field   = instr[20:16];
    assign rt_field   = instr[15:11];
    assign funct      = instr[10:4];
    assign pred_field = instr[3:0];
    assign i_imm      = instr[15:4];
    assign ib_bd      = instr[25:22];
    assign ib_bs      = instr[21:18];
    assign ib_imm     = instr[17:4];
    assign j_offset   = instr[25:4];
    assign md_imm     = instr[20:4];

    // -------------------------------------------------------------------------
    // Predication
    // -------------------------------------------------------------------------

    wire [2:0] pred_bool_idx;
    wire pred_polarity;
    wire pred_satisfied;

    assign pred_bool_idx = pred_field[2:0];
    assign pred_polarity = pred_field[3];
    assign pred_satisfied = (pred_field == 4'b1111)
        ? 1'b1
        : (bool_regs[pred_bool_idx] == ~pred_polarity);

    // -------------------------------------------------------------------------
    // Register helpers
    // -------------------------------------------------------------------------

    function [31:0] read_reg;
        input [4:0] num;
        begin
            case (num)
                5'd0:  read_reg = gpr[0];
                5'd1:  read_reg = gpr[1];
                5'd2:  read_reg = gpr[2];
                5'd3:  read_reg = gpr[3];
                5'd4:  read_reg = gpr[4];
                5'd5:  read_reg = gpr[5];
                5'd6:  read_reg = gpr[6];
                5'd7:  read_reg = gpr[7];
                5'd8:  read_reg = gpr[8];
                5'd9:  read_reg = gpr[9];
                5'd10: read_reg = gpr[10];
                5'd11: read_reg = gpr[11];
                5'd12: read_reg = gpr[12];
                5'd13: read_reg = gpr[13];
                5'd14: read_reg = gpr[14];
                5'd15: read_reg = gpr[15];
                5'd16: read_reg = gpr[16];
                5'd17: read_reg = gpr[17];
                5'd18: read_reg = gpr[18];
                5'd19: read_reg = gpr[19];
                5'd20: read_reg = gpr[20];
                5'd21: read_reg = gpr[21];
                5'd22: read_reg = gpr[22];
                5'd23: read_reg = gpr[23];
                5'd24: read_reg = gpr[24];
                5'd25: read_reg = gpr[25];
                5'd26: read_reg = gpr[26];
                5'd27: read_reg = gpr[27];
                5'd28: read_reg = gpr[28];
                5'd29: read_reg = gpr[29];
                5'd30: read_reg = gpr[30];
                5'd31: read_reg = gpr[31];
                default: read_reg = 32'h0000_0000;
            endcase
        end
    endfunction

    wire [31:0] rd_value;
    wire [31:0] rs_value;
    wire [31:0] rt_value;

    assign rd_value = read_reg(rd_field);
    assign rs_value = read_reg(rs_field);
    assign rt_value = read_reg(rt_field);

    function read_bool;
        input [3:0] num;
        begin
            case (num)
                4'd0: read_bool = bool_regs[0];
                4'd1: read_bool = bool_regs[1];
                4'd2: read_bool = bool_regs[2];
                4'd3: read_bool = bool_regs[3];
                4'd4: read_bool = bool_regs[4];
                4'd5: read_bool = bool_regs[5];
                4'd6: read_bool = bool_regs[6];
                4'd7: read_bool = bool_regs[7];
                4'd8: read_bool = 1'b0;
                4'd9: read_bool = 1'b1;
                default: read_bool = 1'b0;
            endcase
        end
    endfunction

    function read_bool_mem;
        input [13:0] addr;
        begin
            if (addr == UART_READY_BOOL_ADDR) begin
                read_bool_mem = uart_tx_ready;
            end else if (addr == UART_RX_READY_BOOL_ADDR) begin
                read_bool_mem = uart_rx_pending;
            end else if (addr < 14'd128) begin
                read_bool_mem = bool_mem[addr[6:0]];
            end else begin
                read_bool_mem = 1'b0;
            end
        end
    endfunction

    function [31:0] imul32;
        input [31:0] a;
        input [31:0] b;
        reg signed [31:0] sa;
        reg signed [31:0] sb;
        reg signed [63:0] prod;
        begin
            sa = a;
            sb = b;
            prod = sa * sb;
            imul32 = prod[31:0];
        end
    endfunction

    function [31:0] fmul_q7_25;
        input [31:0] a;
        input [31:0] b;
        reg signed [31:0] sa;
        reg signed [31:0] sb;
        reg signed [63:0] prod;
        reg signed [63:0] shifted;
        begin
            sa = a;
            sb = b;
            prod = sa * sb;
            shifted = prod >>> 25;
            fmul_q7_25 = shifted[31:0];
        end
    endfunction

    function [7:0] fb_header_byte;
        input [2:0] index;
        begin
            case (index)
                3'd0: fb_header_byte = 8'd65; // A
                3'd1: fb_header_byte = 8'd68; // D
                3'd2: fb_header_byte = 8'd73; // I
                3'd3: fb_header_byte = 8'd48; // 0
                3'd4: fb_header_byte = 8'd64; // width
                3'd5: fb_header_byte = 8'd64; // height
                default: fb_header_byte = 8'd0;
            endcase
        end
    endfunction

    // -------------------------------------------------------------------------
    // Main FSM
    // -------------------------------------------------------------------------

    always @(posedge clk) begin
        if (rst) begin
            pc <= 32'd0;
            state <= S_FETCH;
            wait_counter <= 32'd0;
            instr <= 32'd0;
            instr2 <= 32'd0;
            uart_tx_valid <= 1'b0;
            uart_tx_data <= 8'd0;
            uart_rx_buf <= 8'd0;
            uart_rx_pending <= 1'b0;
            return_sp <= 5'd0;
            data_we <= 1'b0;
            data_rd_addr <= 9'd0;
            data_wr_addr <= 9'd0;
            data_wr_data <= 32'd0;
            load_dst_reg <= 5'd0;
            fb_base <= 9'd0;
            fb_addr <= 9'd0;
            fb_word_index <= 7'd0;
            fb_bit_index <= 5'd0;
            fb_word <= 32'd0;
            fb_bit_mask <= 32'd0;
            fb_set_bit <= 1'b0;
            fb_header_index <= 3'd0;
            fb_tx_kind <= 1'b0;
            addr9_work <= 9'd0;
            addr14_work <= 14'd0;
            addr32_work <= 32'd0;
            fb_pixel_work <= 12'd0;
            return_index_work <= 5'd0;

            for (i = 0; i < 32; i = i + 1) begin
                gpr[i] <= 32'd0;
            end

            for (i = 0; i < 8; i = i + 1) begin
                bool_regs[i] <= 1'b0;
            end

            for (i = 0; i < 128; i = i + 1) begin
                bool_mem[i] <= 1'b0;
            end

            for (i = 0; i < 16; i = i + 1) begin
                return_stack[i] <= 32'd0;
            end
        end else begin
            uart_tx_valid <= 1'b0;
            data_we <= 1'b0;

            // UART RX has a one-byte buffer. If software does not read it quickly
            // enough, a newer byte overwrites the older byte by design.
            if (uart_rx_valid) begin
                uart_rx_buf <= uart_rx_data;
                uart_rx_pending <= 1'b1;
            end

            case (state)
                S_FETCH: begin
                    instr <= imem[pc[9:0]];
                    state <= S_EXECUTE;
                end

                S_EXECUTE: begin
                    if (!pred_satisfied) begin
                        if (opcode == OP_LOAD_L) begin
                            pc <= pc + 32'd2;
                        end else begin
                            pc <= pc + 32'd1;
                        end
                        state <= S_FETCH;
                    end else begin
                        case (opcode)
                            OP_NOP: begin
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_HALT: begin
                                state <= S_HALT;
                            end

                            OP_ALU_R: begin
                                if (rd_field <= 5'd31) begin
                                    case (funct)
                                        FUNCT_IADD: gpr[rd_field] <= rs_value + rt_value;
                                        FUNCT_FADD: gpr[rd_field] <= rs_value + rt_value;
                                        FUNCT_ISUB: gpr[rd_field] <= rs_value - rt_value;
                                        FUNCT_FSUB: gpr[rd_field] <= rs_value - rt_value;
                                        FUNCT_FABS: gpr[rd_field] <= (rs_value[31] ? (~rs_value + 32'd1) : rs_value);
                                        FUNCT_MOV:  gpr[rd_field] <= rs_value;
                                        FUNCT_IAND: gpr[rd_field] <= rs_value & rt_value;
                                        FUNCT_IOR:  gpr[rd_field] <= rs_value | rt_value;
                                        FUNCT_IXOR: gpr[rd_field] <= rs_value ^ rt_value;
                                        FUNCT_INOT: gpr[rd_field] <= ~rs_value;
                                        FUNCT_IMUL: gpr[rd_field] <= imul32(rs_value, rt_value);
                                        FUNCT_FMUL: gpr[rd_field] <= fmul_q7_25(rs_value, rt_value);
                                        FUNCT_ITOF: gpr[rd_field] <= rs_value << 25;
                                        FUNCT_FTOI: gpr[rd_field] <= $signed(rs_value) >>> 25;
                                        FUNCT_SHL:  gpr[rd_field] <= rs_value << rt_field;
                                        FUNCT_SHR:  gpr[rd_field] <= rs_value >> rt_field;
                                        FUNCT_SAR:  gpr[rd_field] <= $signed(rs_value) >>> rt_field;
                                        default: ;
                                    endcase
                                end
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_CMP_R: begin
                                if (rd_field <= 5'd7) begin
                                    case (funct)
                                        FUNCT_CMP_EQ: bool_regs[rd_field[2:0]] <= (rs_value == rt_value);
                                        FUNCT_CMP_NE: bool_regs[rd_field[2:0]] <= (rs_value != rt_value);
                                        FUNCT_CMP_LT: bool_regs[rd_field[2:0]] <= ($signed(rs_value) <  $signed(rt_value));
                                        FUNCT_CMP_LE: bool_regs[rd_field[2:0]] <= ($signed(rs_value) <= $signed(rt_value));
                                        FUNCT_CMP_GT: bool_regs[rd_field[2:0]] <= ($signed(rs_value) >  $signed(rt_value));
                                        FUNCT_CMP_GE: bool_regs[rd_field[2:0]] <= ($signed(rs_value) >= $signed(rt_value));
                                        default: ;
                                    endcase
                                end
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_LOAD_I: begin
                                if (rd_field <= 5'd31) begin
                                    gpr[rd_field] <= {{20{i_imm[11]}}, i_imm};
                                end
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_LOAD_L: begin
                                instr2 <= imem[pc[9:0] + 10'd1];
                                state <= S_FETCH2;
                            end

                            OP_LOAD_M: begin
                                if (rd_field <= 5'd31) begin
                                    addr32_work = rs_value + {{20{i_imm[11]}}, i_imm};
                                    addr9_work = addr32_work[8:0];

                                    if (addr9_work == UART_RX_ADDR) begin
                                        if (uart_rx_valid) begin
                                            gpr[rd_field] <= {24'd0, uart_rx_data};
                                        end else begin
                                            gpr[rd_field] <= {24'd0, uart_rx_buf};
                                        end
                                        uart_rx_pending <= 1'b0;
                                        pc <= pc + 32'd1;
                                        state <= S_FETCH;
                                    end else begin
                                        load_dst_reg <= rd_field;
                                        data_rd_addr <= addr9_work;
                                        state <= S_LOAD_WAIT;
                                    end
                                end else begin
                                    pc <= pc + 32'd1;
                                    state <= S_FETCH;
                                end
                            end

                            OP_SAVE_M: begin
                                addr32_work = rs_value + {{20{i_imm[11]}}, i_imm};
                                addr9_work = addr32_work[8:0];

                                if (addr9_work == UART_TX_ADDR) begin
                                    if (uart_tx_ready) begin
                                        uart_tx_data <= rd_value[7:0];
                                        uart_tx_valid <= 1'b1;
                                        pc <= pc + 32'd1;
                                        state <= S_FETCH;
                                    end else begin
                                        state <= S_EXECUTE;
                                    end
                                end else begin
                                    data_wr_addr <= addr9_work;
                                    data_wr_data <= rd_value;
                                    data_we <= 1'b1;
                                    pc <= pc + 32'd1;
                                    state <= S_FETCH;
                                end
                            end

                            OP_LOAD_MD: begin
                                if (rd_field <= 5'd31) begin
                                    addr9_work = md_imm[8:0];

                                    if (addr9_work == UART_RX_ADDR) begin
                                        if (uart_rx_valid) begin
                                            gpr[rd_field] <= {24'd0, uart_rx_data};
                                        end else begin
                                            gpr[rd_field] <= {24'd0, uart_rx_buf};
                                        end
                                        uart_rx_pending <= 1'b0;
                                        pc <= pc + 32'd1;
                                        state <= S_FETCH;
                                    end else begin
                                        load_dst_reg <= rd_field;
                                        data_rd_addr <= addr9_work;
                                        state <= S_LOAD_WAIT;
                                    end
                                end else begin
                                    pc <= pc + 32'd1;
                                    state <= S_FETCH;
                                end
                            end

                            OP_SAVE_MD: begin
                                addr9_work = md_imm[8:0];

                                if (addr9_work == UART_TX_ADDR) begin
                                    if (uart_tx_ready) begin
                                        uart_tx_data <= rd_value[7:0];
                                        uart_tx_valid <= 1'b1;
                                        pc <= pc + 32'd1;
                                        state <= S_FETCH;
                                    end else begin
                                        state <= S_EXECUTE;
                                    end
                                end else begin
                                    data_wr_addr <= addr9_work;
                                    data_wr_data <= rd_value;
                                    data_we <= 1'b1;
                                    pc <= pc + 32'd1;
                                    state <= S_FETCH;
                                end
                            end

                            OP_SAVE_BI: begin
                                if (ib_imm < 14'd128) begin
                                    bool_mem[ib_imm[6:0]] <= read_bool(ib_bs);
                                end
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_LOAD_BI: begin
                                if (ib_bd <= 4'd7) begin
                                    bool_regs[ib_bd[2:0]] <= read_bool_mem(ib_imm);
                                end
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_LOAD_BR: begin
                                if (rd_field <= 5'd7) begin
                                    addr32_work = rs_value;
                                    addr14_work = addr32_work[13:0];
                                    bool_regs[rd_field[2:0]] <= read_bool_mem(addr14_work);
                                end
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_SAVE_BR: begin
                                addr32_work = rs_value;
                                addr14_work = addr32_work[13:0];
                                if (addr14_work < 14'd128) begin
                                    bool_mem[addr14_work[6:0]] <= read_bool(rd_field[3:0]);
                                end
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_BOOL_R: begin
                                if (rd_field <= 5'd7) begin
                                    case (funct)
                                        FUNCT_BAND: bool_regs[rd_field[2:0]] <= read_bool(rs_field[3:0]) & read_bool(rt_field[3:0]);
                                        FUNCT_BOR:  bool_regs[rd_field[2:0]] <= read_bool(rs_field[3:0]) | read_bool(rt_field[3:0]);
                                        FUNCT_BXOR: bool_regs[rd_field[2:0]] <= read_bool(rs_field[3:0]) ^ read_bool(rt_field[3:0]);
                                        FUNCT_BNOT: bool_regs[rd_field[2:0]] <= ~read_bool(rs_field[3:0]);
                                        FUNCT_BMOV: bool_regs[rd_field[2:0]] <= read_bool(rs_field[3:0]);
                                        default: ;
                                    endcase
                                end
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_WAIT: begin
                                if (rs_value == 32'd0) begin
                                    pc <= pc + 32'd1;
                                    state <= S_FETCH;
                                end else begin
                                    wait_counter <= rs_value;
                                    state <= S_WAIT;
                                end
                            end

                            OP_FBCLEAR: begin
                                fb_base <= rd_value[8:0];
                                fb_word_index <= 7'd0;
                                state <= S_FB_CLEAR;
                            end

                            OP_FBPLOT: begin
                                if ((rs_value[31:6] != 26'd0) || (rt_value[31:6] != 26'd0)) begin
                                    pc <= pc + 32'd1;
                                    state <= S_FETCH;
                                end else begin
                                    fb_pixel_work = {rt_value[5:0], rs_value[5:0]};
                                    fb_addr <= rd_value[8:0] + {2'b00, fb_pixel_work[11:5]};
                                    fb_bit_mask <= 32'h0000_0001 << fb_pixel_work[4:0];
                                    fb_set_bit <= 1'b1;
                                    data_rd_addr <= rd_value[8:0] + {2'b00, fb_pixel_work[11:5]};
                                    state <= S_FB_RMW_WAIT;
                                end
                            end

                            OP_FBERASE: begin
                                if ((rs_value[31:6] != 26'd0) || (rt_value[31:6] != 26'd0)) begin
                                    pc <= pc + 32'd1;
                                    state <= S_FETCH;
                                end else begin
                                    fb_pixel_work = {rt_value[5:0], rs_value[5:0]};
                                    fb_addr <= rd_value[8:0] + {2'b00, fb_pixel_work[11:5]};
                                    fb_bit_mask <= 32'h0000_0001 << fb_pixel_work[4:0];
                                    fb_set_bit <= 1'b0;
                                    data_rd_addr <= rd_value[8:0] + {2'b00, fb_pixel_work[11:5]};
                                    state <= S_FB_RMW_WAIT;
                                end
                            end

                            OP_FBPRESENT: begin
                                fb_base <= rd_value[8:0];
                                fb_header_index <= 3'd0;
                                state <= S_FB_PRESENT_HEADER;
                            end

                            OP_JUMP: begin
                                pc <= pc + 32'd1 + {{10{j_offset[21]}}, j_offset};
                                state <= S_FETCH;
                            end

                            OP_CALL: begin
                                if (return_sp == 5'd16) begin
                                    state <= S_HALT;
                                end else begin
                                    return_stack[return_sp[3:0]] <= pc + 32'd1;
                                    return_sp <= return_sp + 5'd1;
                                    pc <= pc + 32'd1 + {{10{j_offset[21]}}, j_offset};
                                    state <= S_FETCH;
                                end
                            end

                            OP_RETURN: begin
                                if (return_sp == 5'd0) begin
                                    state <= S_HALT;
                                end else begin
                                    return_index_work = return_sp - 5'd1;
                                    return_sp <= return_index_work;
                                    pc <= return_stack[return_index_work[3:0]];
                                    state <= S_FETCH;
                                end
                            end

                            default: begin
                                pc <= pc + 32'd1;
                                state <= S_FETCH;
                            end
                        endcase
                    end
                end

                S_FETCH2: begin
                    if (rd_field <= 5'd31) begin
                        gpr[rd_field] <= instr2;
                    end
                    pc <= pc + 32'd2;
                    state <= S_FETCH;
                end

                S_LOAD_WAIT: begin
                    state <= S_LOAD_DONE;
                end

                S_LOAD_DONE: begin
                    if (load_dst_reg <= 5'd31) begin
                        gpr[load_dst_reg] <= data_rd_q;
                    end
                    pc <= pc + 32'd1;
                    state <= S_FETCH;
                end

                S_WAIT: begin
                    if (wait_counter == 32'd0) begin
                        pc <= pc + 32'd1;
                        state <= S_FETCH;
                    end else begin
                        wait_counter <= wait_counter - 32'd1;
                    end
                end

                S_FB_CLEAR: begin
                    data_wr_addr <= fb_base + {2'b00, fb_word_index};
                    data_wr_data <= 32'd0;
                    data_we <= 1'b1;

                    if (fb_word_index == 7'd127) begin
                        pc <= pc + 32'd1;
                        state <= S_FETCH;
                    end else begin
                        fb_word_index <= fb_word_index + 7'd1;
                    end
                end

                S_FB_RMW_WAIT: begin
                    state <= S_FB_RMW_WRITE;
                end

                S_FB_RMW_WRITE: begin
                    data_wr_addr <= fb_addr;
                    if (fb_set_bit) begin
                        data_wr_data <= data_rd_q | fb_bit_mask;
                    end else begin
                        data_wr_data <= data_rd_q & ~fb_bit_mask;
                    end
                    data_we <= 1'b1;
                    pc <= pc + 32'd1;
                    state <= S_FETCH;
                end

                S_FB_PRESENT_HEADER: begin
                    if (uart_tx_ready) begin
                        uart_tx_data <= fb_header_byte(fb_header_index);
                        uart_tx_valid <= 1'b1;
                        fb_tx_kind <= 1'b0;
                        state <= S_FB_PRESENT_TX_DRAIN;
                    end
                end

                S_FB_PRESENT_WAIT1: begin
                    state <= S_FB_PRESENT_WAIT2;
                end

                S_FB_PRESENT_WAIT2: begin
                    fb_word <= data_rd_q;
                    fb_bit_index <= 5'd0;
                    state <= S_FB_PRESENT_PIXELS;
                end

                S_FB_PRESENT_PIXELS: begin
                    if (uart_tx_ready) begin
                        if (fb_word[fb_bit_index]) begin
                            uart_tx_data <= 8'd48;
                        end else begin
                            uart_tx_data <= 8'd0;
                        end
                        uart_tx_valid <= 1'b1;
                        fb_tx_kind <= 1'b1;
                        state <= S_FB_PRESENT_TX_DRAIN;
                    end
                end

                S_FB_PRESENT_TX_DRAIN: begin
                    if (!uart_tx_ready) begin
                        if (!fb_tx_kind) begin
                            if (fb_header_index == 3'd5) begin
                                fb_word_index <= 7'd0;
                                fb_bit_index <= 5'd0;
                                data_rd_addr <= fb_base;
                                state <= S_FB_PRESENT_WAIT1;
                            end else begin
                                fb_header_index <= fb_header_index + 3'd1;
                                state <= S_FB_PRESENT_HEADER;
                            end
                        end else begin
                            if (fb_bit_index == 5'd31) begin
                                if (fb_word_index == 7'd127) begin
                                    pc <= pc + 32'd1;
                                    state <= S_FETCH;
                                end else begin
                                    fb_word_index <= fb_word_index + 7'd1;
                                    data_rd_addr <= fb_base + {2'b00, fb_word_index + 7'd1};
                                    state <= S_FB_PRESENT_WAIT1;
                                end
                            end else begin
                                fb_bit_index <= fb_bit_index + 5'd1;
                                state <= S_FB_PRESENT_PIXELS;
                            end
                        end
                    end
                end

                S_HALT: begin
                    state <= S_HALT;
                end

                default: begin
                    state <= S_FETCH;
                end
            endcase
        end
    end

endmodule
