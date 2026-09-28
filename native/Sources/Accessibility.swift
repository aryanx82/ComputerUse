import Foundation
import ApplicationServices
import AppKit

class AccessibilityManager {
    
    /// Check if Accessibility API is enabled
    static func isTrusted() -> Bool {
        return AXIsProcessTrusted()
    }
    
    /// Get the UI tree for the frontmost application or system-wide
    /// - Parameters:
    ///   - maxDepth: Max depth of hierarchy traversal
    ///   - maxChildren: Max children to inspect per container node
    static func getUITree(maxDepth: Int = 8, maxChildren: Int = 20) -> Result<[String: AnyValue], Error> {
        guard isTrusted() else {
            return .failure(NSError(domain: "Accessibility", code: 1, userInfo: [NSLocalizedDescriptionKey: "Accessibility permissions not granted. Enable in System Settings > Privacy & Security > Accessibility."]))
        }
        
        // Get frontmost application
        guard let frontApp = NSWorkspace.shared.frontmostApplication else {
            return .failure(NSError(domain: "Accessibility", code: 2, userInfo: [NSLocalizedDescriptionKey: "No frontmost application found"]))
        }
        
        let appElement = AXUIElementCreateApplication(frontApp.processIdentifier)
        
        // Set timeout to 1.5 seconds to prevent hanging on unresponsive apps
        AXUIElementSetMessagingTimeout(appElement, 1.5)
        
        var tree = dumpElement(appElement, depth: 0, maxDepth: maxDepth, maxChildren: maxChildren)
        tree["app_name"] = .string(frontApp.localizedName ?? "Unknown")
        tree["bundle_id"] = .string(frontApp.bundleIdentifier ?? "")
        tree["pid"] = .int(Int(frontApp.processIdentifier))
        
        return .success(tree)
    }
    
    /// Recursive function to serialize an AXUIElement into a dictionary
    private static func dumpElement(_ element: AXUIElement, depth: Int, maxDepth: Int, maxChildren: Int) -> [String: AnyValue] {
        var node: [String: AnyValue] = [:]
        
        // Role
        if let role = getAttributeString(element, attribute: kAXRoleAttribute) {
            node["role"] = .string(role)
        }
        
        // Title / Label
        if let title = getAttributeString(element, attribute: kAXTitleAttribute), !title.isEmpty {
            node["title"] = .string(title)
        } else if let desc = getAttributeString(element, attribute: kAXDescriptionAttribute), !desc.isEmpty {
            node["description"] = .string(desc)
        }
        
        // Value (e.g. textfield content)
        if let value = getAttributeString(element, attribute: kAXValueAttribute), !value.isEmpty {
            // Truncate long value strings
            let truncated = value.count > 100 ? String(value.prefix(100)) + "..." : value
            node["value"] = .string(truncated)
        }
        
        // Frame / Bounds (x, y, width, height)
        if let frame = getElementBounds(element) {
            node["bounds"] = .object([
                "x": .double(Double(frame.origin.x)),
                "y": .double(Double(frame.origin.y)),
                "width": .double(Double(frame.size.width)),
                "height": .double(Double(frame.size.height))
            ])
        }
        
        // Enabled / Focused
        if let enabled = getAttributeBool(element, attribute: kAXEnabledAttribute) {
            node["enabled"] = .bool(enabled)
        }
        if let focused = getAttributeBool(element, attribute: kAXFocusedAttribute), focused {
            node["focused"] = .bool(true)
        }
        
        // Children (if within maxDepth)
        if depth < maxDepth {
            var childrenRef: CFTypeRef?
            let result = AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &childrenRef)
            
            if result == .success, let children = childrenRef as? [AXUIElement], !children.isEmpty {
                var childNodes: [AnyValue] = []
                let count = min(children.count, maxChildren)
                for i in 0..<count {
                    let childDict = dumpElement(children[i], depth: depth + 1, maxDepth: maxDepth, maxChildren: maxChildren)
                    // Only keep non-empty children
                    if !childDict.isEmpty {
                        childNodes.append(.object(childDict))
                    }
                }
                if !childNodes.isEmpty {
                    node["children"] = .array(childNodes)
                }
            }
        }
        
        return node
    }
    
    // MARK: - Attribute Helpers
    
    private static func getAttributeString(_ element: AXUIElement, attribute: String) -> String? {
        var valueRef: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(element, attribute as CFString, &valueRef)
        guard result == .success, let value = valueRef else { return nil }
        
        if let str = value as? String {
            return str
        } else if let attrStr = value as? NSAttributedString {
            return attrStr.string
        }
        return nil
    }
    
    private static func getAttributeBool(_ element: AXUIElement, attribute: String) -> Bool? {
        var valueRef: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(element, attribute as CFString, &valueRef)
        guard result == .success, let value = valueRef as? Bool else { return nil }
        return value
    }
    
    private static func getElementBounds(_ element: AXUIElement) -> CGRect? {
        var posRef: CFTypeRef?
        var sizeRef: CFTypeRef?
        
        guard AXUIElementCopyAttributeValue(element, kAXPositionAttribute as CFString, &posRef) == .success,
              AXUIElementCopyAttributeValue(element, kAXSizeAttribute as CFString, &sizeRef) == .success,
              let posVal = posRef, let sizeVal = sizeRef else {
            return nil
        }
        
        var point = CGPoint.zero
        var size = CGSize.zero
        
        if CFGetTypeID(posVal) == AXValueGetTypeID() {
            AXValueGetValue(posVal as! AXValue, .cgPoint, &point)
        }
        if CFGetTypeID(sizeVal) == AXValueGetTypeID() {
            AXValueGetValue(sizeVal as! AXValue, .cgSize, &size)
        }
        
        // Filter out zero size or off-screen frames
        if size.width <= 0 || size.height <= 0 {
            return nil
        }
        
        return CGRect(origin: point, size: size)
    }
}
