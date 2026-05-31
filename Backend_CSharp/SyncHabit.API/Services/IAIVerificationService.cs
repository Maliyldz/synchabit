using SyncHabit.Models;

namespace SyncHabit.Services
{
    public interface IAIVerificationService
    {
        Task<VerificationResult> VerifyTaskAsync(byte[] imageBytes, string expectedCategory);

        Task<VerificationResult> VerifyTextAsync(string text);
    }
}