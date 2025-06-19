"""
LEGO Observer Hub System
Uses https://code.pybricks.com/ with LEGO City hub
Receives commands from a primary hub via BLE broadcast
Connect 1 or 2 motors of any kind to Port A and/or B
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from pybricks.parameters import Color, Port, Stop
from pybricks.pupdevices import DCMotor, Motor, Light
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


@dataclass
class ObserverConfiguration:
    """Observer hub configuration"""
    # Communication settings
    observe_channel: int = 1
    connection_timeout_ms: int = 1000  # Consider disconnected after this time
    
    # Motor directions
    motor_a_direction: int = 1
    motor_b_direction: int = -1
    
    # Lighting
    initial_light_value: int = 0
    
    # LED colors for connection status
    led_receiving: Any = Color.GREEN * 0.3
    led_not_receiving: Any = Color.YELLOW * 0.5
    
    # Debug output
    enable_debug_output: bool = True
    
    # Data validation
    max_speed_value: int = 1000  # Maximum expected speed value
    max_light_value: int = 100   # Maximum light brightness


class MotorDevice:
    """Represents a connected motor or device on observer hub"""
    
    # Device ID mappings (same as main controller)
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
                print(f"{self.port}: not connected")
                return self.device_type
            raise
            
        device_id = device.info()['id']
        device_name = self.DEVICE_NAMES.get(device_id, f"Unknown device ID {device_id}")
        
        print(f"--")
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
            print(f"{self.port}: Unknown device with ID {device_id}")
            
        return self.device_type
        
    def _initialize_servo_motor(self, device_id: int) -> None:
        """Initialize servo motor with proper speed limits"""
        self.device_type = DeviceType.MOTOR
        self.device_object = Motor(self.port)
        
        max_speed = self.MAX_SPEEDS.get(device_id, 1000)
        self.max_speed = int(max_speed * 0.9)  # 90% of max for safety
        
        self.device_object.stop()
        self.device_object.control.limits(speed=max_speed, acceleration=10000)
        
        print(f"{self.port}: Motor initialized - max speed: {self.max_speed}")
        
    def _initialize_dc_motor(self) -> None:
        """Initialize DC motor"""
        self.device_type = DeviceType.DC_MOTOR
        self.device_object = DCMotor(self.port)
        print(f"{self.port}: DC Motor initialized")
        
    def _initialize_light(self) -> None:
        """Initialize light device"""
        self.device_type = DeviceType.LIGHT
        self.device_object = Light(self.port)
        print(f"{self.port}: Light initialized")
        
    def set_speed(self, speed: int) -> None:
        """Set motor speed based on device type"""
        if not self.device_object or self.device_type in [DeviceType.NOT_CONNECTED, DeviceType.LIGHT]:
            return
            
        actual_speed = speed * self.direction
        
        if self.device_type == DeviceType.MOTOR:
            if speed == 0:
                self.device_object.stop()
            else:
                # Scale speed appropriately for servo motors
                scaled_speed = actual_speed * self.max_speed / 100
                self.device_object.run(scaled_speed)
                
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
                self.device_object.on(max(0, min(100, brightness)))


class BLEDataReceiver:
    """Handles BLE data reception and validation"""
    
    def __init__(self, hub: CityHub, config: ObserverConfiguration):
        self.hub = hub
        self.config = config
        self.last_received_time = StopWatch()
        self.connection_established = False
        
    def receive_data(self) -> Optional[Tuple[int, int]]:
        """Receive and validate data from BLE broadcast"""
        try:
            data = self.hub.ble.observe(self.config.observe_channel)
            
            if data is None:
                # No data received
                if self.connection_established:
                    # We were connected but lost signal
                    if self.config.enable_debug_output:
                        print("Connection lost - no data received")
                    self.connection_established = False
                return None
                
            # Data received successfully
            if not self.connection_established:
                if self.config.enable_debug_output:
                    print("Connection established")
                self.connection_established = True
                
            self.last_received_time.reset()
            
            # Validate and parse data
            return self._validate_data(data)
            
        except Exception as e:
            if self.config.enable_debug_output:
                print(f"Error receiving data: {e}")
            return None
            
    def _validate_data(self, data: Any) -> Optional[Tuple[int, int]]:
        """Validate received data format and values"""
        try:
            if not isinstance(data, (tuple, list)) or len(data) != 2:
                if self.config.enable_debug_output:
                    print(f"Invalid data format: {data}")
                return None
                
            speed, light = data
            
            # Validate speed value
            if not isinstance(speed, (int, float)):
                if self.config.enable_debug_output:
                    print(f"Invalid speed type: {type(speed)}")
                return None
                
            # Validate light value
            if not isinstance(light, (int, float)):
                if self.config.enable_debug_output:
                    print(f"Invalid light type: {type(light)}")
                return None
                
            # Clamp values to reasonable ranges
            speed = max(-self.config.max_speed_value, 
                       min(self.config.max_speed_value, int(speed)))
            light = max(0, min(self.config.max_light_value, int(light)))
            
            return (speed, light)
            
        except Exception as e:
            if self.config.enable_debug_output:
                print(f"Data validation error: {e}")
            return None
            
    def is_connected(self) -> bool:
        """Check if we're currently receiving data"""
        return (self.connection_established and 
                self.last_received_time.time() < self.config.connection_timeout_ms)


