# debug.py
# Debug printing utilities for G27 Shifter → Fanatec Adapter

from time import time

class ShifterDebugger:
    """Handles all debug output for the shifter adapter"""
    
    def __init__(self, enabled=True, interval=1.0):
        self.enabled = enabled
        self.interval = interval
        self.last_debug_time = 0
        self.last_gear = -1
    
    def should_print(self, current_gear):
        """Determine if we should print debug info based on time interval or gear change"""
        current_time = time()
        
        if not self.enabled:
            return False
        
        if current_time - self.last_debug_time >= self.interval or current_gear != self.last_gear:
            self.last_debug_time = current_time
            self.last_gear = current_gear
            return True
        
        return False
    
    def print_header(self):
        """Print startup header"""
        print("=" * 70)
        print("G27 Shifter → Fanatec Wheelbase Adapter")
        print("ESP32-S2 Mini")
        print(f"Debug mode: ON (interval: {self.interval}s)")
        print("=" * 70)
    
    def print_shifter_input(self, x, y, reverse_button, shifter_x_12, shifter_x_56,
                           shifter_y_neutral_min, shifter_y_neutral_max,
                           shifter_y_135_zone, shifter_y_246r_zone):
        """Print shifter input values"""
        print(f"G27 Input:")
        print(f"  X Pot:          {x:4d} (L: {shifter_x_12:3d}, R: {shifter_x_56:3d})")
        print(f"  Y Pot:          {y:4d} (N: {shifter_y_neutral_min:3d}-{shifter_y_neutral_max:3d}, "
              f"U: {shifter_y_135_zone:3d}, L: {shifter_y_246r_zone:3d})")
        print(f"  Reverse Button: {'PRESSED' if reverse_button else 'released'}")
    
    def print_sequential_output(self, gear, gear_to_string_func):
        """Print sequential mode output"""
        if gear == 3:
            button_state = "Shift DOWN (Pin 4 LOW)"
        elif gear == 4:
            button_state = "Shift UP (Pin 5 LOW)"
        else:
            button_state = "Both buttons released"
        
        print(f"\nMode Switch:    Sequential")
        print(f"Current Gear:   {gear} ({gear_to_string_func(gear)})")
        print(f"\nFanatec Output (Sequential):")
        print(f"  Pin 2 (Mode):   HIGH (Sequential)")
        print(f"  {button_state}")
    
    def print_hpattern_output(self, gear, x_dac, y_dac, gear_to_string_func):
        """Print H-pattern mode output"""
        # Decode Y axis state
        if y_dac == 255:
            y_state = "VCC (forward)"
        elif y_dac == 128:
            y_state = "VCC/2 (center)"
        elif y_dac == 0:
            y_state = "0V (backward)"
        else:
            y_state = f"{y_dac} (0-255)"
        
        print(f"\nMode Switch:    H-pattern")
        print(f"Current Gear:   {gear} ({gear_to_string_func(gear)})")
        print(f"\nFanatec Output (H-pattern):")
        print(f"  Pin 2 (Mode):   LOW (H-pattern)")
        print(f"  Pin 4 (X):      {x_dac} (0-255)")
        print(f"  Pin 5 (Y):      {y_dac} ({y_state})")
    
    def print_debug(self, x, y, reverse_button, gear, sequential_mode_selected, x_dac, y_dac,
                   shifter_x_12, shifter_x_56, shifter_y_neutral_min, shifter_y_neutral_max,
                   shifter_y_135_zone, shifter_y_246r_zone, gear_to_string_func):
        """Print complete debug information"""
        if not self.should_print(gear):
            return
        
        print("=" * 70)
        self.print_shifter_input(x, y, reverse_button, shifter_x_12, shifter_x_56,
                                shifter_y_neutral_min, shifter_y_neutral_max,
                                shifter_y_135_zone, shifter_y_246r_zone)
        
        if sequential_mode_selected:
            self.print_sequential_output(gear, gear_to_string_func)
        else:
            self.print_hpattern_output(gear, x_dac, y_dac, gear_to_string_func)
        
        print("=" * 70)