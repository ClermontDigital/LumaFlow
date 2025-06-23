# LumaFlow Testing Checklist
## 🧪 Real-World Testing & Validation - v0.1.4

### **Current Test Environment**
- ✅ **HACS Version**: 0.1.4 installed successfully
- ✅ **Test Light**: `light.office_1_stat` (Tuya Smart Bulb)
- ✅ **Home Assistant**: Core integration setup complete

---

## **📋 PHASE 1: Basic Functionality Tests** ⚡ URGENT

### Test 1: Initial Setup Validation
- [ ] **3-Step Configuration Flow**
  - [ ] Step 1: Light selection shows available lights correctly
  - [ ] Step 2: Timing configuration accepts valid ranges
  - [ ] Step 3: Advanced options save properly
- [ ] **Entity Creation**
  - [ ] `switch.lumaflow` entity appears
  - [ ] `sensor.lumaflow_current_phase` shows current phase
  - [ ] `sensor.lumaflow_next_transition` displays next transition time
- [ ] **Device Registry**
  - [ ] LumaFlow device appears in Settings → Devices
  - [ ] All entities properly grouped under device

**✅ SUCCESS CRITERIA**: Complete configuration without errors, all entities visible

### Test 2: Automatic Light Adjustment
- [ ] **Circadian Response Test**
  - [ ] Turn on test light manually
  - [ ] Verify light immediately adjusts to current circadian phase
  - [ ] Confirm brightness and color temperature match expected values
- [ ] **Phase Calculation Accuracy**
  - [ ] Check current phase matches time of day
  - [ ] Verify brightness/color temp values are reasonable
  - [ ] Test at different times (day, evening, night)

**✅ SUCCESS CRITERIA**: Light automatically adapts when turned on

### Test 3: Manual Override System
- [ ] **Override Detection**
  - [ ] Enable LumaFlow for test light
  - [ ] Manually change light brightness/color
  - [ ] Verify override is detected (check sensor attributes)
- [ ] **Restore Functionality**
  - [ ] Use `lumaflow.restore_lights` service
  - [ ] Confirm light returns to current circadian cycle
  - [ ] Verify override status clears

**✅ SUCCESS CRITERIA**: Override system works reliably

### Test 4: Daily Reset Behavior  
- [ ] **Midnight Reset Simulation**
  - [ ] Set light to overridden state
  - [ ] Wait for next coordinator update cycle
  - [ ] Verify overrides persist within same day
  - [ ] Check if artificial date change clears overrides

**✅ SUCCESS CRITERIA**: Override reset functions as designed

---

## **📊 PHASE 2: Performance & Reliability Tests**

### Test 5: Resource Usage Monitoring
- [ ] **CPU Usage Tracking**
  - [ ] Monitor HA system stats during operation
  - [ ] Verify claimed <1% CPU usage
  - [ ] Check impact during light transitions
- [ ] **Memory Consumption**
  - [ ] Monitor integration memory usage over time
  - [ ] Check for memory leaks during extended operation
- [ ] **Network Efficiency**
  - [ ] Count API calls to lights per update cycle
  - [ ] Verify minimal network overhead

**✅ SUCCESS CRITERIA**: Resource usage within acceptable limits

### Test 6: Error Handling & Recovery
- [ ] **Light Unavailability**
  - [ ] Disconnect test light from network
  - [ ] Verify graceful error handling
  - [ ] Confirm recovery when light reconnects
- [ ] **Home Assistant Restart**
  - [ ] Restart HA with LumaFlow configured
  - [ ] Verify integration loads properly
  - [ ] Check state persistence
- [ ] **Invalid Configuration**
  - [ ] Test edge cases in configuration values
  - [ ] Verify validation catches errors
  - [ ] Check error message clarity

**✅ SUCCESS CRITERIA**: Robust error handling without crashes

---

## **🌍 PHASE 3: Geographic & Timing Tests**

### Test 7: Astronomical Calculation Accuracy
- [ ] **Current Location Test**
  - [ ] Verify HA location settings are used
  - [ ] Check sunset/sunrise times against reliable source
  - [ ] Confirm timezone handling is correct
- [ ] **Offset Functionality**
  - [ ] Test positive sunset offset (+30 minutes)
  - [ ] Test negative sunset offset (-30 minutes)
  - [ ] Verify timing adjustments work correctly

**✅ SUCCESS CRITERIA**: Accurate astronomical calculations

