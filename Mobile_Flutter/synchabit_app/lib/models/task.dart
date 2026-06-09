class Task {
  final int id;
  final int creatorId;
  final String taskText;
  final String category;
  final int difficultyScore;
  final DateTime? createdAt;
  final int? groupId;

  final String? myCompletionStatus; // "Verified" | "NeedsReview" | null
  final int completionCount;

  Task({
    required this.id,
    required this.creatorId,
    required this.taskText,
    required this.category,
    required this.difficultyScore,
    this.createdAt,
    this.groupId,
    this.myCompletionStatus,
    this.completionCount = 0,
  });

  bool get isVerifiedByMe => myCompletionStatus == 'Verified';
  bool get isPendingReviewByMe => myCompletionStatus == 'NeedsReview';
  bool get isDoneByMe =>
      myCompletionStatus == 'Verified' ||
      myCompletionStatus == 'NeedsReview'; // herhangi bir tamamlama var mı

  // Backend'den gelen JSON → Task nesnesi
  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id: json['id'] ?? 0,
      creatorId: json['creatorId'] ?? 0,
      taskText: json['taskText'] ?? '',
      category: json['category'] ?? 'Belirsiz',
      difficultyScore: json['difficultyScore'] ?? 0,
      createdAt: json['createdAt'] != null
          ? DateTime.tryParse(json['createdAt'].toString())
          : null,
      groupId: json['groupId'],
      myCompletionStatus: json['myCompletionStatus'],
      completionCount: json['completionCount'] ?? 0,
    );
  }
}
