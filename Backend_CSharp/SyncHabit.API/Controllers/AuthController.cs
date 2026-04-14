using Microsoft.AspNetCore.Mvc;
using SyncHabit.API.Data;
using SyncHabit.API.DTOs;
using SyncHabit.API.Models;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;

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

            string token = CreateToken(user);
            return Ok(token);
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
    }
}