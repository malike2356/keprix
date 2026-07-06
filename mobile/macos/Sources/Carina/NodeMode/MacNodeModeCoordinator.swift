import Foundation
import CarinaKit
import OSLog

struct MacNodeGatewayTLSSessionCache {
    private struct Key: Equatable {
        let url: URL
        let required: Bool
        let expectedFingerprint: String?
        let allowTOFU: Bool
        let storeKey: String?

        init(url: URL, params: GatewayTLSParams) {
            self.url = url
            self.required = params.required
            self.expectedFingerprint = params.expectedFingerprint
            self.allowTOFU = params.allowTOFU
            self.storeKey = params.storeKey
        }
    }

    private var cachedKey: Key?
    private var cachedBox: WebSocketSessionBox?

    mutating func sessionBox(url: URL, params: GatewayTLSParams) -> WebSocketSessionBox {
        let key = Key(url: url, params: params)
        if let cachedKey = self.cachedKey, cachedKey == key, let cachedBox = self.cachedBox {
            return cachedBox
        }
        let box = WebSocketSessionBox(session: GatewayTLSPinningSession(params: params))
        self.cachedKey = key
        self.cachedBox = box
        return box
    }

    mutating func invalidate() {
        self.cachedKey = nil
        self.cachedBox = nil
    }
}

@MainActor
final class MacNodeModeCoordinator {
    static let shared = MacNodeModeCoordinator()

    private let logger = Logger(subsystem: "com.verlox.carinakeprix", category: "mac-node")
    private var task: Task<Void, Never>?
    private let runtime: MacNodeRuntime
    private let session: GatewayNodeSession
    private var autoRepairedTLSFingerprintsByStoreKey: [String: String] = [:]
    private var tlsSessionCache = MacNodeGatewayTLSSessionCache()

    private init() {
        let session = GatewayNodeSession()
        self.session = session
        self.runtime = MacNodeRuntime(
            canvasSurfaceUrl: { await session.currentCanvasHostUrl() },
            refreshCanvasSurfaceUrl: { await session.refreshCanvasHostUrl() })
    }

    func start() {
        guard self.task == nil else { return }
        self.task = Task { [weak self] in
            await self?.run()
        }
    }

    func stop() {
        self.task?.cancel()
        self.task = nil
        Task { await self.session.disconnect() }
    }

    func setPreferredGatewayStableID(_ stableID: String?) {
        GatewayDiscoveryPreferences.setPreferredStableID(stableID)
        Task { await self.session.disconnect() }
    }

