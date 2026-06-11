namespace SyncHabit.Services
{
    public static class LevelHelper
    {
        // Seviye N'den N+1'e geçmek için gereken XP = N * 100
        // Yani: 1→2 = 100, 2→3 = 200, 3→4 = 300 ...
        // Toplam XP'den mevcut seviyeyi hesaplar.
        public static int CalculateLevel(int totalXp)
        {
            int level = 1;
            int xpNeeded = 100; // 1→2 için gereken
            int remaining = totalXp;

            while (remaining >= xpNeeded)
            {
                remaining -= xpNeeded;
                level++;
                xpNeeded = level * 100; // bir sonraki seviyenin maliyeti
            }
            return level;
        }

        // Mevcut seviyede ne kadar XP toplandı (ilerleme çubuğu için)
        public static int XpInCurrentLevel(int totalXp)
        {
            int level = 1;
            int xpNeeded = 100;
            int remaining = totalXp;

            while (remaining >= xpNeeded)
            {
                remaining -= xpNeeded;
                level++;
                xpNeeded = level * 100;
            }
            return remaining; // bu seviyede toplanan XP
        }

        // Bir sonraki seviye için gereken toplam XP (ilerleme çubuğu paydası)
        public static int XpNeededForNextLevel(int totalXp)
        {
            int level = CalculateLevel(totalXp);
            return level * 100; // mevcut seviyeden sonrakine geçiş maliyeti
        }

        // Bir tamamlamadan kazanılacak XP'yi hesapla
        // AI otomatik onay → tam puan, manuel onay → yarım
        public static int CalculateXpReward(int difficultyScore, bool isManualApproval)
        {
            double multiplier = isManualApproval ? 0.5 : 1.0;
            return (int)(difficultyScore * multiplier);
        }
    }
}