### Test 8: Edge Case Scenarios
- [ ] **Extreme Timing**
  - [ ] Test during very long/short days
  - [ ] Verify polar region handling (if applicable)
  - [ ] Check daylight saving time transitions
- [ ] **Configuration Limits**
  - [ ] Test minimum/maximum brightness settings
  - [ ] Test color temperature range limits
  - [ ] Verify transition speed variations

**✅ SUCCESS CRITERIA**: Stable operation under edge conditions

---

## **🎛️ PHASE 4: User Experience Tests**

### Test 9: Service Integration
- [ ] **Service Call Testing**
  - [ ] `lumaflow.enable` - enables circadian control
  - [ ] `lumaflow.disable` - disables without losing config
  - [ ] `lumaflow.restore_lights` - restores overridden lights
  - [ ] `lumaflow.override_lights` - applies manual settings
- [ ] **Automation Integration**
  - [ ] Create test automation using LumaFlow services
  - [ ] Verify triggers work with phase changes
  - [ ] Test conditional logic based on LumaFlow state

**✅ SUCCESS CRITERIA**: All services function correctly

### Test 10: User Interface Validation
- [ ] **Entity States**
  - [ ] Switch entity reflects actual state
  - [ ] Sensor data updates correctly
  - [ ] Attributes show relevant information
- [ ] **Configuration Options**
  - [ ] Options flow allows runtime changes
  - [ ] Changes take effect immediately
  - [ ] Invalid inputs are rejected with clear messages

**✅ SUCCESS CRITERIA**: Intuitive user experience

---

## **🚨 CRITICAL VALIDATION POINTS**

### ⚡ **Must-Pass Tests**
1. ✅ **Light Control**: Tuya light responds to circadian adjustments
2. ✅ **Override System**: Manual changes detected and restorable
3. ✅ **Daily Reset**: Overrides clear at midnight (PRD requirement)
4. ✅ **Performance**: <1% CPU usage confirmed
5. ✅ **No Crashes**: Stable operation for extended periods

### 🔍 **Current Test Status**
- **Phase 1**: 🧪 IN PROGRESS (User testing basic functionality)
- **Phase 2**: 🔄 PENDING (Resource monitoring needed)
- **Phase 3**: 🔄 PENDING (Geographic accuracy validation)  
- **Phase 4**: 🔄 PENDING (Service and UI testing)

---

## **📝 TEST EXECUTION LOG**

### **Test Session 1**: Basic Setup & Light Control
**Date**: [TO BE FILLED]
**Environment**: HA Core + Tuya Smart Bulb
**Status**: 🧪 IN PROGRESS

**Results**:
- [ ] Configuration completed successfully
- [ ] Light responds to circadian control
- [ ] Override system functional
- [ ] Issues found: [TO BE DOCUMENTED]

### **Test Session 2**: Performance & Reliability  
**Date**: [TO BE SCHEDULED]
**Focus**: Resource usage and error handling
**Status**: 🔄 PENDING

### **Test Session 3**: Extended Operation
**Date**: [TO BE SCHEDULED]  
**Focus**: 24+ hour continuous operation
**Status**: 🔄 PENDING

---

## **🎯 SUCCESS/FAILURE CRITERIA**

### **✅ PASS Criteria**
- All Phase 1 tests complete without critical issues
- Light control works reliably with test hardware
- Performance meets documented specifications
- Override system functions per PRD requirements
- No integration crashes or HA instability

### **❌ FAIL Criteria**
- Critical functionality doesn't work with common lights
- Performance significantly exceeds resource claims
- Frequent crashes or errors during normal operation
- Configuration flow fails or confuses users
- Override system doesn't meet PRD specifications

---

## **🔄 NEXT STEPS AFTER TESTING**

### **If Tests Pass** ✅
1. **Expand Beta Testing**: Additional users and light brands
2. **Version 0.2.0**: Stability improvements based on feedback
3. **Documentation Updates**: Real-world examples and troubleshooting
4. **Community Feedback**: Feature requests and improvements

### **If Tests Fail** ❌
1. **Issue Resolution**: Fix critical bugs found in testing
2. **Regression Testing**: Re-test after fixes
3. **Version 0.1.5**: Hotfix release if needed
4. **Extended Testing**: More thorough validation before next release

---

**REMEMBER**: This is real-world validation with actual user hardware. Focus on practical functionality over theoretical perfection. 