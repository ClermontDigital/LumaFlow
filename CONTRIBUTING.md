# Contributing to LumaFlow

Thank you for your interest in contributing to LumaFlow! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues
- **Bug Reports**: Use the issue template and include HA version, light brands, and error logs
- **Feature Requests**: Describe the use case and expected behavior
- **Questions**: Check existing issues and documentation first

### Code Contributions
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following our coding standards
4. Test thoroughly with different light types
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 🛠️ Development Setup

### Prerequisites
- Home Assistant development environment
- Python 3.10+
- Git

### Installation
```bash
# Clone your fork
git clone https://github.com/yourusername/LumaFlow.git
cd LumaFlow

# Set up development environment
# Link to your HA custom_components directory
ln -s $(pwd)/custom_components/lumaflow /path/to/homeassistant/custom_components/

# Restart Home Assistant
```

### Testing Setup
Create test light entities in your HA configuration:
```yaml
# configuration.yaml - for testing
light:
  - platform: template
    lights:
      test_rgb:
        friendly_name: "Test RGB Light"
        value_template: "{{ states('input_boolean.test_light') }}"
        turn_on:
          service: input_boolean.turn_on
          entity_id: input_boolean.test_light
        turn_off:
          service: input_boolean.turn_off
          entity_id: input_boolean.test_light
        set_level:
          service: input_number.set_value
          data:
            entity_id: input_number.test_brightness
            value: "{{ brightness }}"
```

## 📝 Coding Standards

### Python Code Style
- Follow [Home Assistant's coding standards](https://developers.home-assistant.io/docs/development_checklist/)
- Use [Black](https://github.com/psf/black) for code formatting
- Use [isort](https://github.com/PyCQA/isort) for import sorting
- Include type hints for all functions and methods
- Write comprehensive docstrings

### Example Code Structure
```python
"""Example module docstring."""

import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ExampleClass:
    """Example class with proper documentation."""
    
    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the example class."""
        self.hass = hass
    
    async def async_example_method(self, param: str) -> Optional[Dict[str, Any]]:
        """Example async method with type hints and docstring.
        
        Args:
            param: Description of the parameter.
            
        Returns:
            Dictionary with results or None if failed.
        """
        try:
            # Implementation here
            return {"result": param}
        except Exception as err:
            _LOGGER.error("Error in example method: %s", err)
            return None
```

### File Organization
- Keep modules focused and single-purpose
- Use constants for magic numbers and strings
- Separate business logic from Home Assistant integration code
- Add comprehensive error handling and logging

## 🧪 Testing Guidelines

### Manual Testing Checklist
- [ ] Test with RGB lights (Hue, LIFX, etc.)
- [ ] Test with color temperature lights
- [ ] Test with white-only lights
- [ ] Test override detection and restore
- [ ] Test daily override reset (wait for midnight or adjust system time)
- [ ] Test configuration flow with various inputs
- [ ] Test edge cases (polar regions, DST transitions)
- [ ] Test performance with many lights

### Test Light Brands
If possible, test with these popular brands:
- Philips Hue (RGB and white)
- LIFX
- Shelly RGBW
- TP-Link Kasa
- WLED
- Generic ESPHome lights

### Performance Testing
- Monitor CPU usage during operation
- Check memory usage with large light counts
- Verify smooth transitions without flicker
- Test network resilience (disconnect/reconnect lights)

## 🏗️ Architecture Overview

### Key Components
- **Coordinator**: Central data management and astronomical calculations
- **Config Flow**: Multi-step setup and options handling
- **Entities**: Switch and sensor entities for HA integration
- **Services**: Manual control and override functionality

### Data Flow
```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐
│   Coordinator   │────│   Light Control  │────│     Lights     │
│                 │    │                  │    │                │
│ • Astronomical  │    │ • State Checking │    │ • RGB Lights   │
│   Calculations  │    │ • Override       │    │ • Color Temp   │
│ • Phase Logic   │    │   Detection      │    │ • White Only   │
│ • Daily Reset   │    │ • Service Calls  │    │                │
└─────────────────┘    └──────────────────┘    └────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────────────┐
                    │   Home Assistant   │
                    │                    │
                    │ • Entities         │
                    │ • Automations      │
                    │ • UI Integration   │
                    └────────────────────┘
```

## 📋 Pull Request Process

### Before Submitting
1. **Code Quality**: Ensure code follows standards and is well-documented
2. **Testing**: Test thoroughly with different light types and configurations
3. **Documentation**: Update README and docstrings as needed
4. **Changelog**: Add entry to IMPLEMENTATION_SUMMARY.md if significant

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tested with RGB lights
- [ ] Tested with color temperature lights
- [ ] Tested configuration flow
- [ ] Tested override functionality

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Documentation updated
- [ ] No new warnings or errors
```

## 🐛 Issue Templates

### Bug Report
- Home Assistant version
- LumaFlow version
- Light brands and models affected
- Configuration details
- Error logs
- Steps to reproduce

### Feature Request
- Use case description
- Expected behavior
- Alternative solutions considered
- Additional context

## 📚 Resources

### Home Assistant Development
- [Developer Documentation](https://developers.home-assistant.io/)
- [Integration Development](https://developers.home-assistant.io/docs/creating_component_index/)
- [Code Standards](https://developers.home-assistant.io/docs/development_checklist/)

### LumaFlow Specific
- [Astral Documentation](https://astral.readthedocs.io/)
- [Circadian Lighting Research](https://en.wikipedia.org/wiki/Circadian_lighting)
- [Home Assistant Light Integration](https://www.home-assistant.io/integrations/light/)

## 🙏 Recognition

Contributors will be recognized in:
- README acknowledgments section
- Release notes
- Git commit history

Thank you for helping make LumaFlow better for everyone! 🌅✨ 