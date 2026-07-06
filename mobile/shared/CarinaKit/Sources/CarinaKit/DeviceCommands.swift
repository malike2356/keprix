import Foundation

public enum CarinaDeviceCommand: String, Codable, Sendable {
    case status = "device.status"
    case info = "device.info"
}

public enum CarinaBatteryState: String, Codable, Sendable {
    case unknown
    case unplugged
    case charging
    case full
}

public enum CarinaThermalState: String, Codable, Sendable {
    case nominal
    case fair
    case serious
    case critical
}

public enum CarinaNetworkPathStatus: String, Codable, Sendable {
    case satisfied
    case unsatisfied
    case requiresConnection
}

public enum CarinaNetworkInterfaceType: String, Codable, Sendable {
    case wifi
    case cellular
    case wired
    case other
}

public struct CarinaBatteryStatusPayload: Codable, Sendable, Equatable {
    public var level: Double?
    public var state: CarinaBatteryState
    public var lowPowerModeEnabled: Bool

    public init(level: Double?, state: CarinaBatteryState, lowPowerModeEnabled: Bool) {
        self.level = level
        self.state = state
        self.lowPowerModeEnabled = lowPowerModeEnabled
    }
}

public struct CarinaThermalStatusPayload: Codable, Sendable, Equatable {
    public var state: CarinaThermalState

    public init(state: CarinaThermalState) {
        self.state = state
    }
}

public struct CarinaStorageStatusPayload: Codable, Sendable, Equatable {
    public var totalBytes: Int64
    public var freeBytes: Int64
    public var usedBytes: Int64

    public init(totalBytes: Int64, freeBytes: Int64, usedBytes: Int64) {
        self.totalBytes = totalBytes
        self.freeBytes = freeBytes
        self.usedBytes = usedBytes
    }
}

public struct CarinaNetworkStatusPayload: Codable, Sendable, Equatable {
    public var status: CarinaNetworkPathStatus
    public var isExpensive: Bool
    public var isConstrained: Bool
    public var interfaces: [CarinaNetworkInterfaceType]

    public init(
        status: CarinaNetworkPathStatus,
        isExpensive: Bool,
        isConstrained: Bool,
        interfaces: [CarinaNetworkInterfaceType])
    {
        self.status = status
        self.isExpensive = isExpensive
        self.isConstrained = isConstrained
        self.interfaces = interfaces
    }
}

public struct CarinaDeviceStatusPayload: Codable, Sendable, Equatable {
    public var battery: CarinaBatteryStatusPayload
    public var thermal: CarinaThermalStatusPayload
    public var storage: CarinaStorageStatusPayload
    public var network: CarinaNetworkStatusPayload
    public var uptimeSeconds: Double

    public init(
        battery: CarinaBatteryStatusPayload,
        thermal: CarinaThermalStatusPayload,
        storage: CarinaStorageStatusPayload,
        network: CarinaNetworkStatusPayload,
        uptimeSeconds: Double)
    {
        self.battery = battery
        self.thermal = thermal
        self.storage = storage
        self.network = network
        self.uptimeSeconds = uptimeSeconds
    }
}

public struct CarinaDeviceInfoPayload: Codable, Sendable, Equatable {
    public var deviceName: String
    public var modelIdentifier: String
    public var systemName: String
    public var systemVersion: String
    public var appVersion: String
    public var appBuild: String
    public var locale: String

    public init(
        deviceName: String,
        modelIdentifier: String,
        systemName: String,
        systemVersion: String,
        appVersion: String,
        appBuild: String,
        locale: String)
    {
        self.deviceName = deviceName
        self.modelIdentifier = modelIdentifier
        self.systemName = systemName
        self.systemVersion = systemVersion
        self.appVersion = appVersion
        self.appBuild = appBuild
        self.locale = locale
    }
}
