using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using SyncHabit.API.Data;
using SyncHabit.API.Models;
using System.Security.Claims;
using SyncHabit.Services;

namespace SyncHabit.API.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Authorize]
    public class FriendsController : ControllerBase
    {
        private readonly AppDbContext _context;

        public FriendsController(AppDbContext context)
        {
            _context = context;
        }

        [HttpPost("add/{friendId}")]
        public IActionResult SendRequest(int friendId)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            if (userId == friendId) return BadRequest("Kendine arkadaşlık isteği gönderemezsin.");

            var existing = _context.Friendships.FirstOrDefault(f =>
                (f.UserId == userId && f.FriendId == friendId) ||
                (f.UserId == friendId && f.FriendId == userId));

            if (existing != null) return BadRequest("Zaten bir istek var veya arkadaşsınız.");

            var friendship = new Friendship
            {
                UserId = userId,
                FriendId = friendId,
                Status = "Pending"
            };

            _context.Friendships.Add(friendship);
            _context.SaveChanges();

            return Ok("Arkadaşlık isteği gönderildi.");
        }

        [HttpGet("requests")]
        public IActionResult GetPendingRequests()
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            // Bana (FriendId) gelen, henüz kabul edilmemiş istekler
            var requests = _context.Friendships
                .Where(f => f.FriendId == userId && f.Status == "Pending")
                .Join(_context.Users,
                    f => f.UserId,          // isteği gönderen kişi
                    u => u.Id,
                    (f, u) => new
                    {
                        requestId = f.Id,    // kabul/red için bu id gerekli
                        senderId = u.Id,
                        senderUsername = u.Username,
                        senderLevel = u.Level
                    })
                .ToList();

            return Ok(requests);
        }

        [HttpGet]
        public IActionResult GetFriends()
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            var friendships = _context.Friendships
                .Where(f => (f.UserId == userId || f.FriendId == userId) && f.Status == "Accepted")
                .ToList();

            var friendIds = friendships
                .Select(f => f.UserId == userId ? f.FriendId : f.UserId)
                .ToList();

            var friends = _context.Users
                .Where(u => friendIds.Contains(u.Id))
                .Select(u => new { u.Id, u.Username, u.TotalXP })  // önce ham veriyi çek
                .ToList()  // belleğe al
                .Select(u => new
                {
                    userId = u.Id,
                    username = u.Username,
                    level = LevelHelper.CalculateLevel(u.TotalXP)  // bellekte hesapla
                })
                .ToList();

            return Ok(friends);
        }

        // ARKADAŞLIK İSTEĞİNİ KABUL ET
        [HttpPost("accept/{requestId}")]
        public IActionResult AcceptRequest(int requestId)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            var friendship = _context.Friendships.FirstOrDefault(f => f.Id == requestId && f.FriendId == userId && f.Status == "Pending");

            if (friendship == null) return NotFound("Onaylanacak istek bulunamadı.");

            friendship.Status = "Accepted";
            _context.SaveChanges();

            return Ok("Arkadaşlık isteği kabul edildi. Artık arkadaşsınız!");
        }

        // ARKADAŞI SİL / İSTEĞİ REDDET
        [HttpDelete("{requestId}")]
        public IActionResult RemoveFriend(int requestId)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            var friendship = _context.Friendships.FirstOrDefault(f => f.Id == requestId && (f.UserId == userId || f.FriendId == userId));

            if (friendship == null) return NotFound("İlişki bulunamadı.");

            _context.Friendships.Remove(friendship);
            _context.SaveChanges();

            return Ok("Arkadaşlık sona erdi veya istek reddedildi.");
        }
    }
}