import Foundation
import Combine

@MainActor
final class StudySessionStore: ObservableObject {
    @Published private(set) var sessions: [StudySession] = []
    @Published var activeSession: StudySession?
    @Published private(set) var streak: StudyStreak = .init(currentCount: 0, bestCount: 0, lastCompletionDate: nil)

    private var timer: Timer?
    private var liveDuration: TimeInterval = 0
    private var cancellables: Set<AnyCancellable> = []

    init() {
        loadSessions()
        observeActiveSession()
    }

    func startSession(for degree: String, subject: String, plannedDuration: TimeInterval, focusLevel: StudySession.FocusLevel) {
        guard activeSession == nil else { return }
        let session = StudySession(degree: degree, subject: subject, plannedDuration: plannedDuration, focusLevel: focusLevel)
        activeSession = session
        liveDuration = 0
        startTimer()
    }

    func addNoteToActiveSession(_ text: String) {
        guard var session = activeSession else { return }
        let note = StudySession.Note(content: text)
        session.notes.append(note)
        activeSession = session
    }

    func stopSession(withNote noteText: String? = nil) {
        guard let session = activeSession else { return }
        timer?.invalidate()
        let note = noteText.map { StudySession.Note(content: $0) }
        let finished = session.finished(with: liveDuration, adding note: note)
        sessions.append(finished)
        streak.registerCompletion(on: Date())
        activeSession = nil
        liveDuration = 0
        saveSessions()
    }

    func deleteSessions(at offsets: IndexSet) {
        sessions.remove(atOffsets: offsets)
        saveSessions()
    }

    func totalDuration(for degree: String) -> TimeInterval {
        sessions
            .filter { $0.degree == degree }
            .reduce(0) { $0 + $1.actualDuration }
    }

    func upcomingNotes(for degree: String) -> [StudySession.Note] {
        sessions
            .filter { $0.degree == degree }
            .flatMap { $0.notes }
            .sorted { $0.createdAt > $1.createdAt }
    }

    private func startTimer() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.liveDuration += 1
            }
        }
    }

    private func observeActiveSession() {
        $activeSession
            .sink { [weak self] session in
                guard let self else { return }
                if session == nil { self.timer?.invalidate() }
            }
            .store(in: &cancellables)
    }

    private func saveSessions() {
        do {
            let data = try JSONEncoder().encode(sessions)
            try data.write(to: persistenceURL(), options: .atomic)
        } catch {
            print("Failed to save sessions: \(error)")
        }
    }

    private func loadSessions() {
        do {
            let data = try Data(contentsOf: persistenceURL())
            sessions = try JSONDecoder().decode([StudySession].self, from: data)
        } catch {
            sessions = []
        }
    }

    private func persistenceURL() -> URL {
        let directory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        return directory.appendingPathComponent("study_sessions.json")
    }

    static let preview: StudySessionStore = {
        let store = StudySessionStore()
        store.sessions = [
            StudySession(degree: "Informatica", subject: "Datastructuren", plannedDuration: 3600).finished(with: 3400),
            StudySession(degree: "Informatica", subject: "AI", plannedDuration: 5400).finished(with: 5600)
        ]
        return store
    }()
}
