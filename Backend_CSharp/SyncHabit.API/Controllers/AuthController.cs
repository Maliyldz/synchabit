using Microsoft.AspNetCore.Mvc;
using SyncHabit.API.Data;
using SyncHabit.API.DTOs;
using SyncHabit.API.Models;
using Microsoft.IdentityModel.Tokens;
using Microsoft.AspNetCore.Authorization;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using SyncHabit.Services;

namespace SyncHabit.API.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class AuthController : ControllerBase
    {
        private readonly AppDbContext _context;
        private readonly IConfiguration _configuration;

        public AuthController(AppDbContext context, IConfiguration configuration)
        {
            _context = context;
            _configuration = configuration;
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

            if (_context.Users.Any(u => u.Username == request.Username))
            {
                return BadRequest("Bu kullanıcı adı zaten alınmış.");
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
            // Veritabanından kullanıcı adını bul
            var user = _context.Users.FirstOrDefault(u => u.Username == request.Username);

            if (user == null)
            {
                return BadRequest("Kullanıcı bulunamadı.");
            }

            if (!BCrypt.Net.BCrypt.Verify(request.Password, user.PasswordHash))
            {
                return BadRequest("Hatalı şifre.");
            }

            string token = CreateToken(user);
            return Ok(token);
        }
        // Kullanıcı adına göre arama (arkadaş/üye eklemek için)
        [Authorize]
        [HttpGet("search")]
        public IActionResult SearchUsers([FromQuery] string username)
        {
            if (string.IsNullOrWhiteSpace(username))
            {
                return BadRequest("Arama terimi boş olamaz.");
            }

            var myUserId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            // Zaten arkadaş olduğum (kabul edilmiş) kullanıcıların id'leri
            var friendIds = _context.Friendships
                .Where(f => (f.UserId == myUserId || f.FriendId == myUserId) && f.Status == "Accepted")
                .Select(f => f.UserId == myUserId ? f.FriendId : f.UserId)
                .ToList();

            // Username eşleşen, kendim olmayan VE zaten arkadaşım olmayan kullanıcılar
            var results = _context.Users
                .Where(u => u.Username.Contains(username)
                            && u.Id != myUserId
                            && !friendIds.Contains(u.Id))  // arkadaşları hariç tut
                .Take(20)
                .Select(u => new { u.Id, u.Username, u.TotalXP })
                .ToList()
                .Select(u => new
                {
                    id = u.Id,
                    username = u.Username,
                    level = LevelHelper.CalculateLevel(u.TotalXP)
                })
                .ToList();

            return Ok(results);
        }

        private string CreateToken(User user)
        {
            // Token içine gizleyeceğimiz küçük bilgiler (Adı ve ID'si)
            var claims = new List<Claim>
            {
                new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
                new Claim(ClaimTypes.Name, user.Username)
            };

            // appsettings'ten gizli anahtar çekiliyor
            var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_configuration.GetSection("Jwt:Key").Value!));

            // İmzalama algoritması
            var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha512Signature);

            // Token'ın oluşturulması (1 gün geçerli olacak)
            var token = new JwtSecurityToken(
                claims: claims,
                expires: DateTime.Now.AddDays(1),
                signingCredentials: creds
            );

            var jwt = new JwtSecurityTokenHandler().WriteToken(token);
            return jwt;
        }

        // Giriş yapan kullanıcının profil bilgisi (XP, seviye, ilerleme)
        [Authorize]
        [HttpGet("me")]
        public IActionResult GetMyProfile()
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);
            var user = _context.Users.FirstOrDefault(u => u.Id == userId);
            if (user == null)
                return NotFound("Kullanıcı bulunamadı.");

            return Ok(new
            {
                username = user.Username,
                totalXp = user.TotalXP,
                level = LevelHelper.CalculateLevel(user.TotalXP),
                xpInCurrentLevel = LevelHelper.XpInCurrentLevel(user.TotalXP),
                // Bu seviyenin toplam boyu (ilerleme çubuğunun paydası)
                xpForThisLevel = LevelHelper.XpNeededForNextLevel(user.TotalXP),
                // Sonraki seviyeye kalan XP (opsiyonel gösterim için)
                xpRemainingNewLevel = LevelHelper.XpNeededForNextLevel(user.TotalXP) - LevelHelper.XpInCurrentLevel(user.TotalXP)
            });
        }
    }
}