class ObserverHub:
    """Main observer hub system"""
    
    def __init__(self, config: ObserverConfiguration):
        self.config = config
        self.hub = CityHub(observe_channels=[config.observe_channel])
        self.data_receiver = BLEDataReceiver(self.hub, config)
        
        # Initialize devices
        self.motors = [
            MotorDevice(Port.A, config.motor_a_direction),
            MotorDevice(Port.B, config.motor_b_direction)
        ]
        
        # System state
        self.current_speed = 0
        self.previous_speed = 0
        self.current_light_value = config.initial_light_value
        self.has_lights = False
        
        # Initialize system
        self._initialize_devices()
        
    def _initialize_devices(self) -> None:
        """Initialize all connected devices"""
        print("Initializing observer hub devices...")
        
        for i, motor in enumerate(self.motors, 1):
            device_type = motor.detect_and_initialize()
            if device_type == DeviceType.LIGHT:
                self.has_lights = True
                motor.set_light_brightness(self.current_light_value)
                
        print(f"Initialization complete. Lights available: {self.has_lights}")
        
    def _update_motor_speeds(self, speed: int) -> None:
        """Update all motor speeds"""
        if speed != self.previous_speed:
            for motor in self.motors:
                motor.set_speed(speed)
            self.previous_speed = speed
            
            if self.config.enable_debug_output and speed != 0:
                print(f"Speed updated to: {speed}")
                
    def _update_lights(self, light_value: int) -> None:
        """Update all light devices"""
        if light_value != self.current_light_value and self.has_lights:
            for motor in self.motors:
                motor.set_light_brightness(light_value)
            self.current_light_value = light_value
            
            if self.config.enable_debug_output:
                print(f"Light value updated to: {light_value}")
                
    def _update_connection_status(self, connected: bool) -> None:
        """Update hub LED based on connection status"""
        if connected:
            self.hub.light.on(self.config.led_receiving)
        else:
            self.hub.light.on(self.config.led_not_receiving)
            
    def run(self) -> None:
        """Main observer loop"""
        print(f"Observer Hub: {self.hub.system.name()}")
        print(f"Observing channel: {self.config.observe_channel}")
        print("Starting observation loop...")
        
        # Initial status
        self._update_connection_status(False)
        
        while True:
            # Receive data from primary hub
            received_data = self.data_receiver.receive_data()
            
            # Update connection status
            connected = self.data_receiver.is_connected()
            self._update_connection_status(connected)
            
            if received_data is not None:
                speed, light_value = received_data
                
                # Update motors and lights
                self._update_motor_speeds(speed)
                self._update_lights(light_value)
                
            elif connected:
                # We're connected but didn't receive new data this cycle
                pass
            else:
                # Not connected - could implement safety stop here
                if self.current_speed != 0:
                    if self.config.enable_debug_output:
                        print("Connection lost - stopping motors")
                    self._update_motor_speeds(0)
                    
            wait(10)


def main():
    """Main entry point - configure your observer hub here"""
    
    # -----------------------------------------------
    # Configure your observer hub settings here
    # -----------------------------------------------
    
    config = ObserverConfiguration(
        # Communication settings
        observe_channel=1,          # Must match primary hub broadcast channel (0-255)
        connection_timeout_ms=1000, # Consider disconnected after this time
        
        # Motor directions (1 or -1)
        motor_a_direction=1,        # Port A motor direction
        motor_b_direction=-1,       # Port B motor direction
        
        # Lighting
        initial_light_value=0,      # Initial light brightness (0-100)
        
        # LED colors for connection status
        led_receiving=Color.GREEN * 0.3,     # Connected to primary hub
        led_not_receiving=Color.YELLOW * 0.5, # Not receiving data
        
        # Debug output
        enable_debug_output=True    # Set to False for quieter operation
    )
    
    # Create and run the observer hub
    print("Starting LEGO Observer Hub...")
    observer = ObserverHub(config)
    observer.run()


if __name__ == "__main__":
    main()
