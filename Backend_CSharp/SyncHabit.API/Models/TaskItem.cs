using SyncHabit.Models;


namespace SyncHabit.API.Models
{
    public class TaskItem
    {
        public int Id { get; set; }
        public int CreatorId { get; set; } // Hangi kullanıcı oluşturdu?
        public string TaskText { get; set; } = string.Empty;
        public string Category { get; set; } = "Belirsiz";
        public int DifficultyScore { get; set; } = 0;
        public DateTime CreatedAt { get; set; } = DateTime.Now;
        public int? GroupId { get; set; } // Nullable: Grup görevi ise dolu olur

        public bool IsCompleted { get; set; } = false;
        public DateTime? CompletedAt { get; set; }

        public string? ProofImagePath { get; set; }
        public VerificationStatus VerificationStatus { get; set; } = VerificationStatus.Pending;
    }
}