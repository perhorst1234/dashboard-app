import Foundation

enum MagisterError: LocalizedError {
    case configurationMissing
    case authenticationFailed
    case apiError(String)

    var errorDescription: String? {
        switch self {
        case .configurationMissing:
            return "Magister configuratie ontbreekt. Voeg je school en account toe in de instellingen."
        case .authenticationFailed:
            return "Aanmelden bij Magister is mislukt. Controleer je gebruikersnaam en wachtwoord."
        case let .apiError(message):
            return message
        }
    }
}

struct MagisterEvent: Codable {
    var id: String
    var title: String
    var description: String
    var dueDate: Date
    var location: String?
}

actor MagisterService {
    private var configuration: MagisterConfiguration? = MagisterConfiguration.load()
    private let urlSession = URLSession.shared

    func updateConfiguration(_ configuration: MagisterConfiguration) async {
        self.configuration = configuration
        configuration.save()
    }

    func currentConfiguration() -> MagisterConfiguration? {
        configuration
    }

    func fetchHomeworkAgenda() async throws -> [MagisterEvent] {
        guard let configuration else { throw MagisterError.configurationMissing }
        let token = try await authenticate(configuration: configuration)
        var components = URLComponents(url: configuration.baseURL.appendingPathComponent("api/agenda/homework"), resolvingAgainstBaseURL: false)
        components?.queryItems = [
            .init(name: "from", value: ISO8601DateFormatter().string(from: .now)),
            .init(name: "until", value: ISO8601DateFormatter().string(from: Calendar.current.date(byAdding: .weekOfYear, value: 4, to: .now)!))
        ]
        guard let url = components?.url else { throw MagisterError.apiError("Ongeldige agenda-URL") }
        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await urlSession.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw MagisterError.apiError("Geen geldig antwoord") }
        guard http.statusCode == 200 else {
            throw MagisterError.apiError("Magister gaf status \(http.statusCode)")
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode([MagisterEvent].self, from: data)
    }

    private func authenticate(configuration: MagisterConfiguration) async throws -> String {
        guard let username = configuration.username, let password = configuration.password else {
            throw MagisterError.configurationMissing
        }
        let loginURL = configuration.baseURL.appendingPathComponent("oauth/token")
        var request = URLRequest(url: loginURL)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = "username=\(username)&password=\(password)&client_id=\(configuration.clientId)&scope=offline_access".data(using: .utf8)
        let (data, response) = try await urlSession.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw MagisterError.apiError("Geen geldig antwoord") }
        guard http.statusCode == 200 else { throw MagisterError.authenticationFailed }
        let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)
        return tokenResponse.accessToken
    }
}

private struct TokenResponse: Codable {
    let accessToken: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
    }
}

struct MagisterConfiguration: Codable {
    var baseURL: URL
    var clientId: String
    var username: String?
    var password: String?

    static func load() -> MagisterConfiguration? {
        guard let data = UserDefaults.standard.data(forKey: "magisterConfig") else { return nil }
        return try? JSONDecoder().decode(MagisterConfiguration.self, from: data)
    }

    func save() {
        if let data = try? JSONEncoder().encode(self) {
            UserDefaults.standard.set(data, forKey: "magisterConfig")
        }
    }
}
