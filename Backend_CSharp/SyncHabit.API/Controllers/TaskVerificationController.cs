using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using System.Security.Claims;
using SyncHabit.Services;
using SyncHabit.Models;
using SyncHabit.API.Data;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using SyncHabit.API.Models;

namespace SyncHabit.Controllers
{
    public class TextVerificationRequest
    {
        public string Text { get; set; }
    }

    [Route("api/[controller]")]
    [ApiController]
    [Authorize]
    public class TaskVerificationController : ControllerBase
    {
        private readonly IAIVerificationService _aiService;
        private readonly AppDbContext _context;
        private readonly IWebHostEnvironment _environment;

        // Maksimum dosya boyutu
        private const int MAX_FILE_SIZE_MB = 10;

        // İzin verilen dosya tipleri
        private static readonly string[] ALLOWED_CONTENT_TYPES =
        {
            "image/jpeg", "image/jpg", "image/png", "image/webp"
        };

        public TaskVerificationController(
            IAIVerificationService aiService,
            AppDbContext context,
            IWebHostEnvironment environment)
        {
            _aiService = aiService;
            _context = context;
            _environment = environment;
        }

        [HttpPost("verify")]
        public async Task<IActionResult> VerifyTask([FromForm] IFormFile image, [FromForm] int taskId)
        {
            // 1. Güvenlik kontrolleri
            if (image == null || image.Length == 0)
                return BadRequest(new { Message = "Lütfen bir fotoğraf yükleyin." });

            if (image.Length > MAX_FILE_SIZE_MB * 1024 * 1024)
                return BadRequest(new { Message = $"Dosya boyutu {MAX_FILE_SIZE_MB} MB'dan büyük olamaz." });

            if (!System.Array.Exists(ALLOWED_CONTENT_TYPES, ct => ct == image.ContentType?.ToLower()))
                return BadRequest(new { Message = "Sadece JPEG, PNG veya WebP formatındaki resimler kabul edilir." });

            // 2. Token'dan kullanıcı, görevi bul
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            var task = _context.Tasks.FirstOrDefault(t => t.Id == taskId);
            if (task == null)
                return NotFound(new { Message = "Görev bulunamadı." });

            // Yetki: kendi görevim VEYA üyesi olduğum grubun görevi
            bool isOwnTask = task.CreatorId == userId;
            bool isGroupMember = task.GroupId != null &&
                _context.GroupMembers.Any(gm => gm.GroupId == task.GroupId && gm.UserId == userId);

            if (!isOwnTask && !isGroupMember)
                return Unauthorized(new { Message = "Bu görevi tamamlama yetkiniz yok." });

            // 3. Tekrar tamamlama kontrolü
            var existing = _context.TaskCompletions
                .FirstOrDefault(c => c.TaskId == taskId && c.UserId == userId);
            if (existing != null)
                return BadRequest(new { Message = "Bu görevi zaten tamamladınız." });

            // 4. Fotoğrafı byte'a çevir
            byte[] imageBytes;
            using (var memoryStream = new MemoryStream())
            {
                await image.CopyToAsync(memoryStream);
                imageBytes = memoryStream.ToArray();
            }

            // 5. AI doğrulaması (görevin kategorisini backend belirliyor)
            var result = await _aiService.VerifyTaskAsync(imageBytes, task.Category);

            // 6. Rejected: hiçbir kayıt oluşturma
            if (result.Status == VerificationStatus.Rejected)
            {
                return Ok(result);
            }

            // 7. Verified veya NeedsReview: fotoğrafı kaydet, TaskCompletion oluştur
            var proofPath = await SaveProofImage(image);

            var completion = new TaskCompletion
            {
                TaskId = taskId,
                UserId = userId,
                ProofImagePath = proofPath,
                VerificationStatus = result.Status,
                IsApproved = result.Status == VerificationStatus.Verified,
                CompletedAt = DateTime.Now
            };

            _context.TaskCompletions.Add(completion);
            _context.SaveChanges();

            return Ok(result);
        }

        private async Task<string> SaveProofImage(IFormFile file)
        {
            var extension = Path.GetExtension(file.FileName).ToLowerInvariant();
            var fileName = System.Guid.NewGuid().ToString() + extension;

            var uploadsFolder = Path.Combine(
                _environment.WebRootPath ?? Path.Combine(Directory.GetCurrentDirectory(), "wwwroot"),
                "uploads");

            if (!Directory.Exists(uploadsFolder))
                Directory.CreateDirectory(uploadsFolder);

            var filePath = Path.Combine(uploadsFolder, fileName);
            using (var stream = new FileStream(filePath, FileMode.Create))
            {
                await file.CopyToAsync(stream);
            }

            return $"/uploads/{fileName}";
        }

        // --- 2. METİN DOĞRULAMA ENDPOINT'İ (YENİ) ---
        [HttpPost("check-text")]
        public async Task<IActionResult> CheckText([FromBody] TextVerificationRequest request)
        {
            // Güvenlik ve Boşluk Kontrolü
            if (request == null || string.IsNullOrWhiteSpace(request.Text))
            {
                return BadRequest(new { Message = "Görev metni boş olamaz." });
            }

            // AI Servisine metni gönder
            var result = await _aiService.VerifyTextAsync(request.Text);

            // Sonucu Flutter'a döndür
            return Ok(result);
        }
    }
}