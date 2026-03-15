import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
} from 'react-native';
import { useAuthStore } from '../../../stores/auth-store';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Colors, Spacing, FontSize, BorderRadius } from '../../../constants/colors';

const RESEND_COOLDOWN = 60;

export default function VerifyCodeModal() {
  const [code, setCode] = useState('');
  const [cooldown, setCooldown] = useState(0);
  const { verify, resendCode, pendingEmail, isLoading, error, clearError } = useAuthStore();

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleVerify = async () => {
    if (!pendingEmail || code.length !== 6) return;
    await verify({ email: pendingEmail, code });
  };

  const handleResend = async () => {
    if (cooldown > 0) return;
    await resendCode();
    setCooldown(RESEND_COOLDOWN);
  };

  if (!pendingEmail) return null;

  return (
    <Modal visible transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.modal}>
          <Text style={styles.title}>Verify Email</Text>
          <Text style={styles.subtitle}>
            We sent a 6-digit code to {pendingEmail}
          </Text>

          <Input
            label="Verification Code"
            placeholder="000000"
            value={code}
            onChangeText={(t) => { clearError(); setCode(t.replace(/\D/g, '').slice(0, 6)); }}
            keyboardType="number-pad"
            maxLength={6}
          />

          {error && <Text style={styles.error}>{error}</Text>}

          <Button
            title="Verify"
            onPress={handleVerify}
            loading={isLoading}
            disabled={code.length !== 6}
            size="lg"
            style={styles.button}
          />

          <TouchableOpacity onPress={handleResend} disabled={cooldown > 0}>
            <Text style={[styles.resend, cooldown > 0 && styles.resendDisabled]}>
              {cooldown > 0
                ? `Resend code in ${cooldown}s`
                : 'Resend code'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    padding: Spacing.xxl,
  },
  modal: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.xxl,
  },
  title: {
    fontSize: FontSize.xl,
    fontWeight: '700',
    color: Colors.text,
    textAlign: 'center',
    marginBottom: Spacing.sm,
  },
  subtitle: {
    fontSize: FontSize.md,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginBottom: Spacing.xl,
  },
  error: {
    color: Colors.error,
    fontSize: FontSize.sm,
    textAlign: 'center',
    marginBottom: Spacing.md,
  },
  button: { marginTop: Spacing.sm },
  resend: {
    color: Colors.primary,
    fontSize: FontSize.md,
    textAlign: 'center',
    marginTop: Spacing.lg,
    fontWeight: '500',
  },
  resendDisabled: {
    color: Colors.textSecondary,
  },
});
