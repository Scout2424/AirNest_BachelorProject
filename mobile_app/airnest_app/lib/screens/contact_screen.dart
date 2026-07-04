import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../theme.dart';
import '../widgets/common.dart';

class ContactScreen extends StatefulWidget {
  const ContactScreen({super.key});
  @override
  State<ContactScreen> createState() => _ContactScreenState();
}

class _ContactScreenState extends State<ContactScreen> {
  final _api = ApiService();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _subject = TextEditingController();
  final _message = TextEditingController();

  static const _allowedDomains = ['gmail.com', 'yahoo.com'];
  String? _nameErr, _emailErr, _subjectErr, _messageErr;
  bool _sending = false;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _subject.dispose();
    _message.dispose();
    super.dispose();
  }

  bool _validEmail(String v) {
    final parts = v.trim().split('@');
    return parts.length == 2 && _allowedDomains.contains(parts[1].toLowerCase());
  }

  Future<void> _submit() async {
    final name = _name.text.trim();
    final email = _email.text.trim();
    final subject = _subject.text.trim();
    final message = _message.text.trim();

    setState(() {
      _nameErr = name.isEmpty ? 'Name cannot be empty.' : null;
      _emailErr = (!_validEmail(email) || email.isEmpty)
          ? 'Please use a @gmail or @yahoo address.'
          : null;
      _subjectErr = subject.isEmpty ? 'Subject cannot be empty.' : null;
      _messageErr = message.isEmpty ? 'Message cannot be empty.' : null;
    });

    if (_nameErr != null ||
        _emailErr != null ||
        _subjectErr != null ||
        _messageErr != null) {
      return;
    }

    setState(() => _sending = true);
    try {
      final ok = await _api.sendContact(
        name: name,
        email: email,
        subject: subject,
        message: message,
      );
      if (!mounted) return;
      if (ok) {
        _name.clear();
        _email.clear();
        _subject.clear();
        _message.clear();
        _toast('Message sent successfully!', AppColors.safe);
      } else {
        _toast('The message was not sent. Please try again.', AppColors.danger);
      }
    } catch (_) {
      if (mounted) {
        _toast('Could not reach the server. Please try again.', AppColors.danger);
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  void _toast(String msg, Color color) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      backgroundColor: color,
      behavior: SnackBarBehavior.floating,
    ));
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      children: [
        const PageTitle('Get in Touch'),
        const SizedBox(height: 4),
        Text('Send a message.', style: AppText.body(14, color: AppColors.muted)),
        const SizedBox(height: 16),
        SurfaceCard(
          child: Column(
            children: [
              _field('Name', _name, 'Enter your name', _nameErr),
              _field('Email', _email,
                  "ex: 'name@gmail.com' or 'name@yahoo.com'", _emailErr,
                  keyboard: TextInputType.emailAddress),
              _field('Subject', _subject, 'Enter subject', _subjectErr),
              _field('Message', _message, 'Write your message here…',
                  _messageErr,
                  maxLines: 6),
              const SizedBox(height: 4),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.navBg,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  onPressed: _sending ? null : _submit,
                  child: _sending
                      ? const SizedBox(
                          height: 18,
                          width: 18,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('Send Message'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _field(String label, TextEditingController c, String hint, String? err,
      {int maxLines = 1, TextInputType? keyboard}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: AppText.body(13,
                  color: AppColors.muted, weight: FontWeight.w600)),
          const SizedBox(height: 6),
          TextField(
            controller: c,
            maxLines: maxLines,
            keyboardType: keyboard,
            style: AppText.body(14),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: AppText.body(13, color: AppColors.muted),
              isDense: true,
              filled: true,
              fillColor: Colors.white,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              border:
                  OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: BorderSide(
                    color: err != null
                        ? AppColors.danger
                        : Colors.black.withOpacity(0.15)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: BorderSide(
                    color: err != null ? AppColors.danger : AppColors.navBg,
                    width: 1.5),
              ),
            ),
          ),
          if (err != null) ...[
            const SizedBox(height: 4),
            Text(err, style: AppText.body(12, color: AppColors.danger)),
          ],
        ],
      ),
    );
  }
}
