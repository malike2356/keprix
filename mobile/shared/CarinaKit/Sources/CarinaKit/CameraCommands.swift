import Foundation

public enum CarinaCameraCommand: String, Codable, Sendable {
    case list = "camera.list"
    case snap = "camera.snap"
    case clip = "camera.clip"
}

public enum CarinaCameraFacing: String, Codable, Sendable {
    case back
    case front
}

public enum CarinaCameraImageFormat: String, Codable, Sendable {
    case jpg
    case jpeg
}

public enum CarinaCameraVideoFormat: String, Codable, Sendable {
    case mp4
}

public struct CarinaCameraSnapParams: Codable, Sendable, Equatable {
    public var facing: CarinaCameraFacing?
    public var maxWidth: Int?
    public var quality: Double?
    public var format: CarinaCameraImageFormat?
    public var deviceId: String?
    public var delayMs: Int?

    public init(
        facing: CarinaCameraFacing? = nil,
        maxWidth: Int? = nil,
        quality: Double? = nil,
        format: CarinaCameraImageFormat? = nil,
        deviceId: String? = nil,
        delayMs: Int? = nil)
    {
        self.facing = facing
        self.maxWidth = maxWidth
        self.quality = quality
        self.format = format
        self.deviceId = deviceId
        self.delayMs = delayMs
    }
}

public struct CarinaCameraClipParams: Codable, Sendable, Equatable {
    public var facing: CarinaCameraFacing?
    public var durationMs: Int?
    public var includeAudio: Bool?
    public var format: CarinaCameraVideoFormat?
    public var deviceId: String?

    public init(
        facing: CarinaCameraFacing? = nil,
        durationMs: Int? = nil,
        includeAudio: Bool? = nil,
        format: CarinaCameraVideoFormat? = nil,
        deviceId: String? = nil)
    {
        self.facing = facing
        self.durationMs = durationMs
        self.includeAudio = includeAudio
        self.format = format
        self.deviceId = deviceId
    }
}
