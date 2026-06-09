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
