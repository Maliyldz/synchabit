using System.Net.WebSockets;
using Microsoft.AspNetCore.Mvc;
using SyncHabit.API.Data;
using SyncHabit.API.Models;

namespace SyncHabit.API.Controllers
{
    [Route("api/[Controller]")] //Adres: localhost:xxxx/api/task olacak
    [ApiController]
    public class TasksController : ControllerBase
    {
        private readonly AppDbContext _context;

        // Veritabanı köprüsünü (AppDbContext) bu garsona veriyoruz
        public TasksController(AppDbContext context)
        {
            _context = context;
        }

        // 1. Kapı: Tüm görevleri getir (GET İsteği)
        [HttpGet]
        public IActionResult GetTasks()
        {
            var tasks = _context.Tasks.ToList(); //Veritabanındaki tüm görevleri listele
            return Ok(tasks); //200 OK koduyla geri gönder
        }

        // 2. Kapı: Yeni görev ekle (POST İsteği)
        [HttpPost]
        public IActionResult AddTask([FromBody] TaskItem newTask)
        {
            _context.Tasks.Add(newTask); // Yeni görevi veritabanına ekle
            _context.SaveChanges(); // Değişiklikleri kaydet

            return Ok(newTask); // Eklenen görevi geri göster
        }
    }
}