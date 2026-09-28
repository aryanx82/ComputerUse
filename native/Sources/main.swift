import Foundation

// MARK: - Logging Helper

func logError(_ message: String) {
    let msg = "[\(Date().description)] ERROR: \(message)\n"
    if let data = msg.data(using: .utf8) {
        FileHandle.standardError.write(data)
    }
}

func logInfo(_ message: String) {
    let msg = "[\(Date().description)] INFO: \(message)\n"
    if let data = msg.data(using: .utf8) {
        FileHandle.standardError.write(data)
    }
}

// MARK: - Server Configuration

let socketDir = NSHomeDirectory().appending("/.computer-use-tool")
let socketPath = socketDir.appending("/daemon.sock")

// Ensure directory exists
let fileManager = FileManager.default
if !fileManager.fileExists(atPath: socketDir) {
    do {
        try fileManager.createDirectory(atPath: socketDir, withIntermediateDirectories: true, attributes: nil)
        logInfo("Created socket directory at \(socketDir)")
    } catch {
        logError("Failed to create socket directory: \(error)")
        exit(1)
    }
}

// Remove old socket if exists
if fileManager.fileExists(atPath: socketPath) {
    do {
        try fileManager.removeItem(atPath: socketPath)
        logInfo("Removed stale socket at \(socketPath)")
    } catch {
        logError("Failed to remove stale socket: \(error)")
        exit(1)
    }
}

// Check Accessibility permissions on startup
if !InputInjection.checkPermissions() {
    logError("Accessibility permissions not granted! Input injection will fail.")
    logError("Please grant access in System Settings > Privacy & Security > Accessibility.")
} else {
    logInfo("Accessibility permissions granted.")
}

// MARK: - Socket Setup

let serverSocket = socket(AF_UNIX, SOCK_STREAM, 0)
guard serverSocket >= 0 else {
    logError("Failed to create socket: \(String(cString: strerror(errno)))")
    exit(1)
}

var serverAddress = sockaddr_un()
serverAddress.sun_family = sa_family_t(AF_UNIX)

let pathLength = socketPath.utf8.count
guard pathLength < MemoryLayout.size(ofValue: serverAddress.sun_path) else {
    logError("Socket path too long")
    exit(1)
}

_ = withUnsafeMutablePointer(to: &serverAddress.sun_path.0) { ptr in
    socketPath.withCString { cString in
        strncpy(ptr, cString, pathLength)
    }
}

let addressLength = socklen_t(MemoryLayout.offset(of: \sockaddr_un.sun_path)! + pathLength)

let bindResult = withUnsafePointer(to: &serverAddress) {
    $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
        bind(serverSocket, $0, addressLength)
    }
}

guard bindResult == 0 else {
    logError("Failed to bind socket: \(String(cString: strerror(errno)))")
    exit(1)
}

guard listen(serverSocket, 5) == 0 else {
    logError("Failed to listen on socket: \(String(cString: strerror(errno)))")
    exit(1)
}

logInfo("Server listening on \(socketPath)")

// Setup clean shutdown
let cleanupSocket = {
    logInfo("Shutting down server, removing socket...")
    try? FileManager.default.removeItem(atPath: socketPath)
}

signal(SIGINT) { _ in
    cleanupSocket()
    exit(0)
}
signal(SIGTERM) { _ in
    cleanupSocket()
    exit(0)
}

// MARK: - Main Loop

let jsonDecoder = JSONDecoder()
let jsonEncoder = JSONEncoder()

// Run a background queue for accepting clients so we can use Task/async handlers for screenshots
let clientQueue = DispatchQueue(label: "com.computer-use.daemon.clientQueue")

// Handle client in an async Task per connection
@Sendable func handleClientConnection(_ clientSocket: Int32) async {
    defer {
        close(clientSocket)
        logInfo("Client disconnected")
    }
    
    var currentData = Data()
    var buffer = [UInt8](repeating: 0, count: 65536)
    
    while true {
        let bytesRead = read(clientSocket, &buffer, buffer.count)
        if bytesRead <= 0 {
            break // EOF or error
        }
        
        currentData.append(buffer, count: bytesRead)
        
        // Process all complete lines (delimited by \n)
        while let newlineIndex = currentData.firstIndex(of: 0x0A) {
            let lineData = currentData.prefix(upTo: newlineIndex)
            currentData.removeSubrange(0...newlineIndex)
            
            if lineData.isEmpty {
                continue
            }
            
            do {
                let request = try jsonDecoder.decode(Request.self, from: lineData)
                logInfo("Received request: \(request.action) (ID: \(request.id))")
                
                let response = await handleRequest(request)
                let responseData = try jsonEncoder.encode(response)
                
                var outputData = responseData
                outputData.append(0x0A) // '\n'
                
                // Write all response bytes using POSIX write
                outputData.withUnsafeBytes { rawBuffer in
                    guard let ptr = rawBuffer.baseAddress else { return }
                    var totalWritten = 0
                    let totalLength = outputData.count
                    while totalWritten < totalLength {
                        let written = write(clientSocket, ptr + totalWritten, totalLength - totalWritten)
                        if written <= 0 {
                            logError("Failed to write response to client socket")
                            break
                        }
                        totalWritten += written
                    }
                }
                logInfo("Sent response for ID: \(request.id)")
            } catch {
                logError("Failed to decode JSON: \(error) - Data: \(String(data: lineData, encoding: .utf8) ?? "")")
            }
        }
    }
}

clientQueue.async {
    while true {
        let clientSocket = accept(serverSocket, nil, nil)
        guard clientSocket >= 0 else {
            logError("Failed to accept client connection: \(String(cString: strerror(errno)))")
            continue
        }
        
        logInfo("Client connected")
        Task {
            await handleClientConnection(clientSocket)
        }
    }
}

