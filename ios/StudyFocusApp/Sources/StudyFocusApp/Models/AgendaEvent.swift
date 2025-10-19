import Foundation

struct AgendaEvent: Identifiable, Codable, Equatable {
    let id: UUID
    var title: String
    var startDate: Date
    var endDate: Date
    var location: String?
    var isStudyBlock: Bool
    var source: Source
    var notes: String?

    enum Source: String, Codable, Identifiable, CaseIterable {
        case google
        case magister
        case manual

        var id: String { rawValue }

        var label: String {
            switch self {
            case .google: return "Google Agenda"
            case .magister: return "Magister"
            case .manual: return "Handmatig"
            }
        }
    }

    init(id: UUID = UUID(), title: String, startDate: Date, endDate: Date, location: String? = nil, isStudyBlock: Bool = false, source: Source, notes: String? = nil) {
        self.id = id
        self.title = title
        self.startDate = startDate
        self.endDate = endDate
        self.location = location
        self.isStudyBlock = isStudyBlock
        self.source = source
        self.notes = notes
    }
}
