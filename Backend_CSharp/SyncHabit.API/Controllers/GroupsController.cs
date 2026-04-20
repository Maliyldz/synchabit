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
    public class GroupsController : ControllerBase
    {
        private readonly AppDbContext _context;

        public GroupsController(AppDbContext context)
        {
            _context = context;
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

        [HttpPost("{groupId}/task")]
        public IActionResult AddGroupTask(int groupId, [FromBody] TaskItem task)
        {
            var userId = int.Parse(User.FindFirst(ClaimTypes.NameIdentifier)!.Value);

            // Sadece grup üyeleri gruba görev atayabilir
            if (!_context.GroupMembers.Any(gm => gm.GroupId == groupId && gm.UserId == userId))
                return Unauthorized("Bu gruba görev atama yetkiniz yok.");

            task.GroupId = groupId;
            task.CreatorId = userId;
            task.CreatedAt = DateTime.Now;

            _context.Tasks.Add(task);
            _context.SaveChanges();

            return Ok(task);
        }
    }
}