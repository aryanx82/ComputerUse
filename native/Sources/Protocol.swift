import Foundation

// MARK: - Protocol Definitions

/// Represents a request coming from the client
struct Request: Codable {
    /// Unique identifier for the request
    let id: String
    /// The action to perform (e.g., "screenshot", "mouseClick", "mouseMove")
    let action: String
    /// Parameters specific to the action, passed as dynamic dictionary
    let params: [String: AnyValue]
}

/// Represents a response going back to the client
struct Response: Codable {
    /// Matches the id of the request this responds to
    let id: String
    /// Whether the action was successful
    let success: Bool
    /// Optional data returned by the action (e.g., base64 image)
    let data: [String: AnyValue]?
    /// Optional error message if success is false
    let error: String?
}

// MARK: - Helper Types

/// A type-erased wrapper to allow decoding arbitrary JSON objects in Codable
enum AnyValue: Codable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case null
    case array([AnyValue])
    case object([String: AnyValue])
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        
        if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode(Int.self) {
            self = .int(value)
        } else if let value = try? container.decode(Double.self) {
            self = .double(value)
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode([AnyValue].self) {
            self = .array(value)
        } else if let value = try? container.decode([String: AnyValue].self) {
            self = .object(value)
        } else if container.decodeNil() {
            self = .null
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "AnyValue value cannot be decoded")
        }
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let value):
            try container.encode(value)
        case .int(let value):
            try container.encode(value)
        case .double(let value):
            try container.encode(value)
        case .bool(let value):
            try container.encode(value)
        case .null:
            try container.encodeNil()
        case .array(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        }
    }
    
    // Convenience accessors
    var asString: String? {
        if case .string(let v) = self { return v }
        return nil
    }
    var asInt: Int? {
        if case .int(let v) = self { return v }
        if case .double(let v) = self { return Int(v) }
        return nil
    }
    var asDouble: Double? {
        if case .double(let v) = self { return v }
        if case .int(let v) = self { return Double(v) }
        return nil
    }
    var asBool: Bool? {
        if case .bool(let v) = self { return v }
        return nil
    }
}

// MARK: - Helper Functions

/// Creates a successful response object
func createSuccessResponse(id: String, data: [String: AnyValue]? = nil) -> Response {
    return Response(id: id, success: true, data: data, error: nil)
}

/// Creates an error response object
func createErrorResponse(id: String, error: String) -> Response {
    return Response(id: id, success: false, data: nil, error: error)
}
