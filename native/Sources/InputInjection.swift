import Foundation
import CoreGraphics
import ApplicationServices

class InputInjection {
    
    /// Check if the process has Accessibility permissions required for input injection
    static func checkPermissions() -> Bool {
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true]
        return AXIsProcessTrustedWithOptions(options as CFDictionary)
    }
    
    // MARK: - Mouse Simulation
    
    /// Move the mouse cursor to a specific coordinate
    static func mouseMove(x: CGFloat, y: CGFloat) -> Result<Void, Error> {
        guard checkPermissions() else {
            return .failure(NSError(domain: "InputInjection", code: 1, userInfo: [NSLocalizedDescriptionKey: "Accessibility permission not granted"]))
        }
        
        let point = CGPoint(x: x, y: y)
        guard let event = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left) else {
            return .failure(NSError(domain: "InputInjection", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to create mouse move event"]))
        }
        
        event.post(tap: .cghidEventTap)
        return .success(())
    }
    
    /// Perform a mouse click
    /// - Parameters:
    ///   - button: "left", "right", "center"
    ///   - clickCount: 1 for single, 2 for double, 3 for triple
    static func mouseClick(x: CGFloat, y: CGFloat, button: String = "left", clickCount: Int = 1) -> Result<Void, Error> {
        guard checkPermissions() else {
            return .failure(NSError(domain: "InputInjection", code: 1, userInfo: [NSLocalizedDescriptionKey: "Accessibility permission not granted"]))
        }
        
        let point = CGPoint(x: x, y: y)
        let downType: CGEventType
        let upType: CGEventType
        let mouseButton: CGMouseButton
        
        switch button.lowercased() {
        case "right":
            downType = .rightMouseDown
            upType = .rightMouseUp
            mouseButton = .right
        case "center", "middle":
            downType = .otherMouseDown
            upType = .otherMouseUp
            mouseButton = .center
        default:
            downType = .leftMouseDown
            upType = .leftMouseUp
            mouseButton = .left
        }
        
        // Post down event
        guard let downEvent = CGEvent(mouseEventSource: nil, mouseType: downType, mouseCursorPosition: point, mouseButton: mouseButton) else {
            return .failure(NSError(domain: "InputInjection", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to create mouse down event"]))
        }
        downEvent.setIntegerValueField(.mouseEventClickState, value: Int64(clickCount))
        downEvent.post(tap: .cghidEventTap)
        
        // Small delay between down and up
        Thread.sleep(forTimeInterval: 0.05)
        
        // Post up event
        guard let upEvent = CGEvent(mouseEventSource: nil, mouseType: upType, mouseCursorPosition: point, mouseButton: mouseButton) else {
            return .failure(NSError(domain: "InputInjection", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to create mouse up event"]))
        }
        upEvent.setIntegerValueField(.mouseEventClickState, value: Int64(clickCount))
        upEvent.post(tap: .cghidEventTap)
        
        return .success(())
    }
    
    /// Perform a click and drag
    static func mouseDrag(fromX: CGFloat, fromY: CGFloat, toX: CGFloat, toY: CGFloat, button: String = "left") -> Result<Void, Error> {
        guard checkPermissions() else {
            return .failure(NSError(domain: "InputInjection", code: 1, userInfo: [NSLocalizedDescriptionKey: "Accessibility permission not granted"]))
        }
        
        let fromPoint = CGPoint(x: fromX, y: fromY)
        let toPoint = CGPoint(x: toX, y: toY)
        
        let downType: CGEventType
        let dragType: CGEventType
        let upType: CGEventType
        let mouseButton: CGMouseButton
        
        switch button.lowercased() {
        case "right":
            downType = .rightMouseDown
            dragType = .rightMouseDragged
            upType = .rightMouseUp
            mouseButton = .right
        case "center", "middle":
            downType = .otherMouseDown
            dragType = .otherMouseDragged
            upType = .otherMouseUp
            mouseButton = .center
        default:
            downType = .leftMouseDown
            dragType = .leftMouseDragged
            upType = .leftMouseUp
            mouseButton = .left
        }
        
        // Move to start position
        guard let moveEvent = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: fromPoint, mouseButton: .left) else {
            return .failure(NSError(domain: "InputInjection", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to create move event"]))
        }
        moveEvent.post(tap: .cghidEventTap)
        Thread.sleep(forTimeInterval: 0.05)
        
        // Mouse Down
        guard let downEvent = CGEvent(mouseEventSource: nil, mouseType: downType, mouseCursorPosition: fromPoint, mouseButton: mouseButton) else {
            return .failure(NSError(domain: "InputInjection", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to create mouse down event"]))
        }
        downEvent.post(tap: .cghidEventTap)
        Thread.sleep(forTimeInterval: 0.05)
        
        // Intermediate interpolation for smooth drag
        let steps = 10
        for i in 1...steps {
            let intermediateX = fromX + (toX - fromX) * (CGFloat(i) / CGFloat(steps))
            let intermediateY = fromY + (toY - fromY) * (CGFloat(i) / CGFloat(steps))
            let intermediatePoint = CGPoint(x: intermediateX, y: intermediateY)
            
            if let dragEvent = CGEvent(mouseEventSource: nil, mouseType: dragType, mouseCursorPosition: intermediatePoint, mouseButton: mouseButton) {
                dragEvent.post(tap: .cghidEventTap)
            }
            Thread.sleep(forTimeInterval: 0.01)
        }
        
        // Mouse Up
        guard let upEvent = CGEvent(mouseEventSource: nil, mouseType: upType, mouseCursorPosition: toPoint, mouseButton: mouseButton) else {
            return .failure(NSError(domain: "InputInjection", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to create mouse up event"]))
        }
        upEvent.post(tap: .cghidEventTap)
        
        return .success(())
    }
    
    /// Scroll the mouse wheel
    static func scroll(x: CGFloat, y: CGFloat, deltaX: Int32, deltaY: Int32) -> Result<Void, Error> {
        guard checkPermissions() else {
            return .failure(NSError(domain: "InputInjection", code: 1, userInfo: [NSLocalizedDescriptionKey: "Accessibility permission not granted"]))
        }
        
        // First move to the location
        let point = CGPoint(x: x, y: y)
        guard let moveEvent = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left) else {
            return .failure(NSError(domain: "InputInjection", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to create move event"]))
        }
        moveEvent.post(tap: .cghidEventTap)
        Thread.sleep(forTimeInterval: 0.02)
        
        // Then scroll (units: pixel scroll)
        guard let scrollEvent = CGEvent(scrollWheelEvent2Source: nil, units: .pixel, wheelCount: 2, wheel1: deltaY, wheel2: deltaX, wheel3: 0) else {
            return .failure(NSError(domain: "InputInjection", code: 2, userInfo: [NSLocalizedDescriptionKey: "Failed to create scroll event"]))
        }
        
        scrollEvent.post(tap: .cghidEventTap)
        return .success(())
    }
    
    // MARK: - Keyboard Simulation
    
    /// Type Unicode text directly using CGEventKeyboardSetUnicodeString
    /// Supports all Unicode characters, emojis, accents, and symbols regardless of keyboard layout
    static func typeText(_ text: String) -> Result<Void, Error> {
        guard checkPermissions() else {
            return .failure(NSError(domain: "InputInjection", code: 1, userInfo: [NSLocalizedDescriptionKey: "Accessibility permission not granted"]))
        }
        
        for char in text {
            let utf16Chars = Array(String(char).utf16)
            
            // Create a virtual key down event
            guard let keyDown = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: true),
                  let keyUp = CGEvent(keyboardEventSource: nil, virtualKey: 0, keyDown: false) else {
                return .failure(NSError(domain: "InputInjection", code: 3, userInfo: [NSLocalizedDescriptionKey: "Failed to create keyboard event"]))
            }
            
            utf16Chars.withUnsafeBufferPointer { ptr in
                guard let baseAddress = ptr.baseAddress else { return }
                keyDown.keyboardSetUnicodeString(stringLength: utf16Chars.count, unicodeString: baseAddress)
                keyUp.keyboardSetUnicodeString(stringLength: utf16Chars.count, unicodeString: baseAddress)
            }
            
            keyDown.post(tap: .cghidEventTap)
            Thread.sleep(forTimeInterval: 0.005)
            keyUp.post(tap: .cghidEventTap)
            Thread.sleep(forTimeInterval: 0.01)
        }
        
        return .success(())
    }
    
    /// Press a specific key with optional modifier keys (e.g. key: "c", modifiers: ["cmd"])
    static func pressKey(key: String, modifiers: [String] = []) -> Result<Void, Error> {
        guard checkPermissions() else {
            return .failure(NSError(domain: "InputInjection", code: 1, userInfo: [NSLocalizedDescriptionKey: "Accessibility permission not granted"]))
        }
        
        guard let keyCode = resolveKeyCode(key.lowercased()) else {
            return .failure(NSError(domain: "InputInjection", code: 4, userInfo: [NSLocalizedDescriptionKey: "Unknown key identifier: '\(key)'"]))
        }
        
        var flags = CGEventFlags()
        for mod in modifiers {
            switch mod.lowercased() {
            case "cmd", "command":
                flags.insert(.maskCommand)
            case "shift":
                flags.insert(.maskShift)
            case "alt", "option", "opt":
                flags.insert(.maskAlternate)
            case "ctrl", "control":
                flags.insert(.maskControl)
            case "fn":
                flags.insert(.maskSecondaryFn)
            default:
                break
            }
        }
        
        guard let keyDown = CGEvent(keyboardEventSource: nil, virtualKey: keyCode, keyDown: true),
              let keyUp = CGEvent(keyboardEventSource: nil, virtualKey: keyCode, keyDown: false) else {
            return .failure(NSError(domain: "InputInjection", code: 5, userInfo: [NSLocalizedDescriptionKey: "Failed to create key event for code \(keyCode)"]))
        }
        
        if !flags.isEmpty {
            keyDown.flags = flags
            keyUp.flags = flags
        }
        
        keyDown.post(tap: .cghidEventTap)
        Thread.sleep(forTimeInterval: 0.02)
        keyUp.post(tap: .cghidEventTap)
        
        return .success(())
    }
    
    // MARK: - Keycode Resolution Table
    
    private static func resolveKeyCode(_ key: String) -> CGKeyCode? {
        let mapping: [String: CGKeyCode] = [
            // Alphabet
            "a": 0x00, "b": 0x0B, "c": 0x08, "d": 0x02, "e": 0x0E, "f": 0x03, "g": 0x05,
            "h": 0x04, "i": 0x22, "j": 0x26, "k": 0x28, "l": 0x25, "m": 0x2E, "n": 0x2D,
            "o": 0x1F, "p": 0x23, "q": 0x0C, "r": 0x0F, "s": 0x01, "t": 0x11, "u": 0x20,
            "v": 0x09, "w": 0x0D, "x": 0x07, "y": 0x10, "z": 0x06,
            
            // Numbers
            "0": 0x1D, "1": 0x12, "2": 0x13, "3": 0x14, "4": 0x15,
            "5": 0x17, "6": 0x16, "7": 0x1A, "8": 0x1C, "9": 0x19,
            
            // Control Keys
            "return": 0x24, "enter": 0x24,
            "tab": 0x30,
            "space": 0x31,
            "backspace": 0x33, "delete": 0x33,
            "escape": 0x35, "esc": 0x35,
            "command": 0x37, "cmd": 0x37,
            "shift": 0x38,
            "capslock": 0x39,
            "option": 0x3A, "alt": 0x3A,
            "control": 0x3B, "ctrl": 0x3B,
            
            // Navigation & Arrows
            "left": 0x7B, "arrow_left": 0x7B,
            "right": 0x7C, "arrow_right": 0x7C,
            "down": 0x7D, "arrow_down": 0x7D,
            "up": 0x7E, "arrow_up": 0x7E,
            "home": 0x73,
            "end": 0x77,
            "pageup": 0x74,
            "pagedown": 0x79,
            "forwarddelete": 0x75,
            
            // Function Keys
            "f1": 0x7A, "f2": 0x78, "f3": 0x63, "f4": 0x76,
            "f5": 0x60, "f6": 0x61, "f7": 0x62, "f8": 0x64,
            "f9": 0x65, "f10": 0x6D, "f11": 0x67, "f12": 0x6F
        ]
        
        return mapping[key]
    }
}
