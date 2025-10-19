import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var sessionStore: StudySessionStore
    @EnvironmentObject private var taskStore: TaskStore
    @EnvironmentObject private var agendaStore: AgendaStore
    @EnvironmentObject private var focusManager: FocusModeManager
    @EnvironmentObject private var liveActivityManager: LiveActivityManager

    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "speedometer")
                }

            AgendaView()
                .tabItem {
                    Label("Agenda", systemImage: "calendar")
                }

            TasksView()
                .tabItem {
                    Label("Taken", systemImage: "checklist")
                }

            SettingsView()
                .tabItem {
                    Label("Instellingen", systemImage: "gearshape")
                }
        }
        .onReceive(sessionStore.$activeSession.compactMap { $0 }) { session in
            liveActivityManager.startOrUpdateActivity(for: session)
        }
        .onChange(of: sessionStore.activeSession) { _, session in
            if session == nil {
                liveActivityManager.endActivity()
            }
        }
        .task {
            await agendaStore.refreshCalendarsIfNeeded()
            await agendaStore.synchronizeMagisterAgenda()
        }
        .alert(item: $focusManager.blockingError) { error in
            Alert(title: Text("Focus-fout"), message: Text(error.localizedDescription), dismissButton: .default(Text("Ok")))
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(StudySessionStore.preview)
        .environmentObject(TaskStore.preview)
        .environmentObject(AgendaStore.preview)
        .environmentObject(FocusModeManager())
        .environmentObject(LiveActivityManager())
}
