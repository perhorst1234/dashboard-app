import Foundation

struct StudyStreak: Codable, Equatable {
    var currentCount: Int
    var bestCount: Int
    var lastCompletionDate: Date?

    mutating func registerCompletion(on date: Date) {
        let calendar = Calendar.current
        if let lastCompletionDate, calendar.isDate(date, inSameDayAs: calendar.date(byAdding: .day, value: -1, to: lastCompletionDate) ?? lastCompletionDate) {
            currentCount += 1
        } else if let lastCompletionDate, calendar.isDate(date, inSameDayAs: lastCompletionDate) {
            // same day, no change
        } else {
            currentCount = 1
        }
        lastCompletionDate = date
        bestCount = max(bestCount, currentCount)
    }
}
