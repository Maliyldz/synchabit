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
            // Güvenlik Kontrolleri

            if (image == null || image.Length == 0)
            {
                return BadRequest(new { Message = "Lütfen bir fotoğraf yükleyin." });
            }

            // Dosya boyutu kontrolü
            if (image.Length > MAX_FILE_SIZE_MB * 1024 * 1024)
            {
                return BadRequest(new { Message = $"Dosya boyutu {MAX_FILE_SIZE_MB} MB'dan büyük olamaz." });
            }

            // Content type kontrolü
            if (!System.Array.Exists(ALLOWED_CONTENT_TYPES, ct => ct == image.ContentType?.ToLower()))
            {
                return BadRequest(new { Message = "Sadece JPEG, PNG veya WebP formatındaki resimler kabul edilir." });
            }

            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);
            var task = _context.Tasks.FirstOrDefault(t => t.Id == taskId && t.CreatorId == userId);

            if (task == null)
                return NotFound(new { Message = "Görev bulunamadı veya bu işlem için yetkiniz yok." });

            // Görevin kategorisini backend'in kendisi belirliyor (Flutter göndermiyor)
            var expectedCategory = task.Category;

            // Flutter'dan gelen dosyayı (IFormFile) byte dizisine (byte[]) çevir
            byte[] imageBytes;
            using (var memoryStream = new MemoryStream())
            {
                await image.CopyToAsync(memoryStream);
                imageBytes = memoryStream.ToArray();
            }

            // Dosyayı AI Servisine Gönder
            var result = await _aiService.VerifyTaskAsync(imageBytes, expectedCategory);

            if (result.Status == VerificationStatus.Rejected)
            {
                // Reddedildi: hiçbir şey kaydetme, sadece sonucu dön
                return Ok(result);
            }

            var proofPath = await SaveProofImage(image);
            task.ProofImagePath = proofPath;
            task.VerificationStatus = result.Status;

            if (result.Status == VerificationStatus.Verified)
            {
                // Otomatik onay: görevi tamamla
                task.IsCompleted = true;
                task.CompletedAt = System.DateTime.Now;
            }

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