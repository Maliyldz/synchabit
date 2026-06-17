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

        // Görsel doğrulaması olan kategoriler (görsel modelin tanıdığı 10 sınıf).
        // İleride model genişlerse burası güncellenir (ya da dinamik endpoint'e geçilir).
        private static readonly string[] IMAGE_VERIFIABLE_CATEGORIES =
        {
            "basketbol", "bisiklet", "evcil_hayvan", "gitar_calma", "ip_atlama",
            "kod_yazma", "bowling", "orgu_orme", "spor_yapma", "voleybol"
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

            // Süre kontrolü: görevin son tarihi geçmişse tamamlanamaz
            if (task.DueDate != null && task.DueDate < DateTime.Now)
            {
                return BadRequest(new { Message = "Bu görevin süresi doldu, artık tamamlanamaz." });
            }
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

            // 5. Görevin durumunu belirle: kategori görsel doğrulamalı mı? bireysel mi grup mu?
            bool hasImageVerification = IMAGE_VERIFIABLE_CATEGORIES
                .Contains(task.Category, StringComparer.OrdinalIgnoreCase);
            bool isIndividual = task.GroupId == null;

            VerificationResult result;

            if (hasImageVerification)
            {
                // Görsel doğrulamalı kategori → AI'ya gönder (servis 30/70 kararı verir)
                result = await _aiService.VerifyTaskAsync(imageBytes, task.Category);
            }
            else
            {
                // Görsel doğrulaması olmayan kategori ("Diğer") → AI'ya gitme, manuel onaya hazırla
                result = new VerificationResult
                {
                    IsApproved = false,
                    Status = VerificationStatus.NeedsReview,
                    Reason = "Bu kategori görsel olarak doğrulanmıyor, manuel onay gerekiyor.",
                    DetectedCategory = task.Category,
                    Confidence = 0
                };
            }

            // 6. Bireysel görev kuralı: NeedsReview'ı otomatik Verified yap (onaylayacak lider yok)
            if (isIndividual && result.Status == VerificationStatus.NeedsReview)
            {
                result.Status = VerificationStatus.Verified;
                result.IsApproved = true;
                result.Reason = "Görev tamamlandı.";
            }

            // 7. Rejected: hiçbir kayıt oluşturma
            if (result.Status == VerificationStatus.Rejected)
            {
                return Ok(result);
            }

            // 8. Verified veya NeedsReview: fotoğrafı kaydet, TaskCompletion oluştur
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

            // Verified ise XP ekle (AI otomatik onay → tam puan, çarpan 1.0)
            if (result.Status == VerificationStatus.Verified)
            {
                var user = _context.Users.FirstOrDefault(u => u.Id == userId);
                if (user != null)
                {
                    int xp = LevelHelper.CalculateXpReward(task.DifficultyScore, isManualApproval: false);
                    user.TotalXP += xp;
                    completion.EarnedXp = xp;
                }
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