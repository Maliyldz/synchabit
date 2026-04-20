using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using SyncHabit.API.Data;
using SyncHabit.API.Models;
using System.Security.Claims;

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

        [HttpGet]
        public IActionResult GetFriends()
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            var friends = _context.Friendships
                .Where(f => (f.UserId == userId || f.FriendId == userId) && f.Status == "Accepted")
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

            _context.Tasks.RemoveRange(_context.Tasks.Where(t => false));

            _context.Friendships.Remove(friendship);
            _context.SaveChanges();

            return Ok("Arkadaşlık sona erdi veya istek reddedildi.");
        }
    }
}