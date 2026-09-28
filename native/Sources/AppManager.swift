import Foundation
import AppKit

class AppManager {
    
    /// Launch or activate an application by name or bundle identifier using /usr/bin/open -a
    static func openApp(name: String) -> Result<[String: AnyValue], Error> {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/open")
        process.arguments = ["-a", name]
        
        do {
            try process.run()
            process.waitUntilExit()
            
            if process.terminationStatus == 0 {
                // Brief pause to allow window server focus transition
                Thread.sleep(forTimeInterval: 0.15)
                
                let active = NSWorkspace.shared.frontmostApplication
                let result: [String: AnyValue] = [
                    "name": .string(active?.localizedName ?? name),
                    "bundle_id": .string(active?.bundleIdentifier ?? ""),
                    "pid": .int(Int(active?.processIdentifier ?? 0)),
                    "status": .string("Launched \(name)")
                ]
                return .success(result)
            } else {
                return .failure(NSError(
                    domain: "AppManager",
                    code: Int(process.terminationStatus),
                    userInfo: [NSLocalizedDescriptionKey: "Application '\(name)' not found or failed to open."]
                ))
            }
        } catch {
            return .failure(error)
        }
    }
    
    /// Get currently frontmost/active application details
    static func getActiveApp() -> Result<[String: AnyValue], Error> {
        guard let frontApp = NSWorkspace.shared.frontmostApplication else {
            return .failure(NSError(domain: "AppManager", code: 2, userInfo: [NSLocalizedDescriptionKey: "No active application found"]))
        }
        
        let result: [String: AnyValue] = [
            "name": .string(frontApp.localizedName ?? "Unknown"),
            "bundle_id": .string(frontApp.bundleIdentifier ?? ""),
            "pid": .int(Int(frontApp.processIdentifier))
        ]
        
        return .success(result)
    }
}
