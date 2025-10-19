import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var sessionStore: StudySessionStore
    @EnvironmentObject private var taskStore: TaskStore

    @State private var degreeFilter: String = "Informatica"
    @State private var subject: String = ""
    @State private var plannedMinutes: Double = 60
    @State private var focusLevel: StudySession.FocusLevel = .deep
    @State private var note: String = ""

    private var availableDegrees: [String] {
        let fromSessions = Set(sessionStore.sessions.map { $0.degree })
        let fromTasks = Set(taskStore.tasks.map { $0.degree })
        let combined = fromSessions.union(fromTasks)
        if combined.isEmpty { return ["Informatica"] }
        return Array(combined).sorted()
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    sessionSummary
                    noteSection
                    streakSection
                    sessionPreparation
                    FocusSessionView(degree: degreeFilter, subject: subject, plannedMinutes: plannedMinutes, focusLevel: focusLevel)
                        .environmentObject(sessionStore)
                }
                .padding()
            }
            .navigationTitle("Dashboard")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Picker("Opleiding", selection: $degreeFilter) {
                        ForEach(availableDegrees, id: \.self) { degree in
                            Text(degree).tag(degree)
                        }
                    }
                }
            }
        }
    }

    private var sessionSummary: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Studietijd deze opleiding")
                .font(.headline)
            let totalDuration = sessionStore.totalDuration(for: degreeFilter)
            Text(totalDuration.formattedTime())
                .font(.largeTitle.bold())
            if let activeSession = sessionStore.activeSession {
                ActiveSessionCard(session: activeSession)
            }
            Divider()
            VStack(alignment: .leading, spacing: 8) {
                Text("Laatste notities")
                    .font(.subheadline.weight(.semibold))
                ForEach(sessionStore.upcomingNotes(for: degreeFilter).prefix(3)) { note in
                    Text(note.content)
                        .font(.body)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private var noteSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Notitie voor volgende sessie")
                .font(.headline)
            TextField("Beschrijf waar je wilt starten", text: $note, axis: .vertical)
                .textFieldStyle(.roundedBorder)
            Button {
                sessionStore.addNoteToActiveSession(note)
                note = ""
            } label: {
                Label("Bewaar notitie", systemImage: "square.and.pencil")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(sessionStore.activeSession == nil || note.isEmpty)
        }
        .padding()
        .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private var streakSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Streaks")
                .font(.headline)
            HStack {
                streakCard(title: "Huidige streak", count: sessionStore.streak.currentCount, symbol: "flame.fill", tint: .orange)
                streakCard(title: "Beste streak", count: sessionStore.streak.bestCount, symbol: "trophy.fill", tint: .yellow)
            }
        }
        .padding()
        .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private var sessionPreparation: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Voorbereiding sessie")
                .font(.headline)
            TextField("Vak of onderwerp", text: $subject)
                .textFieldStyle(.roundedBorder)
            VStack(alignment: .leading) {
                Text("Geplande tijd: \(Int(plannedMinutes)) minuten")
                    .font(.subheadline)
                Slider(value: $plannedMinutes, in: 15...180, step: 15)
            }
            Picker("Focusniveau", selection: $focusLevel) {
                ForEach(StudySession.FocusLevel.allCases) { level in
                    Label(level.label, systemImage: level.icon)
                        .tag(level)
                }
            }
            .pickerStyle(.segmented)
        }
        .padding()
        .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private func streakCard(title: String, count: Int, symbol: String, tint: Color) -> some View {
        VStack(spacing: 12) {
            Image(systemName: symbol)
                .font(.largeTitle)
                .foregroundStyle(tint)
            Text("\(count)")
                .font(.title.bold())
            Text(title)
                .font(.subheadline)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

private struct ActiveSessionCard: View {
    let session: StudySession

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Actieve sessie", systemImage: "timer")
                .font(.subheadline.weight(.semibold))
            Text(session.subject)
                .font(.title3.bold())
            Text(session.focusLevel.label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

#Preview {
    DashboardView()
        .environmentObject(StudySessionStore.preview)
        .environmentObject(TaskStore.preview)
}
