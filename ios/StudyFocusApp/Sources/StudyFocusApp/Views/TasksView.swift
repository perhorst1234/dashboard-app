import SwiftUI

struct TasksView: View {
    @EnvironmentObject private var taskStore: TaskStore

    @State private var isPresentingNewTask = false

    var body: some View {
        NavigationStack {
            List {
                ForEach(taskStore.tasks) { task in
                    TaskRow(task: task) {
                        taskStore.toggleCompletion(for: task)
                    }
                }
                .onDelete(perform: taskStore.deleteTasks)
            }
            .navigationTitle("Taken")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        isPresentingNewTask.toggle()
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $isPresentingNewTask) {
                NewTaskView { task in
                    taskStore.addTask(task)
                }
            }
        }
    }
}

private struct TaskRow: View {
    let task: StudyTask
    let toggle: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Button(action: toggle) {
                Image(systemName: task.isCompleted ? "checkmark.circle.fill" : "circle")
                    .font(.title2)
                    .foregroundStyle(task.isCompleted ? Color.green : Color.secondary)
            }
            .buttonStyle(.plain)

            VStack(alignment: .leading, spacing: 4) {
                Text(task.title)
                    .font(.headline)
                if !task.detail.isEmpty {
                    Text(task.detail)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                if let dueDate = task.dueDate {
                    Text(dueDate, style: .date)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            if let priorityColor = priorityColor {
                Circle()
                    .fill(priorityColor)
                    .frame(width: 12, height: 12)
            }
        }
        .padding(.vertical, 6)
    }

    private var priorityColor: Color? {
        switch task.priority {
        case .high: return .red
        case .medium: return .orange
        case .low: return .green
        }
    }
}

private struct NewTaskView: View {
    @Environment(\.dismiss) private var dismiss

    @State private var title = ""
    @State private var detail = ""
    @State private var degree = ""
    @State private var subject = ""
    @State private var dueDate = Date()
    @State private var hasDueDate = true
    @State private var priority = StudyTask.Priority.medium

    let onCreate: (StudyTask) -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section("Details") {
                    TextField("Titel", text: $title)
                    TextField("Omschrijving", text: $detail)
                    TextField("Opleiding", text: $degree)
                    TextField("Vak", text: $subject)
                }
                Section("Planning") {
                    Toggle("Heeft deadline", isOn: $hasDueDate)
                    if hasDueDate {
                        DatePicker("Deadline", selection: $dueDate, displayedComponents: [.date, .hourAndMinute])
                    }
                    Picker("Prioriteit", selection: $priority) {
                        ForEach(StudyTask.Priority.allCases) { priority in
                            Text(priority.rawValue.capitalized).tag(priority)
                        }
                    }
                }
            }
            .navigationTitle("Nieuwe taak")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Annuleer") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Bewaar") {
                        let task = StudyTask(
                            title: title,
                            detail: detail,
                            dueDate: hasDueDate ? dueDate : nil,
                            degree: degree,
                            subject: subject,
                            priority: priority
                        )
                        onCreate(task)
                        dismiss()
                    }
                    .disabled(title.isEmpty || degree.isEmpty)
                }
            }
        }
    }
}

#Preview {
    TasksView()
        .environmentObject(TaskStore.preview)
}
