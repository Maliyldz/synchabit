using Microsoft.EntityFrameworkCore;
using SyncHabit.API.Models;

namespace SyncHabit.API.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
        {
        }

        // Veritabanında oluşacak tablolarımızın isimleri
        public DbSet<User> Users { get; set; }
        public DbSet<TaskItem> Tasks { get; set; }
    }
}