using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using SyncHabit.Models;

namespace SyncHabit.Services
{
    public class AIVerificationService : IAIVerificationService
    {
        private readonly HttpClient _httpClient;
        private readonly string _aiBaseUrl = "http://localhost:8000";
        private readonly string _nlpBaseUrl = "http://localhost:8001";

        // Görsel doğrulama güven eşikleri (0-100 ölçeği)
        private const double VERIFY_THRESHOLD = 70.0;  // bu ve üstü → Verified
        private const double REVIEW_THRESHOLD = 30.0;  // bu ile 70 arası → NeedsReview, altı → Rejected

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
                var targetUrl = $"{_aiBaseUrl}/predict";

                using var request = new HttpRequestMessage(HttpMethod.Post, targetUrl);
                request.Content = new ByteArrayContent(imageBytes);
                request.Content.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
                request.Content.Headers.ContentLength = imageBytes.Length;

                var response = await _httpClient.SendAsync(request);

                if (!response.IsSuccessStatusCode)
                {
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Status = VerificationStatus.Rejected,
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
                        Status = VerificationStatus.Rejected,
                        Reason = result?.Error ?? "YZ fotoğrafı işleyemedi."
                    };
                }

                bool isCategoryMatch = result.PredictedClass.Equals(expectedCategory, StringComparison.OrdinalIgnoreCase);

                // ADIM 1: Kategori tutmuyorsa → confidence'a bakmadan Rejected
                if (!isCategoryMatch)
                {
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Status = VerificationStatus.Rejected,
                        Reason = "Yüklediğin fotoğraf bu görevle eşleşmedi. Lütfen göreve uygun bir fotoğraf yükle.",
                        DetectedCategory = result.PredictedClass,
                        Confidence = result.Confidence
                    };
                }

                // ADIM 2: Kategori tutuyor → güven skoruna göre 3 katman
                if (result.Confidence >= VERIFY_THRESHOLD)
                {
                    // 70+ → Verified
                    return new VerificationResult
                    {
                        IsApproved = true,
                        Status = VerificationStatus.Verified,
                        Reason = "Görev başarıyla doğrulandı.",
                        DetectedCategory = result.PredictedClass,
                        Confidence = result.Confidence
                    };
                }
                else if (result.Confidence >= REVIEW_THRESHOLD)
                {
                    // 30-70 → NeedsReview (manuel onay)
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Status = VerificationStatus.NeedsReview,
                        Reason = $"Doğruluk oranı (%{result.Confidence}) orta seviyede. Manuel onay gerekiyor.",
                        DetectedCategory = result.PredictedClass,
                        Confidence = result.Confidence
                    };
                }
                else
                {
                    // 30 altı → Rejected
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Status = VerificationStatus.Rejected,
                        Reason = $"Doğruluk oranı (%{result.Confidence}) çok düşük. Fotoğraf reddedildi.",
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
                    Status = VerificationStatus.Rejected,
                    Reason = $"Sistem Hatası: {ex.Message}"
                };
            }
        }

        public async Task<VerificationResult> VerifyTextAsync(string text)
        {
            try
            {
                // NLP server port 8001'de, endpoint /predict
                var targetUrl = $"{_nlpBaseUrl}/predict";

                // Metni API'nin beklediği {"text": "..."} formatına getirip JSON yapıyoruz
                var payload = JsonSerializer.Serialize(new { text = text }, _jsonOptions);
                var content = new StringContent(payload, Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync(targetUrl, content);

                if (!response.IsSuccessStatusCode)
                {
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Reason = $"YZ Sunucusuna ulaşılamadı. Kod: {response.StatusCode}"
                    };
                }

                var jsonString = await response.Content.ReadAsStringAsync();

                // Python NLP server'ı şu formatta dönüyor:
                // { "action": "block"|"warn"|"allow", "probability": 0.93,
                //   "category": "self_harm", "matched_keywords": [...],
                //   "reason": "hard_block", "is_safe": false }
                var nlpResponse = JsonSerializer.Deserialize<NLPResponseDto>(jsonString, _jsonOptions);

                if (nlpResponse == null)
                {
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Reason = "Metin doğrulama servisinden geçerli yanıt alınamadı."
                    };
                }

                // 3-tier kararı VerificationResult'a maple
                return MapNLPResponseToResult(nlpResponse);
            }
            catch (Exception ex)
            {
                return new VerificationResult { IsApproved = false, Reason = $"Sistem Hatası: {ex.Message}" };
            }
        }

        /// <summary>
        /// NLP response'unu VerificationResult yapısına çevirir.
        /// 3-tier mimari: Block ve Warn = engelle, Allow = geçir.
        /// </summary>
        private static VerificationResult MapNLPResponseToResult(NLPResponseDto nlp)
        {
            switch (nlp.Action?.ToLowerInvariant())
            {
                case "allow":
                    return new VerificationResult
                    {
                        IsApproved = true,
                        Reason = "Metin güvenli bulundu.",
                        Confidence = (int)(nlp.Probability * 100)
                    };

                case "warn":
                    // Şüpheli içerik — şu an güvenli tarafta kalıp blokluyoruz
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Reason = "Bu görev içeriği şüpheli bulundu, lütfen ifadenizi gözden geçirin.",
                        DetectedCategory = nlp.Category,
                        Confidence = (int)(nlp.Probability * 100)
                    };

                case "block":
                default:
                    return new VerificationResult
                    {
                        IsApproved = false,
                        Reason = "Bu görev içeriği SyncHabit politikalarına uygun değil.",
                        DetectedCategory = nlp.Category,
                        Confidence = (int)(nlp.Probability * 100)
                    };
            }
        }
    }

    internal sealed class NLPResponseDto
    {
        [System.Text.Json.Serialization.JsonPropertyName("action")]
        public string? Action { get; set; }

        [System.Text.Json.Serialization.JsonPropertyName("probability")]
        public double Probability { get; set; }

        [System.Text.Json.Serialization.JsonPropertyName("category")]
        public string? Category { get; set; }

        [System.Text.Json.Serialization.JsonPropertyName("matched_keywords")]
        public List<string>? MatchedKeywords { get; set; }

        [System.Text.Json.Serialization.JsonPropertyName("reason")]
        public string? Reason { get; set; }

        [System.Text.Json.Serialization.JsonPropertyName("is_safe")]
        public bool IsSafe { get; set; }
    }
}