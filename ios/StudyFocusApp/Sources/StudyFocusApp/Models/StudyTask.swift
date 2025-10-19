import Foundation

struct StudyTask: Identifiable, Codable, Equatable {
    enum Priority: String, CaseIterable, Codable, Identifiable {
        case high, medium, low

        var id: String { rawValue }

        var colorName: String {
            switch self {
            case .high: return "red"
            case .medium: return "orange"
            case .low: return "green"
            }
        }
    }

    let id: UUID
    var title: String
    var detail: String
    var dueDate: Date?
    var degree: String
    var subject: String
    var priority: Priority
    var isCompleted: Bool
    var magisterId: String?

    init(id: UUID = UUID(), title: String, detail: String, dueDate: Date?, degree: String, subject: String, priority: Priority = .medium, isCompleted: Bool = false, magisterId: String? = nil) {
        self.id = id
        self.title = title
        self.detail = detail
        self.dueDate = dueDate
        self.degree = degree
        self.subject = subject
        self.priority = priority
        self.isCompleted = isCompleted
        self.magisterId = magisterId
    }
}
