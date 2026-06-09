using Microsoft.EntityFrameworkCore;
using SyncHabit.API.Models;
using SyncHabit.Models;

namespace SyncHabit.API.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
        {
        }


        public DbSet<User> Users { get; set; }
        public DbSet<TaskItem> Tasks { get; set; }
        public DbSet<Friendship> Friendships { get; set; }
        public DbSet<Group> Groups { get; set; }
        public DbSet<GroupMember> GroupMembers { get; set; }
        public DbSet<TaskCompletion> TaskCompletions { get; set; }
        public DbSet<GroupInvite> GroupInvites { get; set; }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            // VerificationStatus enum'unu veritabanında string olarak sakla
            modelBuilder.Entity<TaskItem>()
                .Property(t => t.VerificationStatus)
                .HasConversion<string>();

            //username benzersiz olmalı (arama ve arkadaş ekleme için)
            modelBuilder.Entity<User>()
                .HasIndex(u => u.Username)
                .IsUnique();

            // TaskCompletion'ın VerificationStatus'ını da string sakla
            modelBuilder.Entity<TaskCompletion>()
                .Property(c => c.VerificationStatus)
                .HasConversion<string>();

            // Bir kullanıcı bir görevi yalnızca bir kez tamamlayabilir
            modelBuilder.Entity<TaskCompletion>()
                .HasIndex(c => new { c.TaskId, c.UserId })
                .IsUnique();
        }
    }
}