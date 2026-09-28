import Foundation
import CoreGraphics
import ScreenCaptureKit
import AppKit

class ScreenCapture {
    
    /// Capture screenshot and return base64 encoded string
    /// - Parameters:
    ///   - quality: JPEG compression quality (0.0 to 1.0)
    ///   - scale: Downscale factor (1.0 = native size)
    /// - Returns: A dictionary with base64 string and dimensions, or an error string
    static func captureScreenshot(quality: CGFloat = 0.8, scale: CGFloat = 1.0) async -> Result<[String: AnyValue], Error> {
        
        // Ensure Screen Recording permission
        guard CGPreflightScreenCaptureAccess() else {
            // If we don't have access, request it. Note: this might show a prompt to the user
            CGRequestScreenCaptureAccess()
            return .failure(NSError(domain: "ScreenCapture", code: 1, userInfo: [NSLocalizedDescriptionKey: "Screen Recording permission not granted. Please grant access in System Settings > Privacy & Security > Screen Recording."]))
        }
        
        do {
            // Get available shareable content (displays, windows, apps)
            let shareableContent = try await SCShareableContent.current
            
            // We want the main display
            guard let mainDisplay = shareableContent.displays.first else {
                return .failure(NSError(domain: "ScreenCapture", code: 2, userInfo: [NSLocalizedDescriptionKey: "No displays found"]))
            }
            
            // Create a content filter for the main display, excluding nothing
            let filter = SCContentFilter(display: mainDisplay, excludingWindows: [])
            
            // Configure the capture stream
            let configuration = SCStreamConfiguration()
            configuration.width = Int(CGFloat(mainDisplay.width) * scale)
            configuration.height = Int(CGFloat(mainDisplay.height) * scale)
            configuration.showsCursor = true
            
            // Capture the image using one-shot API (macOS 14.0+)
            let cgImage = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: configuration)
            
            // Convert to JPEG data
            guard let data = imageToJPEGData(image: cgImage, quality: quality) else {
                return .failure(NSError(domain: "ScreenCapture", code: 3, userInfo: [NSLocalizedDescriptionKey: "Failed to encode image to JPEG"]))
            }
            
            // Encode as base64
            let base64String = data.base64EncodedString()
            
            // Return result
            let resultData: [String: AnyValue] = [
                "base64": .string(base64String),
                "width": .int(cgImage.width),
                "height": .int(cgImage.height)
            ]
            
            return .success(resultData)
            
        } catch {
            // Fallback to older API if ScreenCaptureKit fails
            return captureScreenshotLegacy(quality: quality, scale: scale)
        }
    }
    
    /// Legacy fallback using CGWindowListCreateImage
    private static func captureScreenshotLegacy(quality: CGFloat, scale: CGFloat) -> Result<[String: AnyValue], Error> {
        let displayID = CGMainDisplayID()
        let rect = CGDisplayBounds(displayID)
        
        guard let cgImage = CGDisplayCreateImage(displayID, rect: rect) else {
            return .failure(NSError(domain: "ScreenCapture", code: 4, userInfo: [NSLocalizedDescriptionKey: "Legacy capture failed"]))
        }
        
        // Handle scaling for legacy (if needed)
        let finalImage = cgImage
        if scale != 1.0 {
            // A simple approach for legacy is to just use the raw image and let the client scale
            // or we'd need to draw into a new CGContext to scale it. Let's just use raw for fallback.
        }
        
        guard let data = imageToJPEGData(image: finalImage, quality: quality) else {
            return .failure(NSError(domain: "ScreenCapture", code: 3, userInfo: [NSLocalizedDescriptionKey: "Failed to encode image to JPEG"]))
        }
        
        let base64String = data.base64EncodedString()
        
        let resultData: [String: AnyValue] = [
            "base64": .string(base64String),
            "width": .int(finalImage.width),
            "height": .int(finalImage.height)
        ]
        
        return .success(resultData)
    }
    
    /// Helper to convert CGImage to JPEG Data
    private static func imageToJPEGData(image: CGImage, quality: CGFloat) -> Data? {
        let bitmapRep = NSBitmapImageRep(cgImage: image)
        return bitmapRep.representation(using: .jpeg, properties: [.compressionFactor: quality])
    }
}
