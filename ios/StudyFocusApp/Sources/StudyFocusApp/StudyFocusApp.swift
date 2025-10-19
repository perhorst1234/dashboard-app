import SwiftUI
import FamilyControls
import ActivityKit

@main
struct StudyFocusApp: App {
    @StateObject private var sessionStore = StudySessionStore()
    @StateObject private var taskStore = TaskStore()
    @StateObject private var agendaStore = AgendaStore()
    @StateObject private var focusManager = FocusModeManager()
    @StateObject private var liveActivityManager = LiveActivityManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(sessionStore)
                .environmentObject(taskStore)
                .environmentObject(agendaStore)
                .environmentObject(focusManager)
                .environmentObject(liveActivityManager)
                .task {
                    await focusManager.requestAuthorizationIfNeeded()
                    await liveActivityManager.requestAuthorizationIfNeeded()
                }
        }
    }
}
