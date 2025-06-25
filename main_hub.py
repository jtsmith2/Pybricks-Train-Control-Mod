"""
LEGO Motor Control System
Uses https://code.pybricks.com/ with LEGO City hub and remote control
Connect 1 or 2 motors of any kind to Port A and/or B
"""

from pybricks.parameters import Color, Port, Stop, Button
from pybricks.pupdevices import DCMotor, Motor, Remote, Light
from pybricks.hubs import CityHub
from pybricks.tools import wait, StopWatch
from pybricks.iodevices import PUPDevice
from uerrno import ENODEV


class DeviceType:
    """Supported device types"""
    MOTOR = "Motor"
    DC_MOTOR = "DCMotor"
    LIGHT = "Light"
    UNKNOWN = "Unknown"
    NOT_CONNECTED = "NotConnected"


class ButtonAction:
    """Remote control button actions"""
    A_PLUS = "A+"
    A_MINUS = "A-"
    A_STOP = "A0"
    B_PLUS = "B+"
    B_MINUS = "B-"
    B_STOP = "B0"
    CENTER = "CENTER"


class MotorProfile:
    """Motor speed profile configuration"""
    
    def __init__(self, min_speed=20, max_speed=100, acceleration_step=10, acceleration_delay=100):
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.acceleration_step = acceleration_step
        self.acceleration_delay = acceleration_delay  # in milliseconds


class SpeedLEDConfig:
    """LED color configuration based on speed"""
    
    def __init__(self, stopped=None, slow=None, medium=None, fast=None, 
                 profile_indicator=None, slow_threshold=30, medium_threshold=60, 
                 blink_interval_ms=500):
        self.stopped = stopped if stopped is not None else Color.WHITE * 0.2
        self.slow = slow if slow is not None else Color.YELLOW * 0.5
        self.medium = medium if medium is not None else Color.ORANGE * 0.5
        self.fast = fast if fast is not None else Color.RED * 0.7
        self.profile_indicator = profile_indicator  # Color to blink with when stopped (None = use fast color)
        
        # Speed thresholds (as percentage of max speed)
        self.slow_threshold = slow_threshold  # Below this = slow color
        self.medium_threshold = medium_threshold  # Below this = medium color
        # Above medium_threshold = fast color
        
        # Blinking settings when stopped
        self.blink_interval_ms = blink_interval_ms  # How fast to blink (milliseconds)


class Configuration:
    """System configuration"""
    
    def __init__(self):
        # Motor profiles
        self.profile_a = MotorProfile(20, 100, 10, 100)
        self.profile_b = MotorProfile(10, 500, 5, 200)
        
        # Motor directions
        self.motor_a_direction = 1
        self.motor_b_direction = -1
        
        # Behavior settings
        self.auto_acceleration = True
        self.watchdog_enabled = False
        self.should_broadcast = True
        
        # Connection settings
        self.remote_timeout = 10  # seconds
        self.remote_name = ""
        self.broadcast_channel = 1
        
        # Lighting
        self.initial_light_value = 0
        
        # Button mappings
        self.button_mapping = {
            'UP': ButtonAction.A_PLUS,
            'DOWN': ButtonAction.A_MINUS,
            'STOP': ButtonAction.A_STOP,
            'SWITCH': ButtonAction.CENTER,
            'B_UP': ButtonAction.B_PLUS,
            'B_DOWN': ButtonAction.B_MINUS,
            'B_STOP': ButtonAction.B_STOP,
        }
        
        # LED colors - connection status
        self.led_connected = Color.GREEN * 0.3
        self.led_not_connected = Color.RED * 0.5
        
        # Speed-based LED colors for each profile
        self.led_speed_profile_a = SpeedLEDConfig(
            profile_indicator=Color.GREEN * 0.6  # Blinks green when stopped
        )
        self.led_speed_profile_b = SpeedLEDConfig(
            stopped=Color.WHITE * 0.2,
            slow=Color.BLUE * 0.5,
            medium=Color.MAGENTA * 0.5,
            fast=Color.VIOLET * 0.7,
            profile_indicator=Color.RED * 0.6,  # Blinks red when stopped
            slow_threshold=20,
            medium_threshold=50
        )
        
        # Enable speed-based LED colors
        self.use_speed_based_leds = True
        
        # Enable profile indication when stopped
        self.blink_profile_when_stopped = True


class Timer:
    """Timer utility class"""
    
    def __init__(self, timer_id: int):
        self.id = timer_id
        self.target_time = 0
        self.stopwatch = StopWatch()
        self.active = False
        
    def start(self, duration_ms: int) -> None:
        """Start timer for specified duration"""
        if not self.active:
            self.active = True
            self.stopwatch.reset()
            self.target_time = duration_ms
            
    def check(self) -> bool:
        """Check if timer has elapsed"""
        if self.active and self.stopwatch.time() > self.target_time:
            self.active = False
            self.target_time = 0
            return True
        return False
        
    def reset(self) -> None:
        """Reset timer"""
        self.active = False
        self.target_time = 0


