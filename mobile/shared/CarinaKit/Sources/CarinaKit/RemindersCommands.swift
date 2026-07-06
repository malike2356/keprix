import Foundation

public enum CarinaRemindersCommand: String, Codable, Sendable {
    case list = "reminders.list"
    case add = "reminders.add"
}

public enum CarinaReminderStatusFilter: String, Codable, Sendable {
    case incomplete
    case completed
    case all
}

public struct CarinaRemindersListParams: Codable, Sendable, Equatable {
    public var status: CarinaReminderStatusFilter?
    public var limit: Int?

    public init(status: CarinaReminderStatusFilter? = nil, limit: Int? = nil) {
        self.status = status
        self.limit = limit
    }
}

public struct CarinaRemindersAddParams: Codable, Sendable, Equatable {
    public var title: String
    public var dueISO: String?
    public var notes: String?
    public var listId: String?
    public var listName: String?

    public init(
        title: String,
        dueISO: String? = nil,
        notes: String? = nil,
        listId: String? = nil,
        listName: String? = nil)
    {
        self.title = title
        self.dueISO = dueISO
        self.notes = notes
        self.listId = listId
        self.listName = listName
    }
}

public struct CarinaReminderPayload: Codable, Sendable, Equatable {
    public var identifier: String
    public var title: String
    public var dueISO: String?
    public var completed: Bool
    public var listName: String?

    public init(
        identifier: String,
        title: String,
        dueISO: String? = nil,
        completed: Bool,
        listName: String? = nil)
    {
        self.identifier = identifier
        self.title = title
        self.dueISO = dueISO
        self.completed = completed
        self.listName = listName
    }
}

public struct CarinaRemindersListPayload: Codable, Sendable, Equatable {
    public var reminders: [CarinaReminderPayload]

    public init(reminders: [CarinaReminderPayload]) {
        self.reminders = reminders
    }
}

public struct CarinaRemindersAddPayload: Codable, Sendable, Equatable {
    public var reminder: CarinaReminderPayload

    public init(reminder: CarinaReminderPayload) {
        self.reminder = reminder
    }
}
