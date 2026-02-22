# g27_shifter_gpio.py
# ESP32-S2 Mini specific pin configuration
# With DAC output for Fanatec RJ12 interface

from machine import Pin, ADC, DAC
from time import sleep_us
from debug import ShifterDebugger

# SHIFTER INPUT PINS (from G27 shifter via level shifter)
SHIFTER_CLOCK_PIN = Pin(3, Pin.OUT)
SHIFTER_DATA_PIN = Pin(4, Pin.IN)
SHIFTER_MODE_PIN = Pin(5, Pin.OUT)
SHIFTER_X_PIN = ADC(Pin(8), atten=ADC.ATTN_11DB)
SHIFTER_Y_PIN = ADC(Pin(9), atten=ADC.ATTN_11DB)

# FANATEC OUTPUT PINS (to RJ12 connector for wheelbase)
FANATEC_MODE_PIN = Pin(6, Pin.OUT)      # RJ12 Pin 2: LOW=H-pattern, HIGH=sequential
FANATEC_X_DAC = DAC(Pin(17))            # RJ12 Pin 4: X axis (H-pattern) or shift down (sequential)
FANATEC_Y_DAC = DAC(Pin(18))            # RJ12 Pin 5: Y axis (H-pattern) or shift up (sequential)

# MODE SELECTION PIN
MODE_SWITCH_PIN = Pin(21, Pin.IN, Pin.PULL_UP)  # Physical switch for H-pattern/Sequential selection

# BUTTON DEFINITIONS
BUTTON_REVERSE = 1

# MISC.
SIGNAL_SETTLE_DELAY = 10  # microseconds

# HARDCODED CALIBRATION VALUES (12-bit: 0-4095)
SHIFTER_Y_NEUTRAL_MIN = 1640
SHIFTER_Y_NEUTRAL_MAX = 2456
SHIFTER_Y_246R_ZONE = 680
SHIFTER_Y_135_ZONE = 3416
SHIFTER_X_12 = 1364
SHIFTER_X_56 = 2728

# DEBUG SETTINGS
DEBUG = True
DEBUG_INTERVAL = 1.0  # seconds between debug prints

# Fanatec calibration values (12-bit: 0-4095)
# Converted to 8-bit DAC values (0-255): divide by 4095 * 255
FANATEC_GATE_R_DAC = 210        # 3340 → 210 (Reverse X position)
FANATEC_GATE_12_DAC = 169       # 2690 → 169
FANATEC_GATE_34_DAC = 125       # 2000 → 125
FANATEC_GATE_56_DAC = 77        # 1230 → 77

FANATEC_GATE_R1357_DAC = 255    # 4000 → 255 (VCC - forward)
FANATEC_GATE_246_DAC = 0        # 0 → 0 (0V - backward)
FANATEC_GATE_CENTER_DAC = 128   # ~2000 → 128 (VCC/2 - center/neutral)

# Sequential mode button values (active-low)
FANATEC_BUTTON_PRESSED = 0      # LOW = button active
FANATEC_BUTTON_RELEASED = 255   # HIGH = button inactive

# Fanatec gear mapping: maps gear number to (X_DAC_8bit, Y_DAC_8bit)
FANATEC_GEAR_MAP = {
    0: (FANATEC_GATE_34_DAC, FANATEC_GATE_CENTER_DAC),           # Neutral: center-center
    1: (FANATEC_GATE_12_DAC, FANATEC_GATE_R1357_DAC),            # Gear 1: left-forward
    2: (FANATEC_GATE_12_DAC, FANATEC_GATE_246_DAC),              # Gear 2: left-backward
    3: (FANATEC_GATE_34_DAC, FANATEC_GATE_R1357_DAC),            # Gear 3: center-forward (shift down)
    4: (FANATEC_GATE_34_DAC, FANATEC_GATE_246_DAC),              # Gear 4: center-backward (shift up)
    5: (FANATEC_GATE_56_DAC, FANATEC_GATE_R1357_DAC),            # Gear 5: right-forward
    6: (FANATEC_GATE_56_DAC, FANATEC_GATE_246_DAC),              # Gear 6: right-backward
    7: (FANATEC_GATE_R_DAC, FANATEC_GATE_R1357_DAC),             # Reverse: R position-forward
}

# Initialize debugger
debugger = ShifterDebugger(DEBUG, DEBUG_INTERVAL)

def wait_for_signal_settle():
    sleep_us(SIGNAL_SETTLE_DELAY)

def read_reverse_button():
    """Read all 16 button states from shift register, return reverse button (bit 1)"""
    SHIFTER_MODE_PIN.value(0)
    wait_for_signal_settle()
    SHIFTER_MODE_PIN.value(1)
    wait_for_signal_settle()
    
    button_states = [0] * 16

    for i in range(16):
        SHIFTER_CLOCK_PIN.value(0)
        wait_for_signal_settle()
        
        button_states[i] = SHIFTER_DATA_PIN.value()
        
        SHIFTER_CLOCK_PIN.value(1)
        wait_for_signal_settle()
    
    reverse_button = button_states[BUTTON_REVERSE]
    
    return reverse_button