class MotorDevice:
    """Represents a connected motor or device"""
    
    # Device ID mappings
    DEVICE_NAMES = {
        1: "Wedo 2.0 DC Motor",
        2: "Train DC Motor",
        8: "Light",
        38: "BOOST Interactive Motor",
        46: "Technic Large Motor",
        47: "Technic Extra Large Motor",
        48: "SPIKE Medium Angular Motor",
        49: "SPIKE Large Angular Motor",
        75: "Technic Medium Angular Motor",
        76: "Technic Large Angular Motor",
    }
    
    # Max speeds for different motor types
    MAX_SPEEDS = {
        38: 1530, 46: 1890, 47: 1980, 48: 1367,
        49: 1278, 75: 1367, 76: 1278
    }
    
    def __init__(self, port, direction):
        self.port = port
        self.direction = direction
        self.device_type = DeviceType.NOT_CONNECTED
        self.max_speed = 1000
        self.device_object = None
        
    def detect_and_initialize(self):
        """Detect connected device and initialize it"""
        try:
            device = PUPDevice(self.port)
        except OSError as ex:
            if ex.args[0] == ENODEV:
                self.device_type = DeviceType.NOT_CONNECTED
                return self.device_type
            raise
            
        device_id = device.info()['id']
        device_name = self.DEVICE_NAMES.get(device_id, f"Unknown device ID {device_id}")
        
        print(f"{self.port}: {device_name}")
        
        if device_id in self.DEVICE_NAMES:
            if "Motor" in device_name and "DC" not in device_name:
                self._initialize_servo_motor(device_id)
            elif "DC" in device_name:
                self._initialize_dc_motor()
            elif "Light" in device_name:
                self._initialize_light()
            else:
                self.device_type = DeviceType.UNKNOWN
        else:
            self.device_type = DeviceType.UNKNOWN
            
        return self.device_type
        
    def _initialize_servo_motor(self, device_id):
        """Initialize servo motor with proper speed limits"""
        self.device_type = DeviceType.MOTOR
        self.device_object = Motor(self.port)
        
        max_speed = self.MAX_SPEEDS.get(device_id, 1000)
        self.max_speed = int(max_speed * 0.9)  # 90% of max for safety
        
        self.device_object.stop()
        self.device_object.control.limits(speed=max_speed, acceleration=10000)
        
    def _initialize_dc_motor(self):
        """Initialize DC motor"""
        self.device_type = DeviceType.DC_MOTOR
        self.device_object = DCMotor(self.port)
        
    def _initialize_light(self):
        """Initialize light device"""
        self.device_type = DeviceType.LIGHT
        self.device_object = Light(self.port)
        
    def set_speed(self, speed):
        """Set motor speed based on device type"""
        if not self.device_object:
            return
            
        actual_speed = speed * self.direction
        
        if self.device_type == DeviceType.MOTOR:
            if speed == 0:
                self.device_object.stop()
            else:
                self.device_object.run(actual_speed * self.max_speed / 100)
                
        elif self.device_type == DeviceType.DC_MOTOR:
            if speed == 0:
                self.device_object.stop()
            else:
                self.device_object.dc(actual_speed)
                
    def set_light_brightness(self, brightness):
        """Set light brightness (0-100)"""
        if self.device_type == DeviceType.LIGHT and self.device_object:
            if brightness == 0:
                self.device_object.off()
            else:
                self.device_object.on(brightness)


class RemoteController:
    """Handles remote control interactions"""
    
    BUTTON_MAP = {
        ButtonAction.A_PLUS: Button.LEFT_PLUS,
        ButtonAction.A_MINUS: Button.LEFT_MINUS,
        ButtonAction.A_STOP: Button.LEFT,
        ButtonAction.B_PLUS: Button.RIGHT_PLUS,
        ButtonAction.B_MINUS: Button.RIGHT_MINUS,
        ButtonAction.B_STOP: Button.RIGHT,
        ButtonAction.CENTER: Button.CENTER,
    }
    
    def __init__(self, config):
        self.config = config
        self.remote = None
        self.connected = False
        
    def connect(self):
        """Attempt to connect to remote"""
        try:
            self.remote = Remote(
                name=self.config.remote_name,
                timeout=self.config.remote_timeout * 1000
            )
            self.connected = True
            return True
        except OSError:
            self.connected = False
            return False
            
    def reconnect(self):
        """Attempt to reconnect to remote"""
        try:
            self.remote = Remote(timeout=1000)
            self.connected = True
            return True
        except OSError:
            self.connected = False
            return False
            
    def is_button_pressed(self, action):
        """Check if specific button is pressed"""
        if not self.connected or not self.remote:
            return False
            
        try:
            pressed_buttons = self.remote.buttons.pressed()
            target_button = self.BUTTON_MAP.get(action)
            return target_button in pressed_buttons
        except OSError:
            self.connected = False
            return False
            
    def set_led(self, color):
        """Set remote LED color"""
        if self.connected and self.remote:
            self.remote.light.on(color)


