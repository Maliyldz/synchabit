using Microsoft.EntityFrameworkCore;
using SyncHabit.API.Data;

var builder = WebApplication.CreateBuilder(args);

// 1. Veritabanı bağlantımız (Bunu zaten harika bir şekilde eklemiştin)
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("DefaultConnection")));

// 2. Yazdığımız Controller'ları (TasksController) sisteme tanıtıyoruz!
builder.Services.AddControllers();

// Senin başarıyla kurduğun Swagger ayarları
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

// Geliştirme ortamında Swagger'ı aç
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

// app.UseHttpsRedirection(); // Hata vermemesi için kapalı tutuyoruz

// 3. Controller rotalarını dış dünyaya açıyoruz!
app.MapControllers();

app.Run();