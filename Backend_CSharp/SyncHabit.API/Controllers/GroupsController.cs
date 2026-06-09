using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using SyncHabit.API.Data;
using SyncHabit.API.Models;
using System.Security.Claims;
using SyncHabit.Services;
using System.Threading.Tasks;

namespace SyncHabit.API.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    [Authorize]
    public class GroupsController : ControllerBase
    {
        private readonly AppDbContext _context;
        private readonly IAIVerificationService _aiService;

        public GroupsController(AppDbContext context, IAIVerificationService aiService)
        {
            _context = context;
            _aiService = aiService;
        }

        [HttpPost]
        public IActionResult CreateGroup([FromBody] Group newGroup)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);
            newGroup.CreatorId = userId;

            _context.Groups.Add(newGroup);
            _context.SaveChanges();

            var member = new GroupMember { GroupId = newGroup.Id, UserId = userId };
            _context.GroupMembers.Add(member);
            _context.SaveChanges();

            return Ok(newGroup);
        }

        [HttpPost("{groupId}/join")]
        public IActionResult JoinGroup(int groupId)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            if (_context.GroupMembers.Any(gm => gm.GroupId == groupId && gm.UserId == userId))
                return BadRequest("Zaten bu grubun üyesisiniz.");

            var member = new GroupMember { GroupId = groupId, UserId = userId };
            _context.GroupMembers.Add(member);
            _context.SaveChanges();

            return Ok("Gruba başarıyla katıldınız.");
        }

        // Kullanıcının üye olduğu grupları getir
        [HttpGet("mine")]
        public IActionResult GetMyGroups()
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            // Üyesi olduğum grupların id'lerini bul, sonra o grupları getir
            var myGroupIds = _context.GroupMembers
                .Where(gm => gm.UserId == userId)
                .Select(gm => gm.GroupId)
                .ToList();

            var groups = _context.Groups
                .Where(g => myGroupIds.Contains(g.Id))
                .Select(g => new
                {
                    id = g.Id,
                    name = g.Name,
                    description = g.Description,
                    creatorId = g.CreatorId,
                    isLeader = g.CreatorId == userId  // bu grubun lideri ben miyim?
                })
                .ToList();

            return Ok(groups);
        }

        // Bir grubun üyelerini getir (kullanıcı adlarıyla birlikte)
        [HttpGet("{groupId}/members")]
        public IActionResult GetGroupMembers(int groupId)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            // Sadece grup üyeleri üye listesini görebilir
            if (!_context.GroupMembers.Any(gm => gm.GroupId == groupId && gm.UserId == userId))
                return Unauthorized("Bu grubun üyesi değilsiniz.");

            // GroupMember + User join: userId'den kullanıcı adına ulaş
            var members = _context.GroupMembers
                .Where(gm => gm.GroupId == groupId)
                .Join(_context.Users,
                    gm => gm.UserId,
                    u => u.Id,
                    (gm, u) => new
                    {
                        userId = u.Id,
                        username = u.Username,
                        level = u.Level,
                        joinedAt = gm.JoinedAt
                    })
                .ToList();

            return Ok(members);
        }

        // Bir grubun görevlerini getir
        [HttpGet("{groupId}/tasks")]
        public IActionResult GetGroupTasks(int groupId)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            // Sadece grup üyeleri görevleri görebilir
            if (!_context.GroupMembers.Any(gm => gm.GroupId == groupId && gm.UserId == userId))
                return Unauthorized("Bu grubun üyesi değilsiniz.");

            var tasks = _context.Tasks
                .Where(t => t.GroupId == groupId)
                .Select(t => new
                {
                    id = t.Id,
                    creatorId = t.CreatorId,
                    taskText = t.TaskText,
                    category = t.Category,
                    difficultyScore = t.DifficultyScore,
                    createdAt = t.CreatedAt,
                    groupId = t.GroupId,
                    // Benim bu görevdeki tamamlama durumum (yoksa null)
                    myCompletionStatus = _context.TaskCompletions
                .Where(c => c.TaskId == t.Id && c.UserId == userId)
                .Select(c => c.VerificationStatus.ToString())
                .FirstOrDefault(),
                    // Kaç kişi tamamladı (sadece onaylanmış olanlar)
                    completionCount = _context.TaskCompletions
                .Count(c => c.TaskId == t.Id && c.IsApproved)
                })
                .ToList();

            return Ok(tasks);
        }

        [HttpPost("{groupId}/task")]
        public async Task<IActionResult> AddGroupTask(int groupId, [FromBody] TaskItem task)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            // Sadece grup üyeleri gruba görev atayabilir
            if (!_context.GroupMembers.Any(gm => gm.GroupId == groupId && gm.UserId == userId))
                return Unauthorized("Bu gruba görev atama yetkiniz yok.");

            var nlpResult = await _aiService.VerifyTextAsync(task.TaskText);
            if (!nlpResult.IsApproved)
            {
                return BadRequest(new { Message = nlpResult.Reason });
            }

            task.GroupId = groupId;
            task.CreatorId = userId;
            task.CreatedAt = DateTime.Now;

            _context.Tasks.Add(task);
            _context.SaveChanges();

            return Ok(task);
        }
    }
}