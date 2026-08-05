// Practical format check only — never claims to confirm the address exists
// or is deliverable (that requires an actual verification/confirmation-email
// flow, out of scope here). Mirrors the shape EmailStr accepts backend-side
// closely enough that anything rejected here would also be rejected there.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(email) {
  return EMAIL_PATTERN.test(email.trim());
}
