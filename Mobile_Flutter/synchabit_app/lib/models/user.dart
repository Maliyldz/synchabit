// İleride backend'den kullanıcı profili (username, level, xp) çekersek
// bu sınıfı genişleteceğiz. Şimdilik auth akışı için token yeterli.
class AuthResult {
  final String token;
  AuthResult({required this.token});
}
