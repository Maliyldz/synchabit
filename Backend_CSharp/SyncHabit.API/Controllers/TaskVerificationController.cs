using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using SyncHabit.Services;
using System.IO;
using System.Threading.Tasks;

namespace SyncHabit.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class TaskVerificationController : ControllerBase
    {
        private readonly IAIVerificationService _aiService;

        // Maksimum dosya boyutu
        private const int MAX_FILE_SIZE_MB = 10;

        // İzin verilen dosya tipleri
        private static readonly string[] ALLOWED_CONTENT_TYPES =
        {
            "image/jpeg", "image/jpg", "image/png", "image/webp"
        };

        public TaskVerificationController(IAIVerificationService aiService)
        {
            _aiService = aiService;
        }

        [HttpPost("verify")]
        public async Task<IActionResult> VerifyTask([FromForm] IFormFile image, [FromForm] string expectedCategory)
        {
            // 1. Güvenlik Kontrolleri

            if (image == null || image.Length == 0)
            {
                return BadRequest(new { Message = "Lütfen bir fotoğraf yükleyin." });
            }

            if (string.IsNullOrWhiteSpace(expectedCategory))
            {
                return BadRequest(new { Message = "Beklenen kategori (expectedCategory) boş olamaz." });
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

            // 2. Flutter'dan gelen dosyayı (IFormFile) byte dizisine (byte[]) çevir
            byte[] imageBytes;
            using (var memoryStream = new MemoryStream())
            {
                await image.CopyToAsync(memoryStream);
                imageBytes = memoryStream.ToArray();
            }

            // 3. Dosyayı AI Servisimize Gönder
            var result = await _aiService.VerifyTaskAsync(imageBytes, expectedCategory);

            // 4. Sonucu Flutter'a Döndür
            // Hem başarılı hem başarısız durumda Ok() dönüyoruz — Flutter, result.IsApproved 
            // field'ından durumu anlayacak ve Reason mesajını kullanıcıya gösterecek
            return Ok(result);
        }
    }
}