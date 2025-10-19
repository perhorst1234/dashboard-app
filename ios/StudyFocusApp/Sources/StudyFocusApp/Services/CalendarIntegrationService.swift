import Foundation
import EventKit

actor CalendarIntegrationService {
    private let eventStore = EKEventStore()

    func fetchDedicatedStudyBlocks() async -> [AgendaEvent] {
        do {
            try await eventStore.requestAccess(to: .event)
            let calendars = eventStore.calendars(for: .event).filter { $0.title.localizedCaseInsensitiveContains("study") || $0.title.localizedCaseInsensitiveContains("leren") }
            let startDate = Date()
            let endDate = Calendar.current.date(byAdding: .weekOfYear, value: 2, to: startDate) ?? startDate
            let predicate = eventStore.predicateForEvents(withStart: startDate, end: endDate, calendars: calendars)
            return eventStore.events(matching: predicate).map { event in
                AgendaEvent(title: event.title, startDate: event.startDate, endDate: event.endDate, location: event.location, isStudyBlock: true, source: .google, notes: event.notes)
            }
        } catch {
            print("Failed to fetch dedicated study blocks: \(error)")
            return []
        }
    }
}
