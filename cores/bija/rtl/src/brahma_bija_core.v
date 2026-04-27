// =============================================================================
// brahma_bija_core.v
// Rdzeń procesora Brahma-Bija — multicycle FSM.
//
// Wersja Verilog-2001 / Gowin-safe:
//   - bez logic / always_ff / always_comb / enum / int
//   - bez wymagania trybu SystemVerilog w Project Configuration
//   - CADD/CSUB/CMUL/CABS2 są makrami assemblera, RTL widzi tylko scalar ops
// =============================================================================

module brahma_bija_core (
    input  wire        clk,
    input  wire        rst,
    output wire [127:0] gpio_out,
    input  wire        uart_tx_ready,
    output reg         uart_tx_valid,
    output reg  [7:0]  uart_tx_data,
    input  wire        uart_rx_valid,
    input  wire [7:0]  uart_rx_data,

    input  wire        boot_we,
    input  wire [9:0]  boot_addr,
    input  wire [31:0] boot_data
);

    // -------------------------------------------------------------------------
    // Opcode
    // -------------------------------------------------------------------------
    localparam [5:0] OP_NOP      = 6'h00;
    localparam [5:0] OP_ALU_R    = 6'h01;
    localparam [5:0] OP_CMP_R    = 6'h02;
    localparam [5:0] OP_LOAD_I   = 6'h10;
    localparam [5:0] OP_LOAD_L   = 6'h11;
    localparam [5:0] OP_LOAD_M   = 6'h12;
    localparam [5:0] OP_SAVE_M   = 6'h13;
    localparam [5:0] OP_LOAD_MD  = 6'h14;
    localparam [5:0] OP_SAVE_MD  = 6'h15;
    localparam [5:0] OP_SAVE_BI  = 6'h20;
    localparam [5:0] OP_LOAD_BI  = 6'h21;
    localparam [5:0] OP_BOOL_R   = 6'h22;
    localparam [5:0] OP_LOAD_BR  = 6'h23;
    localparam [5:0] OP_SAVE_BR  = 6'h24;
    localparam [5:0] OP_WAIT     = 6'h30;
    localparam [5:0] OP_JUMP     = 6'h38;
    localparam [5:0] OP_HALT     = 6'h3F;

    localparam [7:0] UART_TX_ADDR = 8'hF0;
    localparam [7:0] UART_RX_ADDR = 8'hF1;
    localparam [13:0] UART_READY_BOOL_ADDR = 14'd128;
    localparam [13:0] UART_RX_READY_BOOL_ADDR = 14'd129;

    localparam [6:0] FUNCT_IADD   = 7'h00;
    localparam [6:0] FUNCT_ISUB   = 7'h01;
    localparam [6:0] FUNCT_IAND   = 7'h02;
    localparam [6:0] FUNCT_IOR    = 7'h03;
    localparam [6:0] FUNCT_IXOR   = 7'h04;
    localparam [6:0] FUNCT_SHL    = 7'h05;
    localparam [6:0] FUNCT_SHR    = 7'h06;
    localparam [6:0] FUNCT_SAR    = 7'h07;
    localparam [6:0] FUNCT_IMUL   = 7'h08;
    localparam [6:0] FUNCT_FMUL   = 7'h09;
    localparam [6:0] FUNCT_ITOF   = 7'h0A;
    localparam [6:0] FUNCT_FTOI   = 7'h0B;
    localparam [6:0] FUNCT_INOT   = 7'h0C;
    localparam [6:0] FUNCT_FADD   = 7'h0D;
    localparam [6:0] FUNCT_FSUB   = 7'h0E;
    localparam [6:0] FUNCT_FABS   = 7'h0F;
    localparam [6:0] FUNCT_MOV    = 7'h10;

    localparam [6:0] FUNCT_BAND   = 7'h00;
    localparam [6:0] FUNCT_BOR    = 7'h01;
    localparam [6:0] FUNCT_BXOR   = 7'h02;
    localparam [6:0] FUNCT_BNOT   = 7'h03;
    localparam [6:0] FUNCT_BMOV   = 7'h04;

    localparam [6:0] FUNCT_CMP_EQ = 7'h00;
    localparam [6:0] FUNCT_CMP_NE = 7'h01;
    localparam [6:0] FUNCT_CMP_LT = 7'h02;
    localparam [6:0] FUNCT_CMP_LE = 7'h03;
    localparam [6:0] FUNCT_CMP_GT = 7'h04;
    localparam [6:0] FUNCT_CMP_GE = 7'h05;

    // -------------------------------------------------------------------------
    // FSM states
    // -------------------------------------------------------------------------
    localparam [2:0] S_FETCH   = 3'd0;
    localparam [2:0] S_FETCH2  = 3'd1;
    localparam [2:0] S_EXECUTE = 3'd2;
    localparam [2:0] S_WAIT    = 3'd3;
    localparam [2:0] S_HALT    = 3'd4;

    reg [2:0] state;

    // -------------------------------------------------------------------------
    // Memories / registers
    // -------------------------------------------------------------------------
    reg [31:0] imem [0:1023];
    reg [31:0] data_mem [0:255];
    reg [31:0] gpr [0:31];
    reg        bool_regs [0:7];
    reg        bool_mem [0:127];

    reg [31:0] pc;
    reg [31:0] instr;
    reg [31:0] instr2;
    reg [31:0] wait_counter;
    reg [7:0]  uart_rx_buf;
    reg        uart_rx_pending;

    integer i;

    initial begin
        $readmemh("src/program.hex", imem);
    end

    // Bootloader zapisuje program RAM bez przebudowy bitstreamu.
    // Rdzeń jest w tym czasie trzymany w resecie przez top/bootloader.
    always @(posedge clk) begin
        if (boot_we) begin
            imem[boot_addr] <= boot_data;
        end
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
    wire [5:0]  opcode;
    wire [4:0]  rd_field;
    wire [4:0]  rs_field;
    wire [4:0]  rt_field;
    wire [6:0]  funct;
    wire [3:0]  pred_field;
    wire [11:0] i_imm;
    wire [3:0]  ib_bd;
    wire [3:0]  ib_bs;
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
    // Predykacja
    // -------------------------------------------------------------------------
    wire [2:0] pred_bool_idx;
    wire       pred_polarity;
    wire       pred_satisfied;

    assign pred_bool_idx = pred_field[2:0];
    assign pred_polarity = pred_field[3];
    assign pred_satisfied = (pred_field == 4'b1111) ? 1'b1 :
                            (bool_regs[pred_bool_idx] == ~pred_polarity);

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------
    function [31:0] read_reg;
        input [4:0] num;
        begin
            case (num)
                5'd0: read_reg = gpr[0];
                5'd1: read_reg = gpr[1];
                5'd2: read_reg = gpr[2];
                5'd3: read_reg = gpr[3];
                5'd4: read_reg = gpr[4];
                5'd5: read_reg = gpr[5];
                5'd6: read_reg = gpr[6];
                5'd7: read_reg = gpr[7];
                5'd8: read_reg = gpr[8];
                5'd9: read_reg = gpr[9];
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
                4'd8: read_bool = 1'b0; // FALSE / LOW / 0
                4'd9: read_bool = 1'b1; // TRUE / HIGH / 1
                default: read_bool = 1'b0;
            endcase
        end
    endfunction

    function [7:0] data_addr;
        input [4:0]  rs;
        input [11:0] imm;
        reg [31:0] tmp;
        begin
            tmp = read_reg(rs) + {{20{imm[11]}}, imm};
            data_addr = tmp[7:0];
        end
    endfunction

    function [13:0] bool_addr;
        input [4:0] rs;
        reg [31:0] tmp;
        begin
            tmp = read_reg(rs);
            bool_addr = tmp[13:0];
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

    reg [7:0]  addr8_work;
    reg [13:0] addr14_work;

    // -------------------------------------------------------------------------
    // Main FSM
    // -------------------------------------------------------------------------
    always @(posedge clk) begin
        if (rst) begin
            pc           <= 32'd0;
            state        <= S_FETCH;
            wait_counter <= 32'd0;
            instr        <= 32'd0;
            instr2       <= 32'd0;
            addr8_work   <= 8'd0;
            addr14_work  <= 14'd0;
            uart_tx_valid  <= 1'b0;
            uart_tx_data   <= 8'd0;
            uart_rx_buf    <= 8'd0;
            uart_rx_pending <= 1'b0;

            for (i = 0; i < 32; i = i + 1) begin
                gpr[i] <= 32'd0;
            end
            for (i = 0; i < 8; i = i + 1) begin
                bool_regs[i] <= 1'b0;
            end
            for (i = 0; i < 256; i = i + 1) begin
                data_mem[i] <= 32'd0;
            end
            for (i = 0; i < 128; i = i + 1) begin
                bool_mem[i] <= 1'b0;
            end
        end else begin
            uart_tx_valid <= 1'b0;

            // UART RX ma jednobajtowy bufor.
            // Jeśli program nie czyta @uart_rx wystarczająco szybko, nowy bajt
            // nadpisze poprzedni — proste i celowe na tym etapie.
            if (uart_rx_valid) begin
                uart_rx_buf     <= uart_rx_data;
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
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_HALT: begin
                                state <= S_HALT;
                            end

                            OP_ALU_R: begin
                                if (rd_field <= 5'd31) begin
                                    case (funct)
                                        FUNCT_IADD: gpr[rd_field] <= read_reg(rs_field) + read_reg(rt_field);
                                        FUNCT_FADD: gpr[rd_field] <= read_reg(rs_field) + read_reg(rt_field);
                                        FUNCT_ISUB: gpr[rd_field] <= read_reg(rs_field) - read_reg(rt_field);
                                        FUNCT_FSUB: gpr[rd_field] <= read_reg(rs_field) - read_reg(rt_field);
                                        FUNCT_FABS: gpr[rd_field] <= (read_reg(rs_field)[31] ? (~read_reg(rs_field) + 32'd1) : read_reg(rs_field));
                                        FUNCT_MOV:  gpr[rd_field] <= read_reg(rs_field);
                                        FUNCT_IAND: gpr[rd_field] <= read_reg(rs_field) & read_reg(rt_field);
                                        FUNCT_IOR:  gpr[rd_field] <= read_reg(rs_field) | read_reg(rt_field);
                                        FUNCT_IXOR: gpr[rd_field] <= read_reg(rs_field) ^ read_reg(rt_field);
                                        FUNCT_INOT: gpr[rd_field] <= ~read_reg(rs_field);
                                        FUNCT_IMUL: gpr[rd_field] <= imul32(read_reg(rs_field), read_reg(rt_field));
                                        FUNCT_FMUL: gpr[rd_field] <= fmul_q7_25(read_reg(rs_field), read_reg(rt_field));
                                        FUNCT_ITOF: gpr[rd_field] <= read_reg(rs_field) << 25;
                                        FUNCT_FTOI: gpr[rd_field] <= $signed(read_reg(rs_field)) >>> 25;
                                        FUNCT_SHL:  gpr[rd_field] <= read_reg(rs_field) << rt_field;
                                        FUNCT_SHR:  gpr[rd_field] <= read_reg(rs_field) >> rt_field;
                                        FUNCT_SAR:  gpr[rd_field] <= $signed(read_reg(rs_field)) >>> rt_field;
                                        default: ;
                                    endcase
                                end
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_CMP_R: begin
                                if (rd_field <= 5'd7) begin
                                    case (funct)
                                        FUNCT_CMP_EQ: bool_regs[rd_field[2:0]] <= (read_reg(rs_field) == read_reg(rt_field));
                                        FUNCT_CMP_NE: bool_regs[rd_field[2:0]] <= (read_reg(rs_field) != read_reg(rt_field));
                                        FUNCT_CMP_LT: bool_regs[rd_field[2:0]] <= ($signed(read_reg(rs_field)) <  $signed(read_reg(rt_field)));
                                        FUNCT_CMP_LE: bool_regs[rd_field[2:0]] <= ($signed(read_reg(rs_field)) <= $signed(read_reg(rt_field)));
                                        FUNCT_CMP_GT: bool_regs[rd_field[2:0]] <= ($signed(read_reg(rs_field)) >  $signed(read_reg(rt_field)));
                                        FUNCT_CMP_GE: bool_regs[rd_field[2:0]] <= ($signed(read_reg(rs_field)) >= $signed(read_reg(rt_field)));
                                        default: ;
                                    endcase
                                end
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_LOAD_I: begin
                                if (rd_field <= 5'd31) begin
                                    gpr[rd_field] <= {{20{i_imm[11]}}, i_imm};
                                end
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_LOAD_L: begin
                                instr2 <= imem[pc[9:0] + 10'd1];
                                state  <= S_FETCH2;
                            end

                            OP_LOAD_M: begin
                                if (rd_field <= 5'd31) begin
                                    addr8_work = data_addr(rs_field, i_imm);
                                    if (addr8_work == UART_RX_ADDR) begin
                                        if (uart_rx_valid) begin
                                            gpr[rd_field] <= {24'd0, uart_rx_data};
                                        end else begin
                                            gpr[rd_field] <= {24'd0, uart_rx_buf};
                                        end
                                        uart_rx_pending <= 1'b0;
                                    end else begin
                                        gpr[rd_field] <= data_mem[addr8_work];
                                    end
                                end
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_SAVE_M: begin
                                addr8_work = data_addr(rs_field, i_imm);
                                if (addr8_work == UART_TX_ADDR) begin
                                    if (uart_tx_ready) begin
                                        uart_tx_data  <= read_reg(rd_field);
                                        uart_tx_valid <= 1'b1;
                                        pc    <= pc + 32'd1;
                                        state <= S_FETCH;
                                    end else begin
                                        state <= S_EXECUTE;
                                    end
                                end else begin
                                    data_mem[addr8_work] <= read_reg(rd_field);
                                    pc    <= pc + 32'd1;
                                    state <= S_FETCH;
                                end
                            end

                            OP_LOAD_MD: begin
                                if (rd_field <= 5'd31) begin
                                    if (md_imm[7:0] == UART_RX_ADDR) begin
                                        if (uart_rx_valid) begin
                                            gpr[rd_field] <= {24'd0, uart_rx_data};
                                        end else begin
                                            gpr[rd_field] <= {24'd0, uart_rx_buf};
                                        end
                                        uart_rx_pending <= 1'b0;
                                    end else begin
                                        gpr[rd_field] <= data_mem[md_imm[7:0]];
                                    end
                                end
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_SAVE_MD: begin
                                addr8_work = md_imm[7:0];
                                if (addr8_work == UART_TX_ADDR) begin
                                    if (uart_tx_ready) begin
                                        uart_tx_data  <= read_reg(rd_field);
                                        uart_tx_valid <= 1'b1;
                                        pc    <= pc + 32'd1;
                                        state <= S_FETCH;
                                    end else begin
                                        state <= S_EXECUTE;
                                    end
                                end else begin
                                    data_mem[addr8_work] <= read_reg(rd_field);
                                    pc    <= pc + 32'd1;
                                    state <= S_FETCH;
                                end
                            end

                            OP_SAVE_BI: begin
                                if (ib_imm < 14'd128) begin
                                    bool_mem[ib_imm[6:0]] <= read_bool(ib_bs);
                                end
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_LOAD_BI: begin
                                if (ib_bd <= 4'd7) begin
                                    bool_regs[ib_bd[2:0]] <= read_bool_mem(ib_imm);
                                end
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_LOAD_BR: begin
                                if (rd_field <= 5'd7) begin
                                    addr14_work = bool_addr(rs_field);
                                    bool_regs[rd_field[2:0]] <= read_bool_mem(addr14_work);
                                end
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_SAVE_BR: begin
                                addr14_work = bool_addr(rs_field);
                                if (addr14_work < 14'd128) begin
                                    bool_mem[addr14_work[6:0]] <= read_bool(rd_field[3:0]);
                                end
                                pc    <= pc + 32'd1;
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
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end

                            OP_WAIT: begin
                                if (read_reg(rs_field) == 32'd0) begin
                                    pc    <= pc + 32'd1;
                                    state <= S_FETCH;
                                end else begin
                                    wait_counter <= read_reg(rs_field);
                                    state        <= S_WAIT;
                                end
                            end

                            OP_JUMP: begin
                                pc    <= pc + 32'd1 + {{10{j_offset[21]}}, j_offset};
                                state <= S_FETCH;
                            end

                            default: begin
                                pc    <= pc + 32'd1;
                                state <= S_FETCH;
                            end
                        endcase
                    end
                end

                S_FETCH2: begin
                    if (rd_field <= 5'd31) begin
                        gpr[rd_field] <= instr2;
                    end
                    pc    <= pc + 32'd2;
                    state <= S_FETCH;
                end

                S_WAIT: begin
                    if (wait_counter == 32'd0) begin
                        pc    <= pc + 32'd1;
                        state <= S_FETCH;
                    end else begin
                        wait_counter <= wait_counter - 32'd1;
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
