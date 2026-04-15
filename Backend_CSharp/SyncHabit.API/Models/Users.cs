namespace SyncHabit.API.Models
{
    public class User
    {
        public int Id { get; set; }
        public string Username { get; set; } = string.Empty;
        public string Email { get; set; } = string.Empty;
        public string PasswordHash { get; set; } = string.Empty;
        public int TotalXP { get; set; } = 0;
        public int Level { get; set; } = 1;
    }
}