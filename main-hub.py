"""
LEGO Motor Control System
Uses https://code.pybricks.com/ with LEGO City hub and remote control
Connect 1 or 2 motors of any kind to Port A and/or B
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List
from pybricks.parameters import Color, Port, Stop, Button
from pybricks.pupdevices import DCMotor, Motor, Remote, Light
from pybricks.hubs import CityHub
from pybricks.tools import wait, StopWatch
from pybricks.iodevices import PUPDevice
from uerrno import ENODEV


class DeviceType(Enum):
    """Supported device types"""
    MOTOR = "Motor"
    DC_MOTOR = "DCMotor"
    LIGHT = "Light"
    UNKNOWN = "Unknown"
    NOT_CONNECTED = "NotConnected"


class ButtonAction(Enum):
    """Remote control button actions"""
    A_PLUS = "A+"
    A_MINUS = "A-"
    A_STOP = "A0"
    B_PLUS = "B+"
    B_MINUS = "B-"
    B_STOP = "B0"
    CENTER = "CENTER"


@dataclass
class MotorProfile:
    """Motor speed profile configuration"""
    min_speed: int
    max_speed: int
    acceleration_step: int
    acceleration_delay: int  # in milliseconds


@dataclass
class SpeedLEDConfig:
    """LED color configuration based on speed"""
    stopped: Any = Color.WHITE * 0.2
    slow: Any = Color.YELLOW * 0.5
    medium: Any = Color.ORANGE * 0.5
    fast: Any = Color.RED * 0.7
    profile_indicator: Any = None  # Color to blink with when stopped (None = use fast color)
    
    # Speed thresholds (as percentage of max speed)
    slow_threshold: int = 30  # Below this = slow color
    medium_threshold: int = 60  # Below this = medium color
    # Above medium_threshold = fast color
    
    # Blinking settings when stopped
    blink_interval_ms: int = 500  # How fast to blink (milliseconds)


@dataclass
class Configuration:
    """System configuration"""
    # Motor profiles
    profile_a: MotorProfile = MotorProfile(20, 100, 10, 100)
    profile_b: MotorProfile = MotorProfile(10, 500, 5, 200)
    
    # Motor directions
    motor_a_direction: int = 1
    motor_b_direction: int = -1
    
    # Behavior settings
    auto_acceleration: bool = False
    watchdog_enabled: bool = False
    should_broadcast: bool = False
    
    # Connection settings
    remote_timeout: int = 10  # seconds
    remote_name: str = ""
    broadcast_channel: int = 1
    
    # Lighting
    initial_light_value: int = 0
    
    # Button mappings
    button_mapping: Dict[str, ButtonAction] = None
    
    # LED colors - connection status
    led_connected: Any = Color.GREEN * 0.3
    led_not_connected: Any = Color.RED * 0.5
    
    # Speed-based LED colors for each profile
    led_speed_profile_a: SpeedLEDConfig = SpeedLEDConfig(
        profile_indicator=Color.GREEN * 0.6  # Blinks green when stopped
    )
    led_speed_profile_b: SpeedLEDConfig = SpeedLEDConfig(
        stopped=Color.WHITE * 0.2,
        slow=Color.BLUE * 0.5,
        medium=Color.MAGENTA * 0.5,
        fast=Color.VIOLET * 0.7,
        profile_indicator=Color.RED * 0.6,  # Blinks red when stopped
        slow_threshold=20,
        medium_threshold=50
    )
    
    # Enable speed-based LED colors
    use_speed_based_leds: bool = True
    
    # Enable profile indication when stopped
    blink_profile_when_stopped: bool = True
    
    def __post_init__(self):
        if self.button_mapping is None:
            self.button_mapping = {
                'UP': ButtonAction.A_PLUS,
                'DOWN': ButtonAction.A_MINUS,
                'STOP': ButtonAction.A_STOP,
                'SWITCH': ButtonAction.CENTER,
                'B_UP': ButtonAction.B_PLUS,
                'B_DOWN': ButtonAction.B_MINUS,
                'B_STOP': ButtonAction.B_STOP,
            }


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
    
    def __init__(self, port: Port, direction: int):
        self.port = port
        self.direction = direction
        self.device_type = DeviceType.NOT_CONNECTED
        self.max_speed = 1000
        self.device_object = None
        
    def detect_and_initialize(self) -> DeviceType:
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
        
    def _initialize_servo_motor(self, device_id: int) -> None:
        """Initialize servo motor with proper speed limits"""
        self.device_type = DeviceType.MOTOR
        self.device_object = Motor(self.port)
        
        max_speed = self.MAX_SPEEDS.get(device_id, 1000)
        self.max_speed = int(max_speed * 0.9)  # 90% of max for safety
        
        self.device_object.stop()
        self.device_object.control.limits(speed=max_speed, acceleration=10000)
        
    def _initialize_dc_motor(self) -> None:
        """Initialize DC motor"""
        self.device_type = DeviceType.DC_MOTOR
        self.device_object = DCMotor(self.port)
        
    def _initialize_light(self) -> None:
        """Initialize light device"""
        self.device_type = DeviceType.LIGHT
        self.device_object = Light(self.port)
        
    def set_speed(self, speed: int) -> None:
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
                
    def set_light_brightness(self, brightness: int) -> None:
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
    
    def __init__(self, config: Configuration):
        self.config = config
        self.remote: Optional[Remote] = None
        self.connected = False
        
    def connect(self) -> bool:
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
            
    def reconnect(self) -> bool:
        """Attempt to reconnect to remote"""
        try:
            self.remote = Remote(timeout=1000)
            self.connected = True
            return True
        except OSError:
            self.connected = False
            return False
            
    def is_button_pressed(self, action: ButtonAction) -> bool:
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
            
    def set_led(self, color) -> None:
        """Set remote LED color"""
        if self.connected and self.remote:
            self.remote.light.on(color)


class MotorControlSystem:
    """Main motor control system"""
    
    def __init__(self, config: Configuration):
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
        
        # System state
        self.current_speed = 0
        self.previous_speed = 0
        self.current_profile = 1
        self.light_value = config.initial_light_value
        self.has_lights = False
        
        # Initialize system
        self._initialize_devices()
        
    def _initialize_devices(self) -> None:
        """Initialize all connected devices"""
        for motor in self.motors:
            device_type = motor.detect_and_initialize()
            if device_type == DeviceType.LIGHT:
                self.has_lights = True
                motor.set_light_brightness(self.light_value)
                
    def _get_current_profile(self) -> MotorProfile:
        """Get current motor profile"""
        return (self.config.profile_a if self.current_profile == 1 
                else self.config.profile_b)
                
    def _get_current_speed_led_config(self) -> SpeedLEDConfig:
        """Get current speed-based LED configuration"""
        return (self.config.led_speed_profile_a if self.current_profile == 1
                else self.config.led_speed_profile_b)
                
    def _get_led_color_for_speed(self, speed: int) -> Any:
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
            return speed_config.stopped
            
        speed_percentage = (abs_speed / profile.max_speed) * 100
        
        if speed_percentage <= speed_config.slow_threshold:
            return speed_config.slow
        elif speed_percentage <= speed_config.medium_threshold:
            return speed_config.medium
        else:
            return speed_config.fast
                
    def _update_motor_speeds(self) -> None:
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
                
    def _handle_speed_control(self) -> None:
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
            
    def _accelerate(self, profile: MotorProfile, direction: int) -> None:
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
                
    def _handle_light_control(self) -> None:
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
            
    def _handle_profile_switch(self) -> None:
        """Handle profile switching"""
        if self.remote_controller.is_button_pressed(self.config.button_mapping['SWITCH']):
            self.current_profile = 2 if self.current_profile == 1 else 1
            
            # Update remote LED based on current speed and new profile
            if self.remote_controller.connected:
                led_color = self._get_led_color_for_speed(self.current_speed)
                self.remote_controller.set_led(led_color)
            
            # Wait for button release
            while self.remote_controller.is_button_pressed(self.config.button_mapping['SWITCH']):
                wait(100)
                
    def _broadcast_data(self) -> None:
        """Broadcast current state data"""
        data = (self.current_speed, self.light_value)
        self.hub.ble.broadcast(data)
        
    def _handle_remote_connection(self) -> None:
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
                
    def run(self) -> None:
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
