class TaskCategory {
  final String label; // Kullanıcının gördüğü: "Gitar Çalma"
  final String value; // Backend'e/modele giden: "gitar_calma"
  final bool hasImageVerification; // Görsel doğrulama var mı?

  const TaskCategory({
    required this.label,
    required this.value,
    required this.hasImageVerification,
  });
}

// Görsel modelin tanıdığı 10 kategori + görsel doğrulaması olmayan "Diğer".
// value alanları modelin sınıf adlarıyla BİREBİR aynı olmalı.
const List<TaskCategory> kTaskCategories = [
  TaskCategory(
    label: 'Basketbol',
    value: 'basketbol',
    hasImageVerification: true,
  ),
  TaskCategory(
    label: 'Bisiklet',
    value: 'bisiklet',
    hasImageVerification: true,
  ),
  TaskCategory(
    label: 'Evcil Hayvan',
    value: 'evcil_hayvan',
    hasImageVerification: true,
  ),
  TaskCategory(
    label: 'Gitar Çalma',
    value: 'gitar_calma',
    hasImageVerification: true,
  ),
  TaskCategory(
    label: 'İp Atlama',
    value: 'ip_atlama',
    hasImageVerification: true,
  ),
  TaskCategory(
    label: 'Kod Yazma',
    value: 'kod_yazma',
    hasImageVerification: true,
  ),
  TaskCategory(label: 'Okçuluk', value: 'okculuk', hasImageVerification: true),
  TaskCategory(
    label: 'Örgü Örme',
    value: 'orgu_orme',
    hasImageVerification: true,
  ),
  TaskCategory(
    label: 'Spor Yapma',
    value: 'spor_yapma',
    hasImageVerification: true,
  ),
  TaskCategory(
    label: 'Voleybol',
    value: 'voleybol',
    hasImageVerification: true,
  ),
  TaskCategory(
    label: 'Diğer (görsel doğrulama yok)',
    value: 'diger',
    hasImageVerification: false,
  ),
];

// Kategori kodundan (örn. "orgu_orme") okunabilir etiketi (örn. "Örgü Örme") döndürür.
// Bilinmeyen/eski kategori için kodu olduğu gibi döndürür (güvenli geri dönüş).
String categoryLabel(String value) {
  final match = kTaskCategories.firstWhere(
    (c) => c.value == value,
    orElse: () =>
        TaskCategory(label: value, value: value, hasImageVerification: false),
  );
  return match.label;
}
