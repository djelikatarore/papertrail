import { getPasswordStrength } from "../utils/passwordValidation";

const STRENGTH_CONFIG = {
  weak: { label: "Weak", barClass: "w-1/3 bg-red-500", textClass: "text-red-600" },
  medium: { label: "Medium", barClass: "w-2/3 bg-amber-500", textClass: "text-amber-600" },
  strong: { label: "Strong", barClass: "w-full bg-emerald-500", textClass: "text-emerald-600" },
};

export default function PasswordStrengthIndicator({ password }) {
  if (!password) {
    return null;
  }

  const strength = getPasswordStrength(password);
  const config = STRENGTH_CONFIG[strength];

  return (
    <div className="mt-1.5">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
        <div className={`h-full transition-all ${config.barClass}`} />
      </div>
      <p className={`mt-1 text-xs font-medium ${config.textClass}`}>{config.label}</p>
    </div>
  );
}
