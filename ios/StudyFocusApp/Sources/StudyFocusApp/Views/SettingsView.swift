import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var agendaStore: AgendaStore
    @EnvironmentObject private var focusManager: FocusModeManager

    @State private var configuration = MagisterConfiguration(
        baseURL: URL(string: "https://school.magister.net")!,
        clientId: "",
        username: nil,
        password: nil
    )
    @State private var username = ""
    @State private var password = ""
    @State private var clientId = ""
    @State private var baseURL = "https://school.magister.net"

    var body: some View {
        NavigationStack {
            Form {
                Section("Magister") {
                    TextField("School URL", text: $baseURL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                    TextField("Client ID", text: $clientId)
                        .autocapitalization(.none)
                    TextField("Gebruikersnaam", text: $username)
                        .autocapitalization(.none)
                    SecureField("Wachtwoord", text: $password)
                    Button("Bewaar Magister instellingen") {
                        if let url = URL(string: baseURL) {
                            configuration.baseURL = url
                        }
                        configuration.clientId = clientId
                        configuration.username = username.isEmpty ? nil : username
                        configuration.password = password.isEmpty ? nil : password
                        Task { await agendaStore.updateMagisterConfiguration(configuration) }
                    }
                }

                Section("Focus") {
                    Toggle("Apps blokkeren tijdens sessie", isOn: Binding(
                        get: { focusManager.isBlockingEnabled },
                        set: { focusManager.setBlockingEnabled($0) }
                    ))
                    .disabled(focusManager.selectedApplications.isEmpty)
                }
            }
            .navigationTitle("Instellingen")
        }
        .task {
            if let stored = await agendaStore.currentMagisterConfiguration() {
                await MainActor.run {
                    configuration = stored
                    baseURL = stored.baseURL.absoluteString
                    clientId = stored.clientId
                    username = stored.username ?? ""
                    password = stored.password ?? ""
                }
            }
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AgendaStore.preview)
        .environmentObject(FocusModeManager())
}
