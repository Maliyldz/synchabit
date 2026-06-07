using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SyncHabit.API.Migrations
{
    /// <inheritdoc />
    public partial class AddProofAndVerificationStatus : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "ProofImagePath",
                table: "Tasks",
                type: "nvarchar(max)",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "VerificationStatus",
                table: "Tasks",
                type: "nvarchar(max)",
                nullable: false,
                defaultValue: "");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "ProofImagePath",
                table: "Tasks");

            migrationBuilder.DropColumn(
                name: "VerificationStatus",
                table: "Tasks");
        }
    }
}
