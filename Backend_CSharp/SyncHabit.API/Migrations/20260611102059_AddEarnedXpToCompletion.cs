using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SyncHabit.API.Migrations
{
    /// <inheritdoc />
    public partial class AddEarnedXpToCompletion : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "EarnedXp",
                table: "TaskCompletions",
                type: "int",
                nullable: false,
                defaultValue: 0);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "EarnedXp",
                table: "TaskCompletions");
        }
    }
}
