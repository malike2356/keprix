import Foundation
import Testing
@testable import Carina

@Suite(.serialized) struct CarinaAppDelegateTests {
    @Test @MainActor func `resolves registry model before view task assigns delegate model`() {
        let registryModel = NodeAppModel()
        CarinaAppModelRegistry.appModel = registryModel
        defer { CarinaAppModelRegistry.appModel = nil }

        let delegate = CarinaAppDelegate()

        #expect(delegate._test_resolvedAppModel() === registryModel)
    }

    @Test @MainActor func `prefers explicit delegate model over registry fallback`() {
        let registryModel = NodeAppModel()
        let explicitModel = NodeAppModel()
        CarinaAppModelRegistry.appModel = registryModel
        defer { CarinaAppModelRegistry.appModel = nil }

        let delegate = CarinaAppDelegate()
        delegate.appModel = explicitModel

        #expect(delegate._test_resolvedAppModel() === explicitModel)
    }

    @Test @MainActor func `derives background refresh task identifier from app bundle identifier`() {
        let delegate = CarinaAppDelegate()
        let bundleIdentifier = Bundle.main.bundleIdentifier ?? "ai.verlox.carinakeprix.app.tests"

        #expect(delegate._test_wakeRefreshTaskIdentifier() == "\(bundleIdentifier).bgrefresh")
    }
}
