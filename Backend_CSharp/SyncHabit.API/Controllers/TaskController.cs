using Microsoft.AspNetCore.Mvc;
using SyncHabit.API.Data;
using SyncHabit.API.Models;
using Microsoft.AspNetCore.Authorization;
using System.Security.Claims;
using SyncHabit.Services;
using System.Threading.Tasks;

namespace SyncHabit.API.Controllers
{
    [Authorize]
    [Route("api/[Controller]")] //Adres: localhost:xxxx/api/task olacak
    [ApiController]
    public class TasksController : ControllerBase
    {
        private readonly AppDbContext _context;
        private readonly IAIVerificationService _aiService;

        // Veritabanı köprüsünü (AppDbContext) bu garsona veriyoruz
        public TasksController(AppDbContext context, IAIVerificationService aiService)
        {
            _context = context;
            _aiService = aiService;
        }

        // 1. Kapı: Tüm görevleri getir (GET İsteği)
        [HttpGet]
        public IActionResult GetTasks()
        {
            var userIdString = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

            if (userIdString == null)
            {
                return Unauthorized("Güvenlik ihlali: Geçerli bir kullanıcı bulunamadı.");
            }

            int myUserId = int.Parse(userIdString);
            var myTasks = _context.Tasks
                .Where(t => t.CreatorId == myUserId && t.GroupId == null) // sadece bireysel görevler
                .Select(t => new
                {
                    id = t.Id,
                    creatorId = t.CreatorId,
                    taskText = t.TaskText,
                    category = t.Category,
                    difficultyScore = t.DifficultyScore,
                    createdAt = t.CreatedAt,
                    groupId = t.GroupId,
                    dueDate = t.DueDate,
                    myCompletionStatus = _context.TaskCompletions
                .Where(c => c.TaskId == t.Id && c.UserId == myUserId)
                .Select(c => c.VerificationStatus.ToString())
                .FirstOrDefault(),
                    completionCount = _context.TaskCompletions
                .Count(c => c.TaskId == t.Id && c.IsApproved)
                })
                .ToList();

            return Ok(myTasks);
        }

        // 2. Kapı: Yeni görev ekle (POST İsteği)
        [HttpPost]
        public async Task<IActionResult> AddTask([FromBody] TaskItem newTask)
        {
            // 1. Token'ın içinden giriş yapan kullanıcının ID'sini çek
            var userIdString = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;

            if (userIdString == null)
            {
                return Unauthorized("Güvenlik ihlali: Geçerli bir kullanıcı bulunamadı.");
            }

            var nlpResult = await _aiService.VerifyTextAsync(newTask.TaskText);

            if (!nlpResult.IsApproved)
            {
                // Eğer AI metni zararlı bulursa, 400 Bad Request ile işlemi reddedip AI'nin sebebini dönüyoruz
                return BadRequest(new { Message = nlpResult.Reason });
            }

            // 2. Görevi oluşturan kişinin ID'sini, Token'dan alınan ID ile eziyoruz
            newTask.CreatorId = int.Parse(userIdString);

            // şimdilik tarih otomatik atılıyor
            newTask.CreatedAt = DateTime.Now;

            //Veritabanına ekleme ve kaydetme 
            _context.Tasks.Add(newTask);
            _context.SaveChanges();

            return Ok(newTask);
        }

        [HttpPut("{id}")]
        public IActionResult UpdateTask(int id, [FromBody] TaskItem updatedTask)
        {
            var userId = int.Parse(User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)!.Value);
            var task = _context.Tasks.FirstOrDefault(t => t.Id == id && t.CreatorId == userId);

            if (task == null)
            {
                return NotFound("Güncellenecek görev bulunamadı veya bu işlem için yetkiniz yok.");
            }

            task.TaskText = updatedTask.TaskText;
            task.Category = updatedTask.Category;
            task.DifficultyScore = updatedTask.DifficultyScore;

            _context.SaveChanges();
            return Ok("Görev başarıyla güncellendi");
        }

        [HttpDelete("{id}")]
        public IActionResult DeleteTask(int id)
        {
            var userId = int.Parse(User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)!.Value);
            var task = _context.Tasks.FirstOrDefault(t => t.Id == id && t.CreatorId == userId);

            if (task == null)
            {
                return NotFound("Silinecek görev bulunamadı veya yetkiniz yok.");
            }

            _context.Tasks.Remove(task);
            _context.SaveChanges();

            return Ok("Görev başarıyla silindi.");
        }
    }
}