class MotorControlSystem:
    """Main motor control system"""
    
    def __init__(self, config):
        self.config = config
        self.hub = CityHub(broadcast_channel=config.broadcast_channel)
        self.remote_controller = RemoteController(config)
        
        # Initialize devices
        self.motors = [
            MotorDevice(Port.A, config.motor_a_direction),
            MotorDevice(Port.B, config.motor_b_direction)
        ]
        
        # Initialize timers
        self.timers = [Timer(i) for i in range(3)]
        self.blink_timer = Timer(99)  # Special timer for LED blinking
        self.led_blink_state = False  # Track blink state (True = profile color, False = white)
        
        # System state
        self.current_speed = 0
        self.previous_speed = 0
        self.current_profile = 1
        self.light_value = config.initial_light_value
        self.has_lights = False
        
        # Initialize system
        self._initialize_devices()
        
    def _initialize_devices(self):
        """Initialize all connected devices"""
        for motor in self.motors:
            device_type = motor.detect_and_initialize()
            if device_type == DeviceType.LIGHT:
                self.has_lights = True
                motor.set_light_brightness(self.light_value)
                
    def _get_current_profile(self):
        """Get current motor profile"""
        return (self.config.profile_a if self.current_profile == 1 
                else self.config.profile_b)
                
    def _get_current_speed_led_config(self):
        """Get current speed-based LED configuration"""
        return (self.config.led_speed_profile_a if self.current_profile == 1
                else self.config.led_speed_profile_b)
                
    def _get_led_color_for_speed(self, speed):
        """Get LED color based on current speed and profile"""
        if not self.config.use_speed_based_leds:
            # Fall back to simple profile-based colors
            return (Color.GREEN * 0.3 if self.current_profile == 1 
                   else Color.RED * 0.5)
        
        speed_config = self._get_current_speed_led_config()
        profile = self._get_current_profile()
        
        # Calculate speed as percentage of max speed
        abs_speed = abs(speed)
        if abs_speed == 0:
            # Handle stopped state with optional blinking
            if self.config.blink_profile_when_stopped:
                return self._get_stopped_led_color(speed_config)
            else:
                return speed_config.stopped
            
        speed_percentage = (abs_speed / profile.max_speed) * 100
        
        if speed_percentage <= speed_config.slow_threshold:
            return speed_config.slow
        elif speed_percentage <= speed_config.medium_threshold:
            return speed_config.medium
        else:
            return speed_config.fast
            
    def _get_stopped_led_color(self, speed_config):
        """Get LED color for stopped state, handling blinking"""
        # Check if it's time to toggle blink state
        if self.blink_timer.check():
            self.led_blink_state = not self.led_blink_state
            
        # Start timer if not active
        if not self.blink_timer.active:
            self.blink_timer.start(speed_config.blink_interval_ms)
            
        # Return appropriate color based on blink state
        if self.led_blink_state:
            # Show profile indicator color
            profile_color = speed_config.profile_indicator
            if profile_color is None:
                # Fall back to fast color if no specific profile color set
                profile_color = speed_config.fast
            return profile_color
        else:
            # Show stopped color (usually white)
            return speed_config.stopped
                
    def _update_motor_speeds(self):
        """Update all motor speeds and remote LED"""
        if self.current_speed != self.previous_speed:
            for motor in self.motors:
                motor.set_speed(self.current_speed)
            self.previous_speed = self.current_speed
            
            # Update remote LED based on speed
            if self.remote_controller.connected:
                led_color = self._get_led_color_for_speed(self.current_speed)
                self.remote_controller.set_led(led_color)
            
            if self.config.should_broadcast:
                self._broadcast_data()
                
    def _handle_speed_control(self):
        """Handle speed increase/decrease controls"""
        profile = self._get_current_profile()
        button_map = self.config.button_mapping
        
        # Speed up
        if (self.remote_controller.is_button_pressed(button_map['UP']) and
            not self.remote_controller.is_button_pressed(button_map['STOP'])):
            self._accelerate(profile, 1)
            
        # Speed down  
        elif (self.remote_controller.is_button_pressed(button_map['DOWN']) and
              not self.remote_controller.is_button_pressed(button_map['STOP'])):
            self._accelerate(profile, -1)
            
        # Stop
        elif self.remote_controller.is_button_pressed(button_map['STOP']):
            self.current_speed = 0
            self._update_motor_speeds()
            wait(100)
            
    def _accelerate(self, profile, direction):
        """Handle acceleration in given direction"""
        for _ in range(profile.acceleration_step):
            self.current_speed += direction
            
            # Apply speed limits
            if self.current_speed > profile.max_speed:
                self.current_speed = profile.max_speed
            elif self.current_speed < -profile.max_speed:
                self.current_speed = -profile.max_speed
                
            # Apply minimum speed threshold
            if 0 < abs(self.current_speed) < profile.min_speed:
                self.current_speed = profile.min_speed * (1 if direction > 0 else -1)
            elif abs(self.current_speed) < profile.min_speed:
                self.current_speed = 0
                
            self._update_motor_speeds()
            wait(profile.acceleration_delay)
            
            if self.current_speed == 0:
                break
                
        # Handle continuous acceleration
        if not self.config.auto_acceleration:
            button_action = (self.config.button_mapping['UP'] if direction > 0 
                           else self.config.button_mapping['DOWN'])
            while self.remote_controller.is_button_pressed(button_action):
                wait(100)
                
        # Prevent direction change at zero speed
        if self.current_speed == 0:
            button_action = (self.config.button_mapping['UP'] if direction > 0 
                           else self.config.button_mapping['DOWN'])
            while self.remote_controller.is_button_pressed(button_action):
                wait(100)
                
    def _handle_light_control(self):
        """Handle light brightness control"""
        button_map = self.config.button_mapping
        wait_time = 0
        
        if (self.remote_controller.is_button_pressed(button_map['B_UP']) and
            not self.remote_controller.is_button_pressed(button_map['B_STOP'])):
            self.light_value = min(100, self.light_value + 10)
            wait_time = 100
            
        elif (self.remote_controller.is_button_pressed(button_map['B_DOWN']) and
              not self.remote_controller.is_button_pressed(button_map['B_STOP'])):
            self.light_value = max(0, self.light_value - 10)
            wait_time = 100
            
        elif self.remote_controller.is_button_pressed(button_map['B_STOP']):
            self.light_value = 100 if self.light_value == 0 else 0
            wait_time = 300
            
        if wait_time > 0:
            if self.config.should_broadcast:
                self._broadcast_data()
                
            if self.has_lights:
                for motor in self.motors:
                    motor.set_light_brightness(self.light_value)
                    
            wait(wait_time)
            
    def _handle_profile_switch(self):
        """Handle profile switching"""
        if self.remote_controller.is_button_pressed(self.config.button_mapping['SWITCH']):
            self.current_profile = 2 if self.current_profile == 1 else 1
            
            # Reset blink timer when switching profiles to immediately show new profile
            self.blink_timer.reset()
            self.led_blink_state = True  # Start with profile color
            
            # Update remote LED based on current speed and new profile
            if self.remote_controller.connected:
                led_color = self._get_led_color_for_speed(self.current_speed)
                self.remote_controller.set_led(led_color)
            
            # Wait for button release
            while self.remote_controller.is_button_pressed(self.config.button_mapping['SWITCH']):
                wait(100)
                
    def _broadcast_data(self):
        """Broadcast current state data"""
        data = (self.current_speed, self.light_value)
        self.hub.ble.broadcast(data)
        
    def _handle_remote_connection(self):
        """Handle remote connection status"""
        try:
            # Test connection by checking buttons
            self.remote_controller.remote.buttons.pressed()
            self.hub.light.on(self.config.led_connected)
            self.remote_controller.connected = True
            
        except (OSError, AttributeError):
            self.hub.light.on(self.config.led_not_connected)
            self.remote_controller.connected = False
            
            # Stop motors if watchdog enabled
            if self.config.watchdog_enabled:
                self.current_speed = 0
                self._update_motor_speeds()
                
            # Attempt reconnection
            if self.remote_controller.reconnect():
                print("Remote reconnected")
                
    def run(self):
        """Main system loop"""
        print(f"System: {self.hub.system.name()}")
        
        # Initial connection
        self.hub.light.on(Color.RED)
        if not self.remote_controller.connect():
            print("Failed to connect to remote")
            self.hub.system.shutdown()
            return
            
        print("Starting main loop...")
        
        while True:
            self._handle_remote_connection()
            
            if self.remote_controller.connected:
                self._handle_profile_switch()
                self._handle_speed_control()
                
                # Update LED continuously when stopped (for blinking)
                if self.current_speed == 0 and self.config.use_speed_based_leds and self.config.blink_profile_when_stopped:
                    led_color = self._get_led_color_for_speed(self.current_speed)
                    self.remote_controller.set_led(led_color)
                
                if self.has_lights or self.config.should_broadcast:
                    self._handle_light_control()
                    
            wait(10)


def main():
    """Main entry point"""
    config = Configuration()
    system = MotorControlSystem(config)
    system.run()


if __name__ == "__main__":
    main()
