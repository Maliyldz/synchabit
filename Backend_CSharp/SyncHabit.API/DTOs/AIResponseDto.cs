using System.Text.Json.Serialization;

namespace SyncHabit.Models
{
    public class AIResponseDto
    {
        [JsonPropertyName("is_success")]
        public bool IsSuccess { get; set; }

        [JsonPropertyName("predicted_class")]
        public string PredictedClass { get; set; }

        [JsonPropertyName("confidence")]
        public double Confidence { get; set; }

        [JsonPropertyName("is_confident")]
        public bool IsConfident { get; set; }

        [JsonPropertyName("error")]
        public string Error { get; set; }
    }
}