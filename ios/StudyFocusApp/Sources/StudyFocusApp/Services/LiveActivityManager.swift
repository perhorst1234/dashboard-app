import Foundation
import ActivityKit

@MainActor
final class LiveActivityManager: ObservableObject {
    private var activity: Activity<StudyActivityAttributes>?

    func requestAuthorizationIfNeeded() async {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else { return }
    }

    func startOrUpdateActivity(for session: StudySession) {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else { return }
        let attributes = StudyActivityAttributes(degree: session.degree, subject: session.subject)
        let state = StudyActivityAttributes.ContentState(startDate: session.startDate, plannedDuration: session.plannedDuration, elapsedTime: session.actualDuration)
        if let activity {
            Task { await activity.update(using: state) }
        } else {
            do {
                activity = try Activity.request(attributes: attributes, contentState: state)
            } catch {
                print("Failed to start activity: \(error)")
            }
        }
    }

    func endActivity() {
        Task {
            await activity?.end(dismissalPolicy: .immediate)
            activity = nil
        }
    }
}

struct StudyActivityAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        var startDate: Date
        var plannedDuration: TimeInterval
        var elapsedTime: TimeInterval
    }

    var degree: String
    var subject: String
}
