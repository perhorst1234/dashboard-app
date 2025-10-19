import Foundation

struct StudySession: Identifiable, Codable, Equatable {
    enum FocusLevel: String, CaseIterable, Codable, Identifiable {
        case deep
        case light
        case revision

        var id: String { rawValue }

        var label: String {
            switch self {
            case .deep: return "Diep werk"
            case .light: return "Licht"
            case .revision: return "Herhaling"
            }
        }

        var icon: String {
            switch self {
            case .deep: return "brain.head.profile"
            case .light: return "book"
            case .revision: return "arrow.counterclockwise"
            }
        }
    }

    struct Note: Identifiable, Codable, Equatable {
        let id: UUID
        var content: String
        var createdAt: Date

        init(id: UUID = UUID(), content: String, createdAt: Date = .now) {
            self.id = id
            self.content = content
            self.createdAt = createdAt
        }
    }

    let id: UUID
    var degree: String
    var subject: String
    var plannedDuration: TimeInterval
    var actualDuration: TimeInterval
    var startDate: Date
    var endDate: Date?
    var notes: [Note]
    var focusLevel: FocusLevel
    var isLive: Bool

    init(id: UUID = UUID(), degree: String, subject: String, plannedDuration: TimeInterval, startDate: Date = .now, focusLevel: FocusLevel = .deep, notes: [Note] = []) {
        self.id = id
        self.degree = degree
        self.subject = subject
        self.plannedDuration = plannedDuration
        self.actualDuration = 0
        self.startDate = startDate
        self.endDate = nil
        self.notes = notes
        self.focusLevel = focusLevel
        self.isLive = true
    }

    func finished(with actualDuration: TimeInterval, endDate: Date = .now, adding note: Note? = nil) -> StudySession {
        var copy = self
        copy.actualDuration = actualDuration
        copy.endDate = endDate
        copy.isLive = false
        if let note { copy.notes.append(note) }
        return copy
    }
}
