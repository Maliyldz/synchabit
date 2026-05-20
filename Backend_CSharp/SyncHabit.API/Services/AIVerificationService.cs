using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Threading.Tasks;
using SyncHabit.Models;

namespace SyncHabit.Services
{
    public class AIVerificationService : IAIVerificationService
    {
        private readonly HttpClient _httpClient;
        private readonly string _aiApiUrl = "http://localhost:8000/predict";

        private static readonly JsonSerializerOptions _jsonOptions = new()
        {
            PropertyNameCaseInsensitive = true
        };

        public AIVerificationService(HttpClient httpClient)
        {
            _httpClient = httpClient;
        }

        public async Task<VerificationResult> VerifyTaskAsync(byte[] imageBytes, string expectedCategory)
        {
            try
            {
                using var request = new HttpRequestMessage(HttpMethod.Post, _aiApiUrl);
                request.Content = new ByteArrayContent(imageBytes);
                request.Content.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
                request.Content.Headers.ContentLength = imageBytes.Length;

                var response = await _httpClient.SendAsync(request);

                if (!response.IsSuccessStatusCode)
                {
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Reason = $"YZ Sunucusuna ulaşılamadı. Durum Kodu: {response.StatusCode}"
                    };
                }

                var jsonString = await response.Content.ReadAsStringAsync();
                var result = JsonSerializer.Deserialize<AIResponseDto>(jsonString, _jsonOptions);

                if (result == null || !result.IsSuccess)
                {
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Reason = result?.Error ?? "YZ fotoğrafı işleyemedi."
                    };
                }

                // Mantık Kontrolleri
                bool isCategoryMatch = result.PredictedClass.Equals(expectedCategory, StringComparison.OrdinalIgnoreCase);
                bool isConfident = result.IsConfident;

                // SENARYO 1: Her şey mükemmel
                if (isCategoryMatch && isConfident)
                {
                    return new VerificationResult
                    {
                        IsApproved = true,
                        Reason = "Görev başarıyla doğrulandı.",
                        DetectedCategory = result.PredictedClass,
                        Confidence = result.Confidence
                    };
                }
                // SENARYO 2: Kategori uyumsuz
                else if (!isCategoryMatch)
                {
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Reason = $"Görsel eşleşmedi. Beklenen: '{expectedCategory}', Algılanan: '{result.PredictedClass}'.",
                        DetectedCategory = result.PredictedClass,
                        Confidence = result.Confidence
                    };
                }
                // SENARYO 3: Kategori doğru ama eminlik oranı düşük (Örn: Çok karanlık/bulanık fotoğraf)
                else
                {
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Reason = $"Fotoğraf net değil. Doğruluk oranı (%{result.Confidence}) sınırın altında kaldı.",
                        DetectedCategory = result.PredictedClass,
                        Confidence = result.Confidence
                    };
                }
            }
            catch (Exception ex)
            {
                return new VerificationResult
                {
                    IsApproved = false,
                    Reason = $"Sistem Hatası: {ex.Message}"
                };
            }
        }
    }
}