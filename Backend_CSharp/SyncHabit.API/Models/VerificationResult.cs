namespace SyncHabit.Models
{
    public class VerificationResult
    {
        public bool IsApproved { get; set; }
        public string Reason { get; set; }
        public string DetectedCategory { get; set; }
        public double Confidence { get; set; }
    }
}