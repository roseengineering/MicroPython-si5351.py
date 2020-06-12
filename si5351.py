
SI5351_I2C_ADDRESS_DEFAULT = 0x60

SI5351_CRYSTAL_LOAD_6PF    = (1<<6)
SI5351_CRYSTAL_LOAD_8PF    = (2<<6)
SI5351_CRYSTAL_LOAD_10PF   = (3<<6)

SI5351_CRYSTAL_FREQ_25MHZ  = 25000000
SI5351_CRYSTAL_FREQ_27MHZ  = 27000000

SI5351_MULTISYNTH_C_MAX    = 1048575
SI5351_CLKOUT_MIN_FREQ     = 4000

SI5351_REGISTER_16_CLK0_CONTROL                       = 16
SI5351_REGISTER_17_CLK1_CONTROL                       = 17
SI5351_REGISTER_18_CLK2_CONTROL                       = 18
SI5351_REGISTER_19_CLK3_CONTROL                       = 19
SI5351_REGISTER_20_CLK4_CONTROL                       = 20
SI5351_REGISTER_21_CLK5_CONTROL                       = 21
SI5351_REGISTER_22_CLK6_CONTROL                       = 22
SI5351_REGISTER_23_CLK7_CONTROL                       = 23

SI5351_REGISTER_42_MULTISYNTH0_PARAMETERS_1           = 42
SI5351_REGISTER_50_MULTISYNTH1_PARAMETERS_1           = 50
SI5351_REGISTER_58_MULTISYNTH2_PARAMETERS_1           = 58

SI5351_REGISTER_44_MULTISYNTH0_PARAMETERS_3           = 44
SI5351_REGISTER_52_MULTISYNTH1_PARAMETERS_3           = 52
SI5351_REGISTER_60_MULTISYNTH2_PARAMETERS_3           = 60

SI5351_REGISTER_3_OUTPUT_ENABLE_CONTROL               = 3
SI5351_REGISTER_177_PLL_RESET                         = 177
SI5351_REGISTER_183_CRYSTAL_INTERNAL_LOAD_CAPACITANCE = 183


