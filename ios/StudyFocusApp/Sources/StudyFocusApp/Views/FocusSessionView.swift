import SwiftUI
import FamilyControls

struct FocusSessionView: View {
    @EnvironmentObject private var sessionStore: StudySessionStore
    @EnvironmentObject private var focusManager: FocusModeManager

    @State private var note: String = ""
    @State private var isPickerPresented = false
    @State private var selection = FamilyActivitySelection()

    let degree: String
    let subject: String
    let plannedMinutes: Double
    let focusLevel: StudySession.FocusLevel

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Start nieuwe sessie")
                .font(.headline)
            if let activeSession = sessionStore.activeSession {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Bezig met \(activeSession.subject)")
                        .font(.subheadline)
                    Button("Stop sessie") {
                        sessionStore.stopSession(withNote: note.isEmpty ? nil : note)
                        focusManager.setBlockingEnabled(false)
                        note = ""
                    }
                    .buttonStyle(.borderedProminent)
                }
            } else {
                Button {
                    sessionStore.startSession(for: degree, subject: subject, plannedDuration: plannedMinutes * 60, focusLevel: focusLevel)
                    if !focusManager.selectedApplications.isEmpty {
                        focusManager.setBlockingEnabled(true)
                    }
                } label: {
                    Label("Start sessie", systemImage: "play.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(subject.isEmpty)
            }
            Toggle(isOn: Binding(
                get: { focusManager.isBlockingEnabled },
                set: { focusManager.setBlockingEnabled($0) }
            )) {
                Label("Blokkeer afleidende apps", systemImage: "moon.zzz.fill")
            }
            .toggleStyle(.switch)
            .disabled(focusManager.selectedApplications.isEmpty)

            Button {
                isPickerPresented = true
            } label: {
                Label("Kies te blokkeren apps", systemImage: "iphone")
            }
            .buttonStyle(.bordered)
            .familyActivityPicker(isPresented: $isPickerPresented, selection: $selection)
            .onChange(of: selection) { newValue in
                focusManager.updateBlockedApplications(Set(newValue.applicationTokens))
            }

            TextField("Notitie voor afronding", text: $note, axis: .vertical)
                .textFieldStyle(.roundedBorder)
        }
        .padding()
        .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }
}

#Preview {
    FocusSessionView(degree: "Informatica", subject: "AI", plannedMinutes: 90, focusLevel: .deep)
        .environmentObject(StudySessionStore.preview)
        .environmentObject(FocusModeManager())
}
