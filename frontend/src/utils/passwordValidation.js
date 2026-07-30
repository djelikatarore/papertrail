export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_LENGTH = 12;

// Mirrors backend/app/utils/password_validation.py exactly — keep both lists
// in sync so a password rejected by one side is never accepted by the other.
const WEAK_PASSWORDS = new Set([
  "password",
  "12345678",
  "123456789",
  "1234567890",
  "qwerty",
  "qwerty123",
  "admin",
  "azerty",
  "letmein",
  "00000000",
  "11111111",
  "123123123",
  "iloveyou",
  "welcome",
  "monkey",
  "football",
  "abc12345",
  "abcd1234",
  "passw0rd",
]);

// Returns an error message string if the password is rejected, or null if
// it's acceptable. Same rules and wording as the backend check.
export function getPasswordError(password) {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters`;
  }

  if (password.length > MAX_PASSWORD_LENGTH) {
    return `Password must be at most ${MAX_PASSWORD_LENGTH} characters`;
  }

  if (WEAK_PASSWORDS.has(password.toLowerCase())) {
    return "This password is too common, please choose a stronger one";
  }

  return null;
}

// The input also has maxLength={MAX_PASSWORD_LENGTH} set, so typing stops
// dead at the limit — this tells the UI when to explain why, rather than
// leaving the user wondering why the field stopped accepting keystrokes.
export function isAtMaxLength(password) {
  return password.length >= MAX_PASSWORD_LENGTH;
}

// Purely a UI hint — informational only, never a pass/fail gate. A password
// only needs to clear getPasswordError (length + blocklist) to be
// submittable; "Medium" and "Strong" are both fully acceptable, this just
// tells the user how much room there'd be to do better. Scored on character
// variety, with length as a secondary bonus once there's already decent
// variety — tuned for the narrow 8-12 char window, where an 8-char password
// with 3 character classes (e.g. "Test1234") is a perfectly reasonable
// "Medium", not a "Weak".
export function getPasswordStrength(password) {
  if (getPasswordError(password)) {
    return "weak";
  }

  let variety = 0;
  if (/[a-z]/.test(password)) variety += 1;
  if (/[A-Z]/.test(password)) variety += 1;
  if (/[0-9]/.test(password)) variety += 1;
  if (/[^a-zA-Z0-9]/.test(password)) variety += 1;

  if (variety <= 1) {
    return "weak";
  }
  if (variety >= 3 && password.length >= 10) {
    return "strong";
  }

  return "medium";
}