    private func run() async {
        var retryDelay: UInt64 = 1_000_000_000
        var lastCameraEnabled: Bool?
        var lastBrowserControlEnabled: Bool?
        let defaults = UserDefaults.standard

        while !Task.isCancelled {
            if await MainActor.run(body: { AppStateStore.shared.isPaused }) {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                continue
            }

            let cameraEnabled = defaults.object(forKey: cameraEnabledKey) as? Bool ?? false
            if lastCameraEnabled == nil {
                lastCameraEnabled = cameraEnabled
            } else if lastCameraEnabled != cameraEnabled {
                lastCameraEnabled = cameraEnabled
                await self.session.disconnect()
                try? await Task.sleep(nanoseconds: 200_000_000)
            }
            let browserControlEnabled = CarinaConfigFile.browserControlEnabled()
            if lastBrowserControlEnabled == nil {
                lastBrowserControlEnabled = browserControlEnabled
            } else if lastBrowserControlEnabled != browserControlEnabled {
                lastBrowserControlEnabled = browserControlEnabled
                await self.session.disconnect()
                try? await Task.sleep(nanoseconds: 200_000_000)
            }

            var attemptedURL: URL?
            do {
                let config = try await GatewayEndpointStore.shared.requireConfig()
                attemptedURL = config.url
                let caps = self.currentCaps()
                let commands = self.currentCommands(caps: caps)
                let permissions = await self.currentPermissions()
                let connectOptions = GatewayConnectOptions(
                    role: "node",
                    scopes: [],
                    caps: caps,
                    commands: commands,
                    permissions: permissions,
                    clientId: "openclaw-macos",
                    clientMode: "node",
                    clientDisplayName: InstanceIdentity.displayName)
                let sessionBox = self.buildSessionBox(
                    url: config.url,
                    connectionMode: AppStateStore.shared.connectionMode)

                try await self.session.connect(
                    url: config.url,
                    token: config.token,
                    bootstrapToken: nil,
                    password: config.password,
                    connectOptions: connectOptions,
                    sessionBox: sessionBox,
                    onConnected: { [weak self] in
                        guard let self else { return }
                        self.logger.info("mac node connected to gateway")
                        let mainSessionKey = await GatewayConnection.shared.mainSessionKey()
                        await self.runtime.updateMainSessionKey(mainSessionKey)
                        await self.runtime.setEventSender { [weak self] event, payload in
                            guard let self else { return }
                            await self.session.sendEvent(event: event, payloadJSON: payload)
                        }
                    },
                    onDisconnected: { [weak self] reason in
                        guard let self else { return }
                        await self.runtime.setEventSender(nil)
                        self.logger.error("mac node disconnected: \(reason, privacy: .public)")
                    },
                    onInvoke: { [weak self] req in
                        guard let self else {
                            return BridgeInvokeResponse(
                                id: req.id,
                                ok: false,
                                error: CarinaNodeError(code: .unavailable, message: "UNAVAILABLE: node not ready"))
                        }
                        return await self.runtime.handleInvoke(req)
                    })

                retryDelay = 1_000_000_000
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            } catch {
                if await self.autoRepairStaleTLSPinIfNeeded(error: error, url: attemptedURL) {
                    retryDelay = 1_000_000_000
                    continue
                }
                self.logger.error("mac node gateway connect failed: \(error.localizedDescription, privacy: .public)")
                try? await Task.sleep(nanoseconds: min(retryDelay, 10_000_000_000))
                retryDelay = min(retryDelay * 2, 10_000_000_000)
            }
        }
    }

    nonisolated static func resolvedCaps(
        browserControlEnabled: Bool,
        cameraEnabled: Bool,
        locationMode: CarinaLocationMode,
        connectionMode: AppState.ConnectionMode) -> [String]
    {
        var caps: [String] = [
            CarinaCapability.canvas.rawValue,
            CarinaCapability.screen.rawValue,
        ]
        if browserControlEnabled, connectionMode == .local {
            caps.append(CarinaCapability.browser.rawValue)
        }
        if cameraEnabled {
            caps.append(CarinaCapability.camera.rawValue)
        }
        if locationMode != .off {
            caps.append(CarinaCapability.location.rawValue)
        }
        return caps
    }

    private func currentCaps() -> [String] {
        let rawLocationMode = UserDefaults.standard.string(forKey: locationModeKey) ?? "off"
        return Self.resolvedCaps(
            browserControlEnabled: CarinaConfigFile.browserControlEnabled(),
            cameraEnabled: UserDefaults.standard.object(forKey: cameraEnabledKey) as? Bool ?? false,
            locationMode: CarinaLocationMode(rawValue: rawLocationMode) ?? .off,
            connectionMode: AppStateStore.shared.connectionMode)
    }

    private func currentPermissions() async -> [String: Bool] {
        let statuses = await PermissionManager.status()
        return Dictionary(uniqueKeysWithValues: statuses.map { ($0.key.rawValue, $0.value) })
    }

    nonisolated static func resolvedCommands(caps: [String]) -> [String] {
        var commands: [String] = [
            CarinaCanvasCommand.present.rawValue,
            CarinaCanvasCommand.hide.rawValue,
            CarinaCanvasCommand.navigate.rawValue,
            CarinaCanvasCommand.evalJS.rawValue,
            CarinaCanvasCommand.snapshot.rawValue,
            CarinaCanvasA2UICommand.push.rawValue,
            CarinaCanvasA2UICommand.pushJSONL.rawValue,
            CarinaCanvasA2UICommand.reset.rawValue,
            MacNodeScreenCommand.snapshot.rawValue,
            MacNodeScreenCommand.record.rawValue,
            CarinaSystemCommand.notify.rawValue,
            CarinaSystemCommand.which.rawValue,
            CarinaSystemCommand.run.rawValue,
            CarinaSystemCommand.execApprovalsGet.rawValue,
            CarinaSystemCommand.execApprovalsSet.rawValue,
        ]

        let capsSet = Set(caps)
        if capsSet.contains(CarinaCapability.browser.rawValue) {
            commands.append(CarinaBrowserCommand.proxy.rawValue)
        }
        if capsSet.contains(CarinaCapability.camera.rawValue) {
            commands.append(CarinaCameraCommand.list.rawValue)
            commands.append(CarinaCameraCommand.snap.rawValue)
            commands.append(CarinaCameraCommand.clip.rawValue)
        }
        if capsSet.contains(CarinaCapability.location.rawValue) {
            commands.append(CarinaLocationCommand.get.rawValue)
        }

        return commands
    }

