namespace SyncHabit.API.Models
{
    public class GroupInvite
    {
        public int Id { get; set; }
        public int GroupId { get; set; }      // hangi gruba
        public int InviterId { get; set; }    // kim davet etti (lider)
        public int InviteeId { get; set; }    // kim davet edildi
        public string Status { get; set; } = "Pending"; // Pending / Accepted / Rejected
        public DateTime CreatedAt { get; set; } = DateTime.Now;
    }
}