class SI5351_I2C:

    PLL_A = 0
    PLL_B = 1

    R_DIV_1   = 0
    R_DIV_2   = 1
    R_DIV_4   = 2
    R_DIV_8   = 3
    R_DIV_16  = 4
    R_DIV_32  = 5
    R_DIV_64  = 6
    R_DIV_128 = 7


    def write8(self, register, value):
        self.i2c.writeto_mem(self.address, register, bytes([value]))


    def __init__(self, i2c, 
                 address=SI5351_I2C_ADDRESS_DEFAULT,
                 crystalFreq=SI5351_CRYSTAL_FREQ_25MHZ):
        load = SI5351_CRYSTAL_LOAD_10PF
        self.plla_freq   = 0
        self.pllb_freq   = 0
        self.address     = address
        self.i2c         = i2c
        self.crystalFreq = crystalFreq

        # disable all outputs setting CLKx_DIS high
        self.write8(SI5351_REGISTER_3_OUTPUT_ENABLE_CONTROL, 0xFF)

        # power down all output drivers
        self.write8(SI5351_REGISTER_16_CLK0_CONTROL, 0x80)
        self.write8(SI5351_REGISTER_17_CLK1_CONTROL, 0x80)
        self.write8(SI5351_REGISTER_18_CLK2_CONTROL, 0x80)
        self.write8(SI5351_REGISTER_19_CLK3_CONTROL, 0x80)
        self.write8(SI5351_REGISTER_20_CLK4_CONTROL, 0x80)
        self.write8(SI5351_REGISTER_21_CLK5_CONTROL, 0x80)
        self.write8(SI5351_REGISTER_22_CLK6_CONTROL, 0x80)
        self.write8(SI5351_REGISTER_23_CLK7_CONTROL, 0x80)

        # set the load capacitance for the XTAL
        self.write8(SI5351_REGISTER_183_CRYSTAL_INTERNAL_LOAD_CAPACITANCE, load)


    def setupPLL(self, pll, mult, num=0, denom=1):
        # @brief  Sets the multiplier for the specified PLL
        # @param  pll   The PLL to configure, which must be one of the following:
        #               - SI5351_PLL_A
        #               - SI5351_PLL_B
        # @param  mult  The PLL integer multiplier (must be between 15 and 90)
        # @param  num   The 20-bit numerator for fractional output (0..1,048,575).
        #               Set this to '0' for integer output.
        # @param  denom The 20-bit denominator for fractional output (1..1,048,575).
        #               Set this to '1' or higher to avoid divider by zero errors.
        # @section PLL Configuration
        #     fVCO is the PLL output, and must be between 600..900MHz, where:
        #     fVCO = fXTAL * (a+(b/c))
        #     fXTAL = the crystal input frequency
        #     a     = an integer between 15 and 90
        #     b     = the fractional numerator (0..1,048,575)
        #     c     = the fractional denominator (1..1,048,575)
        # @note Try to use integers whenever possible to avoid clock jitter
        #     (only use the a part, setting b to '0' and c to '1').
        #     See: http://www.silabs.com/Support%20Documents/TechnicalDocs/AN619.pdf
        #
        # Feedback Multisynth Divider Equation
        # where: a = mult, b = num and c = denom
        # P1[17:0] = 128 * mult + floor(128*(num/denom)) - 512
        # P2[19:0] = 128 * num - denom * floor(128*(num/denom))
        # P3[19:0] = denom

        # Set the main PLL config registers
        P1 = 128 * mult + int(128.0 * num / denom) - 512
        P2 = 128 * num - denom * int(128.0 * num / denom)
        P3 = denom

        # Get the appropriate starting point for the PLL registers
        baseaddr = 26 if pll == self.PLL_A else 34

        # The datasheet is a nightmare of typos and inconsistencies here!
        self.write8(baseaddr,     (P3 & 0x0000FF00) >> 8)
        self.write8(baseaddr + 1, (P3 & 0x000000FF))
        self.write8(baseaddr + 2, (P1 & 0x00030000) >> 16)
        self.write8(baseaddr + 3, (P1 & 0x0000FF00) >> 8)
        self.write8(baseaddr + 4, (P1 & 0x000000FF))
        self.write8(baseaddr + 5, ((P3 & 0x000F0000) >> 12) | ((P2 & 0x000F0000) >> 16) )
        self.write8(baseaddr + 6, (P2 & 0x0000FF00) >> 8)
        self.write8(baseaddr + 7, (P2 & 0x000000FF))

        # Reset both PLLs
        self.write8(SI5351_REGISTER_177_PLL_RESET, (1<<7) | (1<<5))

        # Store the frequency settings for use with the Multisynth helper
        fvco = int(self.crystalFreq * (mult + float(num) / denom))
        if pll == self.PLL_A:
            self.plla_freq = fvco
        else:
            self.pllb_freq = fvco


    def setupMultisynth(self, output, pll, div, num=0, denom=1):
        # @brief  Configures the Multisynth divider, which determines the
        #         output clock frequency based on the specified PLL input.
        # 
        # @param  output    The output channel to use (0..2)
        # @param  pll       The PLL input source to use, which must be one of:
        #                   - SI5351_PLL_A
        #                   - SI5351_PLL_B
        # @param  div       The integer divider for the Multisynth output.
        #                   If pure integer values are used, this value must
        #                   be one of:
        #                   - SI5351_MULTISYNTH_DIV_4
        #                   - SI5351_MULTISYNTH_DIV_6
        #                   - SI5351_MULTISYNTH_DIV_8
        #                   If fractional output is used, this value must be
        #                   between 8 and 900.
        # @param  num       The 20-bit numerator for fractional output
        #                   (0..1,048,575). Set this to '0' for integer output.
        # @param  denom     The 20-bit denominator for fractional output
        #                   (1..1,048,575). Set this to '1' or higher to
        #                   avoid divide by zero errors.
        # 
        # @section Output Clock Configuration
        # 
        # The multisynth dividers are applied to the specified PLL output,
        # and are used to reduce the PLL output to a valid range (500kHz
        # to 160MHz). The relationship can be seen in this formula, where
        # fVCO is the PLL output frequency and MSx is the multisynth
        # divider:
        #     fOUT = fVCO / MSx
        # Valid multisynth dividers are 4, 6, or 8 when using integers,
        # or any fractional values between 8 + 1/1,048,575 and 900 + 0/1
        # The following formula is used for the fractional mode divider:
        #     a + b / c
        # a = The integer value, which must be 4, 6 or 8 in integer mode (MSx_INT=1)
        #     or 8..900 in fractional mode (MSx_INT=0).
        # b = The fractional numerator (0..1,048,575)
        # c = The fractional denominator (1..1,048,575)
        # @note   Try to use integers whenever possible to avoid clock jitter
        # @note   For output frequencies > 150MHz, you must set the divider
        #         to 4 and adjust to PLL to generate the frequency (for example
        #         a PLL of 640 to generate a 160MHz output clock). This is not
        #         yet supported in the driver, which limits frequencies to
        #         500kHz .. 150MHz.
        # @note   For frequencies below 500kHz (down to 8kHz) Rx_DIV must be
        #         used, but this isn't currently implemented in the driver.
        #
        # Output Multisynth Divider Equations
        # where: a = div, b = num and c = denom
        # P1[17:0] = 128 * a + floor(128*(b/c)) - 512
        # P2[19:0] = 128 * b - c * floor(128*(b/c))
        # P3[19:0] = c

        # Set the main PLL config registers
        P1 = 128 * div + int(128.0 * num / denom) - 512
        P2 = 128 * num - denom * int(128.0 * num / denom)
        P3 = denom

        # Get the appropriate starting point for the PLL registers
        if output == 0: baseaddr = SI5351_REGISTER_42_MULTISYNTH0_PARAMETERS_1
        if output == 1: baseaddr = SI5351_REGISTER_50_MULTISYNTH1_PARAMETERS_1
        if output == 2: baseaddr = SI5351_REGISTER_58_MULTISYNTH2_PARAMETERS_1

        # Set the MSx config registers
        self.write8(baseaddr,   (P3 & 0x0000FF00) >> 8)
        self.write8(baseaddr + 1, (P3 & 0x000000FF))
        self.write8(baseaddr + 2, (P1 & 0x00030000) >> 16)	
        # ToDo: Add DIVBY4 (>150MHz) and R0 support (<500kHz) later
        self.write8(baseaddr + 3, (P1 & 0x0000FF00) >> 8)
        self.write8(baseaddr + 4, (P1 & 0x000000FF))
        self.write8(baseaddr + 5, ((P3 & 0x000F0000) >> 12) | ((P2 & 0x000F0000) >> 16) )
        self.write8(baseaddr + 6, (P2 & 0x0000FF00) >> 8)
        self.write8(baseaddr + 7, (P2 & 0x000000FF))

        # Configure the clk control and enable the output
        # 8mA drive strength, MS0 as CLK0 source, Clock not inverted, powered up
        clkControlReg = 0x0F
        if pll == self.PLL_B: clkControlReg |= (1 << 5)   # Uses PLLB 
        if num == 0: clkControlReg |= (1 << 6)            # Integer mode
        if output == 0: self.write8(SI5351_REGISTER_16_CLK0_CONTROL, clkControlReg)
        if output == 1: self.write8(SI5351_REGISTER_17_CLK1_CONTROL, clkControlReg)
        if output == 2: self.write8(SI5351_REGISTER_18_CLK2_CONTROL, clkControlReg)


    def setupRdiv(self, output, div):
        if output == 0: Rreg = SI5351_REGISTER_44_MULTISYNTH0_PARAMETERS_3
        if output == 1: Rreg = SI5351_REGISTER_52_MULTISYNTH1_PARAMETERS_3
        if output == 2: Rreg = SI5351_REGISTER_60_MULTISYNTH2_PARAMETERS_3
        return self.write8(Rreg, (div & 0x07) << 4)


    def enableOutputs(self, enabled):
        # Enabled desired outputs (see Register 3)
        val = 0x00 if enabled else 0xFF
        self.write8(SI5351_REGISTER_3_OUTPUT_ENABLE_CONTROL, val)


    def set_freq(self, output, pll, freq):
        r_div = self.R_DIV_1
        if (freq >= SI5351_CLKOUT_MIN_FREQ and 
            freq <  SI5351_CLKOUT_MIN_FREQ * 2):
            r_div = self.R_DIV_128
            freq *= 128
        elif (freq >= SI5351_CLKOUT_MIN_FREQ * 2 and 
              freq <  SI5351_CLKOUT_MIN_FREQ * 4):
            r_div = self.R_DIV_64
            freq *= 64
        elif (freq >= SI5351_CLKOUT_MIN_FREQ * 4 and 
              freq <  SI5351_CLKOUT_MIN_FREQ * 8):
            r_div = self.R_DIV_32
            freq *= 32
        elif (freq >= SI5351_CLKOUT_MIN_FREQ * 8 and 
              freq <  SI5351_CLKOUT_MIN_FREQ * 16):
            r_div = self.R_DIV_16
            freq *= 16
        elif (freq >= SI5351_CLKOUT_MIN_FREQ * 16 and
              freq <  SI5351_CLKOUT_MIN_FREQ * 32):
            r_div = self.R_DIV_8
            freq *= 8
        elif (freq >= SI5351_CLKOUT_MIN_FREQ * 32 and
              freq <  SI5351_CLKOUT_MIN_FREQ * 64):
            r_div = self.R_DIV_4
            freq *= 4
        elif (freq >= SI5351_CLKOUT_MIN_FREQ * 64 and
              freq <  SI5351_CLKOUT_MIN_FREQ * 128):
            r_div = self.R_DIV_2
            freq *= 2

        if pll == self.PLL_A:
            fvco = self.plla_freq
        else:
            fvco = self.pllb_freq

        div = fvco // freq
        num = fvco % freq
        denom = freq
        while denom > SI5351_MULTISYNTH_C_MAX:
           num //= 2
           denom //= 2

        self.setupMultisynth(output, pll, div, num, denom)
        self.setupRdiv(output, r_div)