// Keep main thread alive
RunLoop.main.run()

// MARK: - Request Handler

@Sendable func handleRequest(_ request: Request) async -> Response {
    var response: Response
    
    switch request.action {
        
    case "screenshot":
        let scale = request.params["scale"]?.asDouble ?? 1.0
        let quality = request.params["quality"]?.asDouble ?? 0.8
        
        let result = await ScreenCapture.captureScreenshot(quality: CGFloat(quality), scale: CGFloat(scale))
        
        switch result {
        case .success(let data):
            response = createSuccessResponse(id: request.id, data: data)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    case "mouseMove":
        guard let x = request.params["x"]?.asDouble, let y = request.params["y"]?.asDouble else {
            return createErrorResponse(id: request.id, error: "Missing x or y parameters")
        }
        
        let result = InputInjection.mouseMove(x: CGFloat(x), y: CGFloat(y))
        switch result {
        case .success:
            response = createSuccessResponse(id: request.id)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    case "mouseClick":
        guard let x = request.params["x"]?.asDouble, let y = request.params["y"]?.asDouble else {
            return createErrorResponse(id: request.id, error: "Missing x or y parameters")
        }
        
        let button = request.params["button"]?.asString ?? "left"
        let clickCount = request.params["clickCount"]?.asInt ?? 1
        
        let result = InputInjection.mouseClick(x: CGFloat(x), y: CGFloat(y), button: button, clickCount: clickCount)
        switch result {
        case .success:
            response = createSuccessResponse(id: request.id)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    case "mouseDrag":
        guard let fromX = request.params["fromX"]?.asDouble,
              let fromY = request.params["fromY"]?.asDouble,
              let toX = request.params["toX"]?.asDouble,
              let toY = request.params["toY"]?.asDouble else {
            return createErrorResponse(id: request.id, error: "Missing fromX, fromY, toX, or toY parameters")
        }
        
        let button = request.params["button"]?.asString ?? "left"
        
        let result = InputInjection.mouseDrag(fromX: CGFloat(fromX), fromY: CGFloat(fromY), toX: CGFloat(toX), toY: CGFloat(toY), button: button)
        switch result {
        case .success:
            response = createSuccessResponse(id: request.id)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    case "scroll":
        guard let x = request.params["x"]?.asDouble,
              let y = request.params["y"]?.asDouble,
              let deltaX = request.params["deltaX"]?.asInt,
              let deltaY = request.params["deltaY"]?.asInt else {
            return createErrorResponse(id: request.id, error: "Missing x, y, deltaX, or deltaY parameters")
        }
        
        let result = InputInjection.scroll(x: CGFloat(x), y: CGFloat(y), deltaX: Int32(deltaX), deltaY: Int32(deltaY))
        switch result {
        case .success:
            response = createSuccessResponse(id: request.id)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    case "typeText":
        guard let text = request.params["text"]?.asString else {
            return createErrorResponse(id: request.id, error: "Missing 'text' parameter for typeText")
        }
        
        let result = InputInjection.typeText(text)
        switch result {
        case .success:
            response = createSuccessResponse(id: request.id)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    case "pressKey":
        guard let key = request.params["key"]?.asString else {
            return createErrorResponse(id: request.id, error: "Missing 'key' parameter for pressKey")
        }
        
        var modifiers: [String] = []
        if case .array(let modValues) = request.params["modifiers"] {
            for m in modValues {
                if let str = m.asString {
                    modifiers.append(str)
                }
            }
        } else if let modStr = request.params["modifiers"]?.asString {
            modifiers = modStr.split(separator: "+").map { String($0).trimmingCharacters(in: .whitespaces) }
        }
        
        let result = InputInjection.pressKey(key: key, modifiers: modifiers)
        switch result {
        case .success:
            response = createSuccessResponse(id: request.id)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    case "getUITree":
        let maxDepth = request.params["maxDepth"]?.asInt ?? 8
        let maxChildren = request.params["maxChildren"]?.asInt ?? 25
        
        let result = AccessibilityManager.getUITree(maxDepth: maxDepth, maxChildren: maxChildren)
        switch result {
        case .success(let tree):
            response = createSuccessResponse(id: request.id, data: tree)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    case "openApp":
        guard let name = request.params["name"]?.asString else {
            return createErrorResponse(id: request.id, error: "Missing 'name' parameter for openApp")
        }
        
        let result = AppManager.openApp(name: name)
        switch result {
        case .success(let appData):
            response = createSuccessResponse(id: request.id, data: appData)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    case "getActiveApp":
        let result = AppManager.getActiveApp()
        switch result {
        case .success(let appData):
            response = createSuccessResponse(id: request.id, data: appData)
        case .failure(let error):
            response = createErrorResponse(id: request.id, error: error.localizedDescription)
        }
        
    default:
        return createErrorResponse(id: request.id, error: "Unknown action: \(request.action)")
    }
    
    // Auto-screenshot compound pattern:
    // If the caller requested returnScreenshot = true and the action succeeded, attach a fresh screenshot!
    if response.success && request.params["returnScreenshot"]?.asBool == true {
        try? await Task.sleep(nanoseconds: 200_000_000) // 200ms debounce for UI repaint
        let shotResult = await ScreenCapture.captureScreenshot(quality: 0.8, scale: 0.5)
        if case .success(let shotData) = shotResult {
            var mergedData = response.data ?? [:]
            mergedData["screenshot"] = .object(shotData)
            response = createSuccessResponse(id: request.id, data: mergedData)
        }
    }
    
    return response
}
