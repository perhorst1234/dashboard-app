import Foundation
import EventKit

@MainActor
final class AgendaStore: ObservableObject {
    @Published private(set) var events: [AgendaEvent] = []
    @Published private(set) var calendars: [EKCalendar] = []
    @Published var selectedCalendarIdentifiers: Set<String> = []

    private let eventStore = EKEventStore()
    private let googleCalendarService = CalendarIntegrationService()
    private let magisterService = MagisterService()

    init() {
        loadStoredCalendarSelections()
    }

    func refreshCalendarsIfNeeded() async {
        do {
            try await eventStore.requestAccess(to: .event)
            calendars = eventStore.calendars(for: .event)
            if selectedCalendarIdentifiers.isEmpty {
                selectedCalendarIdentifiers = Set(calendars.map { $0.calendarIdentifier })
            }
            saveCalendarSelections()
            await fetchEvents()
        } catch {
            print("Calendar authorization failed: \(error)")
        }
    }

    func fetchEvents() async {
        let startDate = Date()
        let endDate = Calendar.current.date(byAdding: .month, value: 1, to: startDate) ?? startDate
        let predicate = eventStore.predicateForEvents(withStart: startDate, end: endDate, calendars: calendars.filter { selectedCalendarIdentifiers.contains($0.calendarIdentifier) })
        let eventKitEvents = eventStore.events(matching: predicate)
            .map { event -> AgendaEvent in
                AgendaEvent(title: event.title, startDate: event.startDate, endDate: event.endDate, location: event.location, isStudyBlock: false, source: .google, notes: event.notes)
            }
        let googleBlocks = await googleCalendarService.fetchDedicatedStudyBlocks()
        let merged = (eventKitEvents + googleBlocks).sorted { $0.startDate < $1.startDate }
        self.events = merged
    }

    func synchronizeMagisterAgenda() async {
        do {
            let magisterEvents = try await magisterService.fetchHomeworkAgenda()
            let converted = magisterEvents.map { event in
                AgendaEvent(title: event.title, startDate: event.dueDate, endDate: event.dueDate.addingTimeInterval(3600), location: event.location, isStudyBlock: true, source: .magister, notes: event.description)
            }
            events = (events + converted).sorted { $0.startDate < $1.startDate }
        } catch {
            print("Failed to sync Magister: \(error)")
        }
    }

    func updateMagisterConfiguration(_ configuration: MagisterConfiguration) async {
        await magisterService.updateConfiguration(configuration)
    }

    func currentMagisterConfiguration() async -> MagisterConfiguration? {
        await magisterService.currentConfiguration()
    }

    private func loadStoredCalendarSelections() {
        let defaults = UserDefaults.standard
        if let stored = defaults.array(forKey: "selectedCalendars") as? [String] {
            selectedCalendarIdentifiers = Set(stored)
        }
    }

    private func saveCalendarSelections() {
        UserDefaults.standard.set(Array(selectedCalendarIdentifiers), forKey: "selectedCalendars")
    }

    static let preview: AgendaStore = {
        let store = AgendaStore()
        store.events = [
            AgendaEvent(title: "Collegereeks AI", startDate: .now.addingTimeInterval(3600 * 4), endDate: .now.addingTimeInterval(3600 * 6), source: .google),
            AgendaEvent(title: "Magister huiswerk", startDate: .now.addingTimeInterval(3600 * 24), endDate: .now.addingTimeInterval(3600 * 25), isStudyBlock: true, source: .magister, notes: "Maak hoofdstuk 5")
        ]
        return store
    }()
}
