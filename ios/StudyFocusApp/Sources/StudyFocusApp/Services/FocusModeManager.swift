import Foundation
import FamilyControls
import ManagedSettings

@MainActor
final class FocusModeManager: ObservableObject {
    @Published private(set) var isBlockingEnabled = false
    @Published var blockingError: FocusBlockingError?
    @Published private(set) var selectedApplications: Set<ApplicationToken> = [] {
        didSet { persistSelectedApplications() }
    }

    private let store = ManagedSettingsStore()

    func requestAuthorizationIfNeeded() async {
        do {
            try await AuthorizationCenter.shared.requestAuthorization(for: .individual)
            selectedApplications = loadSelectedApplications()
        } catch {
            blockingError = FocusBlockingError(reason: "Toegang tot focusfilter mislukt: \(error.localizedDescription)")
        }
    }

    func updateBlockedApplications(_ applications: Set<ApplicationToken>) {
        selectedApplications = applications
        if isBlockingEnabled { applyBlockingState() }
    }

    func setBlockingEnabled(_ enabled: Bool) {
        guard AuthorizationCenter.shared.authorizationStatus == .approved else {
            blockingError = FocusBlockingError(reason: "Geen toestemming om apps te blokkeren")
            isBlockingEnabled = false
            return
        }
        guard !selectedApplications.isEmpty else {
            isBlockingEnabled = false
            return
        }
        isBlockingEnabled = enabled
        applyBlockingState()
    }

    private func applyBlockingState() {
        if isBlockingEnabled {
            store.shield.applications = selectedApplications
        } else {
            store.shield.applications = []
        }
    }

    private func persistSelectedApplications() {
        let identifiers = selectedApplications.compactMap { $0.bundleIdentifier }
        UserDefaults.standard.set(identifiers, forKey: "blockedApps")
    }

    private func loadSelectedApplications() -> Set<ApplicationToken> {
        let identifiers = UserDefaults.standard.array(forKey: "blockedApps") as? [String] ?? []
        let tokens = identifiers.compactMap { ApplicationToken(bundleIdentifier: $0) }
        return Set(tokens)
    }
}

struct FocusBlockingError: Identifiable, LocalizedError {
    let id = UUID()
    let reason: String

    var errorDescription: String? { reason }
}
