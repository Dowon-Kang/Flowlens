import 'package:supabase_flutter/supabase_flutter.dart';
class BookingRepository {
  Future<dynamic> listBookings() async {
    return Supabase.instance.client.from('bookings').select();
  }
}
