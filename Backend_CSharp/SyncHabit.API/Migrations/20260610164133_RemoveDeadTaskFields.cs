using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SyncHabit.API.Migrations
{
    /// <inheritdoc />
    public partial class RemoveDeadTaskFields : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "CompletedAt",
                table: "Tasks");

            migrationBuilder.DropColumn(
                name: "IsCompleted",
                table: "Tasks");

            migrationBuilder.DropColumn(
                name: "ProofImagePath",
                table: "Tasks");

            migrationBuilder.DropColumn(
                name: "VerificationStatus",
                table: "Tasks");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<DateTime>(
                name: "CompletedAt",
                table: "Tasks",
                type: "datetime2",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "IsCompleted",
                table: "Tasks",
                type: "bit",
                nullable: false,
                defaultValue: false);

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
    }
}
