# Pybricks-Train-Control-Mod
An updated pythonized version of the train control script created by Lok24 and modified by and-ampersand-and

[Original Thread on Eurobricks](https://www.eurobricks.com/forum/forums/topic/187081-control-your-trains-without-smart-device-with-pybricks/)

[and-ampersand-and Thread on Eurobricks moding the original script by Lok24](https://www.eurobricks.com/forum/forums/topic/197633-controlling-multiple-locomotives-on-the-same-train-with-pybricks/)

[Script by and-ampersand-and on Github](https://github.com/and-ampersand-and/PyBricks-Train-Motor-Control-Script/tree/main)

## Updates made from original script
- Refactored into modern python coding standards with an object-oriented design
- Added ability to customize the remote LED based on the speed of the train.
  - Based upon a comment made on the original Lok24 Eurobrick thread [link to comment](https://www.eurobricks.com/forum/forums/topic/187081-control-your-trains-without-smart-device-with-pybricks/?do=findComment&comment=3477742)
- When stopped, remote LED blinks between stopped color (see point above) and color indicating which profile is active

## Todos
- Allow for more than 2 speed profiles and let user cycle through them

# LEGO Motor Control System

A modern Python-based control system for LEGO trains and motors using Pybricks. This system provides remote control of multiple LEGO hubs with advanced features like speed profiles, LED feedback, and wireless coordination between hubs.

## 🚂 Features

- **Remote Control**: Control motors using LEGO remote control
- **Multiple Speed Profiles**: Two configurable speed profiles with different acceleration characteristics
- **Visual Feedback**: Speed-based LED colors with profile indication
- **Multi-Hub Support**: Wireless control of multiple observer hubs from one primary hub
- **Auto-Detection**: Automatic detection and configuration of connected motors and lights
- **Safety Features**: Watchdog timers, connection monitoring, and graceful error handling
- **Modern Python**: Clean, maintainable code with object-oriented design

## 📋 Requirements

### Hardware
- LEGO City Hub (primary controller)
- LEGO Remote Control
- Additional LEGO City Hubs (for observer hubs)
- LEGO motors (any compatible type):
  - Wedo 2.0 DC Motor
  - Train DC Motor
  - BOOST Interactive Motor
  - Technic Large/Medium Angular Motors
  - SPIKE Medium/Large Angular Motors
- LEGO lights (optional)

### Software
- [Pybricks](https://code.pybricks.com/) development environment
- **Note**: Code is optimized for MicroPython compatibility (no dataclasses, enums, or type hints)

## 🚀 Quick Start

### 1. Primary Hub Setup (Main Controller)

1. Copy `main_hub.py` to your primary hub
2. Connect motors to Port A and/or Port B
3. Pair your LEGO remote control
4. Configure settings in the `Configuration` class:

```python
config = Configuration(
    # Motor profiles
    profile_a=MotorProfile(20, 100, 10, 100),  # min, max, step, delay
    profile_b=MotorProfile(10, 500, 5, 200),
    
    # Enable broadcasting for observer hubs
    should_broadcast=True,
    broadcast_channel=1,
    
    # Enable speed-based LED colors
    use_speed_based_leds=True,
    blink_profile_when_stopped=True
)
```

5. Run the script

### 2. Observer Hub Setup (Secondary Hubs)

1. Copy `observer_hub.py` to each observer hub
2. Connect motors to Port A and/or Port B
3. Configure the observer channel to match your primary hub:

```python
config = ObserverConfiguration()

# Communication settings
config.observe_channel = 1          # Must match primary hub's broadcast_channel
config.connection_timeout_ms = 1000 # Consider disconnected after this time

# Motor directions (1 or -1)
config.motor_a_direction = 1        # Adjust motor directions as needed
config.motor_b_direction = -1

# Debug output
config.enable_debug_output = True   # Set to False for quieter operation
```

4. Run the script on each observer hub

## 🎮 Controls

### Remote Control Layout

| Button | Function |
|--------|----------|
| **Left +** | Increase speed (based on current profile) |
| **Left -** | Decrease speed (based on current profile) |
| **Left** | Emergency stop |
| **Right +** | Increase light brightness |
| **Right -** | Decrease light brightness |
| **Right** | Toggle lights (off/max) |
| **Center** | Switch between Profile A and Profile B |

### LED Feedback

#### Hub LED (Connection Status)
- **Green**: Remote connected
- **Red/Yellow**: Remote disconnected

#### Remote LED (Speed & Profile)
When `use_speed_based_leds=True`:

**Profile A (Default Colors)**:
- **White ↔ Green (blinking)**: Stopped (indicates Profile A)
- **Yellow**: Slow speed (0-30% of max)
- **Orange**: Medium speed (30-60% of max)
- **Red**: High speed (60-100% of max)

**Profile B (Default Colors)**:
- **White ↔ Red (blinking)**: Stopped (indicates Profile B)
- **Blue**: Slow speed (0-20% of max)
- **Magenta**: Medium speed (20-50% of max)
- **Violet**: High speed (50-100% of max)

## ⚙️ Configuration

### Motor Profiles

Motor profiles define speed and acceleration characteristics:

```python
# Note: Using regular classes instead of dataclasses for MicroPython compatibility
class MotorProfile:
    def __init__(self, min_speed=20, max_speed=100, acceleration_step=10, acceleration_delay=100):
        self.min_speed = min_speed           # Minimum speed when moving
        self.max_speed = max_speed           # Maximum speed
        self.acceleration_step = acceleration_step   # Speed increase per button press
        self.acceleration_delay = acceleration_delay  # Delay between steps (milliseconds)
```

**Example Profiles**:
- **Profile A**: `MotorProfile(20, 100, 10, 100)` - Smooth, precise control
- **Profile B**: `MotorProfile(10, 100, 5, 200)` - Lower starting speed, more gradual acceleration

### LED Color Customization

Customize LED colors for each profile:

```python
# Speed-based colors for Profile A (using regular class syntax)
config = Configuration()
config.led_speed_profile_a.stopped = Color.WHITE * 0.2
config.led_speed_profile_a.slow = Color.YELLOW * 0.5
config.led_speed_profile_a.medium = Color.ORANGE * 0.5
config.led_speed_profile_a.fast = Color.RED * 0.7
config.led_speed_profile_a.profile_indicator = Color.GREEN * 0.6  # Blinks with white when stopped
config.led_speed_profile_a.slow_threshold = 30      # Below 30% = slow color
config.led_speed_profile_a.medium_threshold = 60    # Below 60% = medium color
config.led_speed_profile_a.blink_interval_ms = 500  # Blink speed when stopped
```

### Multi-Hub Communication

Set up wireless communication between hubs:

**Primary Hub**:
```python
config = Configuration(
    should_broadcast=True,
    broadcast_channel=1
)
```

**Observer Hubs**:
```python
config = ObserverConfiguration(
    observe_channel=1  # Must match primary hub's broadcast_channel
)
```

## 🔧 Advanced Features

### Watchdog Timer

Enable automatic motor stop when remote disconnects:

```python
config = Configuration(
    watchdog_enabled=True,
    remote_timeout=10  # seconds
)
```

### Auto-Acceleration

Enable continuous acceleration while holding buttons:

```python
config = Configuration(
    auto_acceleration=True
)
```

## 🏗️ System Architecture

### Primary Hub (Controller)
- Handles remote control input
- Manages motor speed profiles
- Controls LED feedback
- Broadcasts commands to observer hubs
- Manages connected motors and lights

### Observer Hub (Receiver)
- Receives commands via BLE broadcast
- Controls local motors and lights
- Provides connection status feedback
- Automatic device detection and configuration

### Communication Protocol
Data broadcast format: `(speed, light_brightness)`
- **speed**: Integer (-max_speed to +max_speed)
- **light_brightness**: Integer (0-100)

## 🔍 Troubleshooting

### Common Issues

**Remote won't connect**:
- Check remote is paired and powered on
- Verify `remote_timeout` setting
- Try restarting both remote and hub

**Observer hub not responding**:
- Verify `observe_channel` matches `broadcast_channel`
- Check observer hub LED (should be green when receiving)
- Enable `enable_debug_output=True` for diagnostics

**Motors not moving**:
- Check motor connections (Port A and/or B)
- Verify motor direction settings (`motor_a_direction`, `motor_b_direction`)
- Check that profile min_speed isn't too high

**LED colors wrong**:
- Verify `use_speed_based_leds=True`
- Check speed thresholds in LED configuration
- Ensure remote is properly connected

## 🔗 Related Links

- [Pybricks Documentation](https://docs.pybricks.com/)
- [LEGO Powered Up Specification](https://lego.github.io/lego-ble-wireless-protocol-docs/)
- [Pybricks Code Environment](https://code.pybricks.com/)

---

**Happy Building! 🧱**
