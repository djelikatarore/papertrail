import { useState } from "react";
import { MAX_PASSWORD_LENGTH } from "../utils/passwordValidation";

function EyeIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-5 w-5">
      <path
        d="M1.5 10S4.5 4 10 4s8.5 6 8.5 6-3 6-8.5 6-8.5-6-8.5-6Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="10" cy="10" r="2.5" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="h-5 w-5">
      <path
        d="M2.5 2.5l15 15M8.3 4.3C8.85 4.1 9.42 4 10 4c5.5 0 8.5 6 8.5 6a15 15 0 0 1-3.15 4.05M11.6 11.6a2.5 2.5 0 0 1-3.5-3.5M6.1 6.15C3.5 7.7 1.5 10 1.5 10s3 6 8.5 6c1.05 0 2-.15 2.85-.4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function PasswordInput({ value, onChange, className = "" }) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative">
      <input
        type={visible ? "text" : "password"}
        value={value}
        onChange={onChange}
        maxLength={MAX_PASSWORD_LENGTH}
        className={`w-full rounded-lg border border-gray-300 px-3 py-2 pr-10 text-sm ${className}`}
      />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Hide password" : "Show password"}
        className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-400 hover:text-gray-600"
      >
        {visible ? <EyeOffIcon /> : <EyeIcon />}
      </button>
    </div>
  );
}
