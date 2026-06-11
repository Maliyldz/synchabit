using SyncHabit.Models; // VerificationStatus enum'u için

namespace SyncHabit.API.Models
{
    public class TaskCompletion
    {
        public int Id { get; set; }

        public int TaskId { get; set; }   // hangi görev
        public int UserId { get; set; }   // kim tamamladı

        public string? ProofImagePath { get; set; }
        public VerificationStatus VerificationStatus { get; set; } = VerificationStatus.Pending;

        public bool IsApproved { get; set; } = false; // Verified ise true
        public DateTime CompletedAt { get; set; } = DateTime.Now;
        public int EarnedXp { get; set; } = 0;
    }
}