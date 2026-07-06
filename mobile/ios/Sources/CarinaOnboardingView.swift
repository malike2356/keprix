import SwiftUI

struct CarinaOnboardingView: View {
    @State private var serverURL = ""
    @State private var statusMessage = ""
    @State private var isTesting = false
    @State private var isConfigured = false
    let onComplete: () -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section("Connect to your keprix server") {
                    TextField("https://my-keprix.example.com", text: $serverURL)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()
                    if !statusMessage.isEmpty {
                        Text(statusMessage)
                            .font(.footnote)
                            .foregroundStyle(isConfigured ? .green : .secondary)
                    }
                }
                Section {
                    Button(isTesting ? "Testing..." : "Test connection") {
                        Task { await testConnection() }
                    }
                    .disabled(serverURL.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isTesting)
                    Button("Continue") {
                        onComplete()
                    }
                    .disabled(!isConfigured)
                }
            }
            .navigationTitle("keprix")
        }
    }

    private func testConnection() async {
        isTesting = true
        defer { isTesting = false }
        do {
            try CarinaServerConfig.saveServerURL(serverURL)
            guard let healthURL = CarinaServerConfig.healthCheckURL() else {
                statusMessage = "Enter a valid server URL."
                isConfigured = false
                return
            }
            var request = URLRequest(url: healthURL)
            request.httpMethod = "GET"
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                statusMessage = "Server did not respond with OK."
                isConfigured = false
                return
            }
            statusMessage = "Connected. Server URL saved."
            isConfigured = true
        } catch {
            statusMessage = "Connection failed: \(error.localizedDescription)"
            isConfigured = false
        }
    }
}