    private func currentCommands(caps: [String]) -> [String] {
        Self.resolvedCommands(caps: caps)
    }

    nonisolated static func tlsPinStoreKey(for url: URL) -> String {
        let host = url.host?.trimmingCharacters(in: .whitespacesAndNewlines).nonEmpty ?? "gateway"
        let port = url.port ?? 443
        return "\(host):\(port)"
    }

    nonisolated static func shouldAutoRepairStaleTLSPin(url: URL, failure: GatewayTLSValidationFailure) -> Bool {
        guard failure.kind == .pinMismatch else { return false }
        guard url.scheme?.lowercased() == "wss" else { return false }
        guard failure.storeKey == nil || failure.storeKey == self.tlsPinStoreKey(for: url) else { return false }
        guard let host = url.host?.trimmingCharacters(in: .whitespacesAndNewlines).lowercased(), !host.isEmpty
        else { return false }

        if LoopbackHost.isLoopback(host) {
            return failure.systemTrustOk
        }

        // Tailscale Serve uses publicly trusted, rotating certificates for *.ts.net names.
        // A stale legacy leaf pin should not leave the companion app half-connected forever.
        if host == "ts.net" || host.hasSuffix(".ts.net") {
            return failure.systemTrustOk
        }

        return false
    }

    private func autoRepairStaleTLSPinIfNeeded(error: Error, url: URL?) async -> Bool {
        guard let tlsError = error as? GatewayTLSValidationError, let url else { return false }
        guard Self.shouldAutoRepairStaleTLSPin(url: url, failure: tlsError.failure) else { return false }
        let storeKey = tlsError.failure.storeKey ?? Self.tlsPinStoreKey(for: url)
        guard let observedFingerprint = tlsError.failure.observedFingerprint else { return false }
        guard self.autoRepairedTLSFingerprintsByStoreKey[storeKey] != observedFingerprint else { return false }

        guard GatewayTLSStore.replaceFingerprint(observedFingerprint, stableID: storeKey) else { return false }
        self.autoRepairedTLSFingerprintsByStoreKey[storeKey] = observedFingerprint
        self.logger.info("replaced stale gateway TLS pin storeKey=\(storeKey, privacy: .public)")
        await self.session.disconnect()
        return true
    }

    nonisolated static func tlsParams(
        for url: URL,
        connectionMode: AppState.ConnectionMode,
        root: [String: Any],
        storedFingerprint: String?) -> GatewayTLSParams?
    {
        guard url.scheme?.lowercased() == "wss" else { return nil }
        let stableID = Self.tlsPinStoreKey(for: url)
        let configuredFingerprint = connectionMode == .remote
            ? GatewayRemoteConfig.resolveTLSFingerprint(root: root)
            : nil
        let expectedFingerprint = configuredFingerprint ?? storedFingerprint
        return GatewayTLSParams(
            required: true,
            expectedFingerprint: expectedFingerprint,
            allowTOFU: expectedFingerprint == nil,
            storeKey: stableID)
    }

    private func buildSessionBox(url: URL, connectionMode: AppState.ConnectionMode) -> WebSocketSessionBox? {
        guard url.scheme?.lowercased() == "wss" else {
            self.tlsSessionCache.invalidate()
            return nil
        }
        let stableID = Self.tlsPinStoreKey(for: url)
        let stored = GatewayTLSStore.loadFingerprint(stableID: stableID)
        guard let params = Self.tlsParams(
            for: url,
            connectionMode: connectionMode,
            root: CarinaConfigFile.loadDict(),
            storedFingerprint: stored)
        else {
            self.tlsSessionCache.invalidate()
            return nil
        }
        return self.tlsSessionCache.sessionBox(url: url, params: params)
    }
}
