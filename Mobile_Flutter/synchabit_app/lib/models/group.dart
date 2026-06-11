class Group {
  final int id;
  final String name;
  final String description;
  final int creatorId;
  final bool isLeader;

  Group({
    required this.id,
    required this.name,
    required this.description,
    required this.creatorId,
    required this.isLeader,
  });

  factory Group.fromJson(Map<String, dynamic> json) {
    return Group(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      creatorId: json['creatorId'] ?? 0,
      isLeader: json['isLeader'] ?? false,
    );
  }
}

// Bana gelen grup daveti
class GroupInvite {
  final int inviteId;
  final int groupId;
  final String groupName;
  final String inviterUsername;

  GroupInvite({
    required this.inviteId,
    required this.groupId,
    required this.groupName,
    required this.inviterUsername,
  });

  factory GroupInvite.fromJson(Map<String, dynamic> json) {
    return GroupInvite(
      inviteId: json['inviteId'] ?? 0,
      groupId: json['groupId'] ?? 0,
      groupName: json['groupName'] ?? '',
      inviterUsername: json['inviterUsername'] ?? '',
    );
  }
}

// Grup üyesi (members endpoint'inden gelir)
class GroupMember {
  final int userId;
  final String username;
  final int level;

  GroupMember({
    required this.userId,
    required this.username,
    required this.level,
  });

  factory GroupMember.fromJson(Map<String, dynamic> json) {
    return GroupMember(
      userId: json['userId'] ?? 0,
      username: json['username'] ?? '',
      level: json['level'] ?? 1,
    );
  }
}

// Lider onayı bekleyen tamamlama
class PendingApproval {
  final int completionId;
  final String taskText;
  final String category;
  final String? proofImagePath;
  final String submitterUsername;

  PendingApproval({
    required this.completionId,
    required this.taskText,
    required this.category,
    this.proofImagePath,
    required this.submitterUsername,
  });

  factory PendingApproval.fromJson(Map<String, dynamic> json) {
    return PendingApproval(
      completionId: json['completionId'] ?? 0,
      taskText: json['taskText'] ?? '',
      category: json['category'] ?? '',
      proofImagePath: json['proofImagePath'],
      submitterUsername: json['submitterUsername'] ?? '',
    );
  }
}

// Grup sıralaması satırı
class LeaderboardEntry {
  final int userId;
  final String username;
  final int groupXp;

  LeaderboardEntry({
    required this.userId,
    required this.username,
    required this.groupXp,
  });

  factory LeaderboardEntry.fromJson(Map<String, dynamic> json) {
    return LeaderboardEntry(
      userId: json['userId'] ?? 0,
      username: json['username'] ?? '',
      groupXp: json['groupXp'] ?? 0,
    );
  }
}
