using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SyncHabit.API.Migrations
{
    /// <inheritdoc />
    public partial class AddFriendshipSystem : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.RenameColumn(
                name: "FrienId",
                table: "Friendships",
                newName: "FriendId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.RenameColumn(
                name: "FriendId",
                table: "Friendships",
                newName: "FrienId");
        }
    }
}
