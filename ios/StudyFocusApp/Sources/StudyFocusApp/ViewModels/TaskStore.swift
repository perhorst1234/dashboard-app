import Foundation

@MainActor
final class TaskStore: ObservableObject {
    @Published private(set) var tasks: [StudyTask] = []

    init() {
        loadTasks()
    }

    func addTask(_ task: StudyTask) {
        tasks.append(task)
        saveTasks()
    }

    func toggleCompletion(for task: StudyTask) {
        guard let index = tasks.firstIndex(where: { $0.id == task.id }) else { return }
        tasks[index].isCompleted.toggle()
        saveTasks()
    }

    func deleteTasks(at offsets: IndexSet) {
        tasks.remove(atOffsets: offsets)
        saveTasks()
    }

    func tasks(for degree: String) -> [StudyTask] {
        tasks.filter { $0.degree == degree && !$0.isCompleted }
    }

    private func saveTasks() {
        do {
            let data = try JSONEncoder().encode(tasks)
            try data.write(to: persistenceURL(), options: .atomic)
        } catch {
            print("Failed to save tasks: \(error)")
        }
    }

    private func loadTasks() {
        do {
            let data = try Data(contentsOf: persistenceURL())
            tasks = try JSONDecoder().decode([StudyTask].self, from: data)
        } catch {
            tasks = []
        }
    }

    private func persistenceURL() -> URL {
        let directory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        return directory.appendingPathComponent("study_tasks.json")
    }

    static let preview: TaskStore = {
        let store = TaskStore()
        store.tasks = [
            StudyTask(title: "Lees hoofdstuk 4", detail: "Voorbereiding college", dueDate: .now.addingTimeInterval(3600 * 24), degree: "Informatica", subject: "AI", priority: .high),
            StudyTask(title: "Maak opdracht 2", detail: "Datastructuren", dueDate: .now.addingTimeInterval(3600 * 48), degree: "Informatica", subject: "Datastructuren", priority: .medium)
        ]
        return store
    }()
}
