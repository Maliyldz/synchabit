namespace SyncHabit.Models
{
    public enum VerificationStatus
    {
        Pending,
        Verified,      // Kategori eşleşti + güven yeterli → otomatik onay
        NeedsReview,   // Kategori eşleşti ama güven düşük → manuel onay bekler
        Rejected       // Kategori eşleşmedi → reddedildi
    }

    public class VerificationResult
    {
        public bool IsApproved { get; set; }
        public string Reason { get; set; }
        public string DetectedCategory { get; set; }
        public double Confidence { get; set; }
        public VerificationStatus Status { get; set; }
    }
}