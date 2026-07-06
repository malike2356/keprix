import CoreLocation
import Foundation
import CarinaKit
import UIKit

typealias CarinaCameraSnapResult = (format: String, base64: String, width: Int, height: Int)
typealias CarinaCameraClipResult = (format: String, base64: String, durationMs: Int, hasAudio: Bool)

protocol CameraServicing: Sendable {
    func listDevices() async -> [CameraController.CameraDeviceInfo]
    func snap(params: CarinaCameraSnapParams) async throws -> CarinaCameraSnapResult
    func clip(params: CarinaCameraClipParams) async throws -> CarinaCameraClipResult
}

protocol ScreenRecordingServicing: Sendable {
    func record(
        screenIndex: Int?,
        durationMs: Int?,
        fps: Double?,
        includeAudio: Bool?,
        outPath: String?) async throws -> String
}

@MainActor
protocol LocationServicing: Sendable {
    func authorizationStatus() -> CLAuthorizationStatus
    func accuracyAuthorization() -> CLAccuracyAuthorization
    func ensureAuthorization(mode: CarinaLocationMode) async -> CLAuthorizationStatus
    func currentLocation(
        params: CarinaLocationGetParams,
        desiredAccuracy: CarinaLocationAccuracy,
        maxAgeMs: Int?,
        timeoutMs: Int?) async throws -> CLLocation
    func startMonitoringSignificantLocationChanges(onUpdate: @escaping @Sendable (CLLocation) -> Void)
}

@MainActor
protocol DeviceStatusServicing: Sendable {
    func status() async throws -> CarinaDeviceStatusPayload
    func info() -> CarinaDeviceInfoPayload
}

protocol PhotosServicing: Sendable {
    func latest(params: CarinaPhotosLatestParams) async throws -> CarinaPhotosLatestPayload
}

protocol ContactsServicing: Sendable {
    func search(params: CarinaContactsSearchParams) async throws -> CarinaContactsSearchPayload
    func add(params: CarinaContactsAddParams) async throws -> CarinaContactsAddPayload
}

protocol CalendarServicing: Sendable {
    func events(params: CarinaCalendarEventsParams) async throws -> CarinaCalendarEventsPayload
    func add(params: CarinaCalendarAddParams) async throws -> CarinaCalendarAddPayload
}

protocol RemindersServicing: Sendable {
    func list(params: CarinaRemindersListParams) async throws -> CarinaRemindersListPayload
    func add(params: CarinaRemindersAddParams) async throws -> CarinaRemindersAddPayload
}

protocol MotionServicing: Sendable {
    func activities(params: CarinaMotionActivityParams) async throws -> CarinaMotionActivityPayload
    func pedometer(params: CarinaPedometerParams) async throws -> CarinaPedometerPayload
}

struct WatchMessagingStatus: Equatable {
    var supported: Bool
    var paired: Bool
    var appInstalled: Bool
    var reachable: Bool
    var activationState: String
}

struct WatchQuickReplyEvent: Equatable {
    var replyId: String
    var promptId: String
    var actionId: String
    var actionLabel: String?
    var sessionKey: String?
    var note: String?
    var sentAtMs: Int?
    var transport: String
}

struct WatchExecApprovalResolveEvent: Equatable {
    var replyId: String
    var approvalId: String
    var decision: CarinaWatchExecApprovalDecision
    var sentAtMs: Int?
    var transport: String
}

struct WatchExecApprovalSnapshotRequestEvent: Equatable {
    var requestId: String
    var sentAtMs: Int?
    var transport: String
}

struct WatchAppSnapshotRequestEvent: Equatable {
    var requestId: String
    var sentAtMs: Int?
    var transport: String
}

struct WatchAppCommandEvent: Codable, Equatable {
    var commandId: String
    var command: CarinaWatchAppCommand
    var sessionKey: String?
    var gatewayStableID: String?
    var text: String?
    var sentAtMs: Int?
    var transport: String
}

struct WatchNotificationSendResult: Equatable {
    var deliveredImmediately: Bool
    var queuedForDelivery: Bool
    var transport: String
}

protocol WatchMessagingServicing: AnyObject, Sendable {
    func status() async -> WatchMessagingStatus
    func setStatusHandler(_ handler: (@Sendable (WatchMessagingStatus) -> Void)?)
    func setReplyHandler(_ handler: (@Sendable (WatchQuickReplyEvent) -> Void)?)
    func setExecApprovalResolveHandler(_ handler: (@Sendable (WatchExecApprovalResolveEvent) -> Void)?)
    func setExecApprovalSnapshotRequestHandler(
        _ handler: (@Sendable (WatchExecApprovalSnapshotRequestEvent) -> Void)?)
    func setAppSnapshotRequestHandler(_ handler: (@Sendable (WatchAppSnapshotRequestEvent) -> Void)?)
    func setAppCommandHandler(_ handler: (@Sendable (WatchAppCommandEvent) -> Void)?)
    func sendNotification(
        id: String,
        params: CarinaWatchNotifyParams) async throws -> WatchNotificationSendResult
    func sendExecApprovalPrompt(
        _ message: CarinaWatchExecApprovalPromptMessage) async throws -> WatchNotificationSendResult
    func sendExecApprovalResolved(
        _ message: CarinaWatchExecApprovalResolvedMessage) async throws -> WatchNotificationSendResult
    func sendExecApprovalExpired(
        _ message: CarinaWatchExecApprovalExpiredMessage) async throws -> WatchNotificationSendResult
    func syncExecApprovalSnapshot(
        _ message: CarinaWatchExecApprovalSnapshotMessage) async throws -> WatchNotificationSendResult
    func syncAppSnapshot(
        _ message: CarinaWatchAppSnapshotMessage) async throws -> WatchNotificationSendResult
}

extension CameraController: CameraServicing {}
extension ScreenRecordService: ScreenRecordingServicing {}
extension LocationService: LocationServicing {}
