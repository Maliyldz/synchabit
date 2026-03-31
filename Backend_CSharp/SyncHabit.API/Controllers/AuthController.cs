using Microsoft.AspNetCore.Mvc;
using SyncHabit.API.Data;
using SyncHabit.API.DTOs;
using SyncHabit.API.Models;

namespace SyncHabit.API.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        private readonly AppDbContext _context;

        public AuthController(AppDbContext context)
        {
            _context = context;
        }

        // 1. KAYIT OL (REGISTER) KAPISI
        [HttpPost("register")]
        public IActionResult Register([FromBody] UserRegisterDto request)
        {
            // E-posta sistemde var mı kontrol
            if (_context.Users.Any(u => u.Email == request.Email))
            {
                return BadRequest("Bu e-posta adresi zaten kullanılıyor.");
            }

            // Şifreyi BCrypt ile kırılmaz hale getir (Hash'le)
            string passwordHash = BCrypt.Net.BCrypt.HashPassword(request.Password);

            // Yeni kullanıcıyı oluştur
            var newUser = new User
            {
                Username = request.Username,
                Email = request.Email,
                PasswordHash = passwordHash,
                TotalXP = 0,
                Level = 1
            };

            // Veritabanına kaydet
            _context.Users.Add(newUser);
            _context.SaveChanges();

            return Ok("Kullanıcı başarıyla oluşturuldu!");
        }

        // 2. GİRİŞ YAP (LOGIN) KAPISI
        [HttpPost("login")]
        public IActionResult Login([FromBody] UserLoginDto request)
        {
            // Veritabanından e-postayı bul
            var user = _context.Users.FirstOrDefault(u => u.Email == request.Email);

            if (user == null)
            {
                return BadRequest("Kullanıcı bulunamadı.");
            }

            // Girilen şifre ile veritabanındaki şifreli (hash) metin eşleşiyor mu kontrol et
            if (!BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            {
                return BadRequest("Hatalı şifre.");
            }

            return Ok($"Giriş başarılı! Hoş geldin, {user.Username}.");
        }
    }
}