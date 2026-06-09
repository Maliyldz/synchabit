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

        // LİDER bir ARKADAŞINI gruba davet eder
        [HttpPost("{groupId}/invite/{friendId}")]
        public IActionResult InviteToGroup(int groupId, int friendId)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            // 1. Grup var mı ve ben lider miyim?
            var group = _context.Groups.FirstOrDefault(g => g.Id == groupId);
            if (group == null)
                return NotFound("Grup bulunamadı.");
            if (group.CreatorId != userId)
                return Unauthorized("Sadece grup lideri davet gönderebilir.");

            // 2. Davet edilen kişi arkadaşım mı? (kabul edilmiş arkadaşlık)
            bool isFriend = _context.Friendships.Any(f =>
                f.Status == "Accepted" &&
                ((f.UserId == userId && f.FriendId == friendId) ||
                 (f.UserId == friendId && f.FriendId == userId)));
            if (!isFriend)
                return BadRequest("Sadece arkadaşlarınızı davet edebilirsiniz.");

            // 3. Zaten üye mi?
            if (_context.GroupMembers.Any(gm => gm.GroupId == groupId && gm.UserId == friendId))
                return BadRequest("Bu kişi zaten grubun üyesi.");

            // 4. Zaten bekleyen davet var mı?
            if (_context.GroupInvites.Any(i => i.GroupId == groupId && i.InviteeId == friendId && i.Status == "Pending"))
                return BadRequest("Bu kişiye zaten bekleyen bir davet var.");

            var invite = new GroupInvite
            {
                GroupId = groupId,
                InviterId = userId,
                InviteeId = friendId,
                Status = "Pending"
            };
            _context.GroupInvites.Add(invite);
            _context.SaveChanges();

            return Ok("Davet gönderildi.");
        }

        // BANA GELEN bekleyen grup davetleri (grup adı + davet eden adıyla)
        [HttpGet("invites")]
        public IActionResult GetMyInvites()
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            var invites = _context.GroupInvites
                .Where(i => i.InviteeId == userId && i.Status == "Pending")
                .Join(_context.Groups,
                    i => i.GroupId,
                    g => g.Id,
                    (i, g) => new { invite = i, group = g })
                .Join(_context.Users,
                    x => x.invite.InviterId,
                    u => u.Id,
                    (x, u) => new
                    {
                        inviteId = x.invite.Id,
                        groupId = x.group.Id,
                        groupName = x.group.Name,
                        inviterUsername = u.Username
                    })
                .ToList();

            return Ok(invites);
        }

        // DAVETİ KABUL ET → GroupMember olarak eklen
        [HttpPost("invites/{inviteId}/accept")]
        public IActionResult AcceptInvite(int inviteId)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            var invite = _context.GroupInvites
                .FirstOrDefault(i => i.Id == inviteId && i.InviteeId == userId && i.Status == "Pending");
            if (invite == null)
                return NotFound("Kabul edilecek davet bulunamadı.");

            // Zaten üye değilse ekle (çift kontrol)
            if (!_context.GroupMembers.Any(gm => gm.GroupId == invite.GroupId && gm.UserId == userId))
            {
                _context.GroupMembers.Add(new GroupMember
                {
                    GroupId = invite.GroupId,
                    UserId = userId
                });
            }

            invite.Status = "Accepted";
            _context.SaveChanges();

            return Ok("Gruba katıldınız.");
        }
    }
}