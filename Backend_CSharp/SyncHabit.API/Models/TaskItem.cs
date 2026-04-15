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
    }
}