import { useState } from 'react';
import { Phone, ArrowRight, Loader2, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import api from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const PhoneLogin = ({ onClose }) => {
  const [step, setStep] = useState(1); // 1: phone input, 2: OTP input
  const [phoneNumber, setPhoneNumber] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [maskedPhone, setMaskedPhone] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const formatPhoneInput = (value) => {
    // Remove non-numeric characters except +
    const cleaned = value.replace(/[^\d+]/g, '');
    return cleaned;
  };

  const handleSendOTP = async () => {
    if (!phoneNumber || phoneNumber.length < 10) {
      toast.error('Please enter a valid phone number');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/auth/phone/send-otp', {
        phone_number: phoneNumber
      });
      
      if (response.data.success) {
        setMaskedPhone(response.data.phone_number);
        setStep(2);
        toast.success('OTP sent! Check your phone for the code.');
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to send OTP';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async () => {
    if (!otpCode || otpCode.length !== 6) {
      toast.error('Please enter the 6-digit code');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/auth/phone/verify-otp', {
        phone_number: phoneNumber,
        otp_code: otpCode,
        full_name: fullName || undefined
      });
      
      if (response.data.success) {
        login(response.data.access_token, response.data.user);
        toast.success(response.data.is_new_user ? 'Account created!' : 'Welcome back!');
        if (onClose) onClose();
        navigate('/');
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to verify OTP';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    setLoading(true);
    try {
      const response = await api.post('/auth/phone/resend-otp', {
        phone_number: phoneNumber
      });
      
      if (response.data.success) {
        toast.success('New OTP sent!');
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Failed to resend OTP';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {step === 1 ? (
        <>
          <div className="text-center mb-4">
            <div className="w-12 h-12 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mx-auto mb-3">
              <Phone className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Sign in with Phone
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              We'll send you a verification code
            </p>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Phone Number
              </label>
              <Input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(formatPhoneInput(e.target.value))}
                placeholder="+1 234 567 8900"
                className="h-11"
                data-testid="phone-input"
              />
              <p className="text-xs text-slate-400 mt-1">
                Include country code (e.g., +1 for US)
              </p>
            </div>

            <Button
              onClick={handleSendOTP}
              disabled={loading || !phoneNumber}
              className="w-full h-11 btn-primary"
              data-testid="send-otp-button"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <ArrowRight className="w-4 h-4 mr-2" />
              )}
              {loading ? 'Sending...' : 'Send Verification Code'}
            </Button>
          </div>
        </>
      ) : (
        <>
          <div className="text-center mb-4">
            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-3">
              <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Enter Verification Code
            </h3>
            <p className="text-sm text-slate-500 mt-1">
              Code sent to {maskedPhone}
            </p>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                6-Digit Code
              </label>
              <Input
                type="text"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                className="h-11 text-center text-2xl tracking-widest font-mono"
                maxLength={6}
                data-testid="otp-input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Your Name (optional)
              </label>
              <Input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="John Doe"
                className="h-10"
                data-testid="name-input"
              />
            </div>

            <Button
              onClick={handleVerifyOTP}
              disabled={loading || otpCode.length !== 6}
              className="w-full h-11 btn-primary"
              data-testid="verify-otp-button"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <CheckCircle className="w-4 h-4 mr-2" />
              )}
              {loading ? 'Verifying...' : 'Verify & Sign In'}
            </Button>

            <div className="flex items-center justify-between text-sm">
              <button
                onClick={() => setStep(1)}
                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              >
                Change number
              </button>
              <button
                onClick={handleResendOTP}
                disabled={loading}
                className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
              >
                Resend code
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default PhoneLogin;
