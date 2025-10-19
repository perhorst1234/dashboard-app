import SwiftUI
import EventKit

struct AgendaView: View {
    @EnvironmentObject private var agendaStore: AgendaStore

    @State private var isSelectingCalendars = false

    var body: some View {
        NavigationStack {
            List {
                ForEach(agendaStore.events) { event in
                    AgendaRow(event: event)
                }
            }
            .navigationTitle("Agenda")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        isSelectingCalendars.toggle()
                    } label: {
                        Image(systemName: "slider.horizontal.3")
                    }
                }
            }
            .sheet(isPresented: $isSelectingCalendars) {
                CalendarSelectionView(calendars: agendaStore.calendars, selectedIdentifiers: $agendaStore.selectedCalendarIdentifiers) {
                    Task { await agendaStore.fetchEvents() }
                }
            }
            .refreshable {
                await agendaStore.fetchEvents()
                await agendaStore.synchronizeMagisterAgenda()
            }
        }
    }
}

private struct AgendaRow: View {
    let event: AgendaEvent

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(event.title)
                    .font(.headline)
                Spacer()
                Text(event.source.label)
                    .font(.caption)
                    .padding(6)
                    .background(sourceTint, in: Capsule())
            }
            HStack(spacing: 8) {
                Image(systemName: "calendar")
                Text(event.startDate, style: .date)
                Text(event.startDate, style: .time)
                Text("–")
                Text(event.endDate, style: .time)
            }
            .font(.caption)
            .foregroundStyle(.secondary)
            if let notes = event.notes, !notes.isEmpty {
                Text(notes)
                    .font(.subheadline)
            }
        }
        .padding(.vertical, 8)
    }

    private var sourceTint: Color {
        switch event.source {
        case .google: return .blue.opacity(0.2)
        case .magister: return .green.opacity(0.2)
        case .manual: return .gray.opacity(0.2)
        }
    }
}

private struct CalendarSelectionView: View {
    let calendars: [EKCalendar]
    @Binding var selectedIdentifiers: Set<String>
    let onDismiss: () -> Void

    var body: some View {
        NavigationStack {
            List(calendars, id: \.calendarIdentifier) { calendar in
                MultipleSelectionRow(isSelected: selectedIdentifiers.contains(calendar.calendarIdentifier)) {
                    if selectedIdentifiers.contains(calendar.calendarIdentifier) {
                        selectedIdentifiers.remove(calendar.calendarIdentifier)
                    } else {
                        selectedIdentifiers.insert(calendar.calendarIdentifier)
                    }
                } label: {
                    Text(calendar.title)
                }
            }
            .navigationTitle("Kies agenda's")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Gereed") { onDismiss() }
                }
            }
        }
    }
}

private struct MultipleSelectionRow<Label: View>: View {
    let isSelected: Bool
    let action: () -> Void
    let label: Label

    init(isSelected: Bool, action: @escaping () -> Void, @ViewBuilder label: () -> Label) {
        self.isSelected = isSelected
        self.action = action
        self.label = label()
    }

    var body: some View {
        Button(action: action) {
            HStack {
                label
                Spacer()
                if isSelected {
                    Image(systemName: "checkmark")
                }
            }
        }
    }
}

#Preview {
    AgendaView()
        .environmentObject(AgendaStore.preview)
}