def read_mode_switch():
    """Read physical mode switch (pulled up)
    Returns False for H-pattern (switch LOW), True for Sequential (switch HIGH)
    """
    return MODE_SWITCH_PIN.value() == 0

def get_shifter_position():
    """Read X and Y potentiometer values"""
    x = SHIFTER_X_PIN.read()
    y = SHIFTER_Y_PIN.read()
    return [x, y]

def get_current_gear(x, y, reverse_button):
    """Determine gear from X/Y position and reverse button"""
    # Neutral
    if SHIFTER_Y_NEUTRAL_MIN < y < SHIFTER_Y_NEUTRAL_MAX:
        return 0
    
    # Upper gate (1, 3, 5)
    if y > SHIFTER_Y_135_ZONE:
        if x <= SHIFTER_X_12:
            return 1
        elif x >= SHIFTER_X_56:
            return 5
        else:
            return 3
    
    # Lower gate (2, 4, 6/Reverse)
    if y < SHIFTER_Y_246R_ZONE:
        if x <= SHIFTER_X_12:
            return 2
        elif x >= SHIFTER_X_56:
            return 7 if reverse_button else 6
        else:
            return 4
    
    return 0

def gear_to_string(gear):
    """Convert gear number to readable string"""
    gear_names = {
        0: "Neutral",
        1: "Gear 1",
        2: "Gear 2",
        3: "Gear 3",
        4: "Gear 4",
        5: "Gear 5",
        6: "Gear 6",
        7: "Reverse"
    }
    return gear_names.get(gear, "Unknown")

def output_gear_to_fanatec(gear, mode):
    """
    Output gear to Fanatec wheelbase via RJ12
    
    RJ12 Pinout:
    Pin 1: GND
    Pin 2: Mode (LOW=H-pattern, HIGH=sequential)
    Pin 3: Shorted to Pin 2
    Pin 4: X axis (H-pattern) or shift down button (sequential)
    Pin 5: Y axis (H-pattern) or shift up button (sequential)
    Pin 6: VCC
    
    H-pattern behavior:
    - Pin 2: LOW
    - Pin 4: X axis angle (0-255 DAC)
    - Pin 5: VCC if forward, VCC/2 if center, 0 if backward
    
    Sequential behavior:
    - Pin 2: HIGH
    - Pin 4: LOW if lever is pushed forward (shift down)
    - Pin 5: LOW if lever is pulled backward (shift up)
    """
    
    # Set mode pin based on mode switch
    FANATEC_MODE_PIN.value(1 if mode else 0)
    
    if mode:
        # Sequential mode: output as shift buttons (active-low)
        if gear == 3:
            # Gear 3 position (forward/push) = Shift DOWN
            FANATEC_X_DAC.write(FANATEC_BUTTON_PRESSED)
            FANATEC_Y_DAC.write(FANATEC_BUTTON_RELEASED)
        elif gear == 4:
            # Gear 4 position (backward/pull) = Shift UP
            FANATEC_X_DAC.write(FANATEC_BUTTON_RELEASED)
            FANATEC_Y_DAC.write(FANATEC_BUTTON_PRESSED)
        else:
            # Neutral or other positions = both buttons released
            FANATEC_X_DAC.write(FANATEC_BUTTON_RELEASED)
            FANATEC_Y_DAC.write(FANATEC_BUTTON_RELEASED)
    else:
        # H-pattern mode: output gear position
        if gear in FANATEC_GEAR_MAP:
            x_dac, y_dac = FANATEC_GEAR_MAP[gear]
        else:
            x_dac, y_dac = FANATEC_GEAR_MAP[0]
        
        # Output X and Y axes via DAC (8-bit: 0-255)
        FANATEC_X_DAC.write(x_dac)
        FANATEC_Y_DAC.write(y_dac)

def setup():
    """Initialize GPIO pins"""
    SHIFTER_MODE_PIN.value(1)
    SHIFTER_CLOCK_PIN.value(1)
    FANATEC_MODE_PIN.value(0)
    
    if DEBUG:
        debugger.print_header()

def main():
    """Main loop"""
    setup()
    
    while True:
        # Get shifter position
        shifter_position = get_shifter_position()
        x = shifter_position[0]
        y = shifter_position[1]
        
        # Get reverse button state
        reverse_button = read_reverse_button()
        
        # Read mode switch
        mode = read_mode_switch()
        
        # Determine current gear
        gear = get_current_gear(x, y, reverse_button)
        
        # Output to Fanatec wheel interface
        output_gear_to_fanatec(gear, mode)
        
        # Get DAC values for debug output
        if gear in FANATEC_GEAR_MAP:
            x_dac, y_dac = FANATEC_GEAR_MAP[gear]
        else:
            x_dac, y_dac = FANATEC_GEAR_MAP[0]
        
        # Debug output
        if DEBUG:
            debugger.print_debug(
                x, y, reverse_button, gear, mode, x_dac, y_dac,
                SHIFTER_X_12, SHIFTER_X_56, SHIFTER_Y_NEUTRAL_MIN, SHIFTER_Y_NEUTRAL_MAX,
                SHIFTER_Y_135_ZONE, SHIFTER_Y_246R_ZONE, gear_to_string
            )

if __name__ == "__main__":
    main()