import { Bell, CheckCircle, Lock, Mail, User } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import ErrorBanner from "../components/ErrorBanner";
import { updateProfile } from "../services/authService";
import { useAuth } from "../context/AuthContext";

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "password", label: "Password", icon: Lock },
  { id: "notifications", label: "Notifications", icon: Bell },
];

function initials(fullName) {
  if (!fullName) return "?";
  return fullName
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

function ProfileTab() {
  const { user, updateUser } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  const trimmedName = fullName.trim();
  const canSave = trimmedName.length > 0 && trimmedName !== user?.full_name && !saving;

  async function handleSave(event) {
    event.preventDefault();
    if (!canSave) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateProfile({ fullName: trimmedName });
      updateUser(updated);
      setFullName(updated.full_name);
      setSaved(true);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Could not update your profile. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="overflow-hidden rounded-[var(--radius-card-lg)] border border-border bg-card shadow-card">
      <div className="flex items-center gap-4 border-b border-border px-6 py-5">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-[#A78BFA]">
          <span className="text-xl font-bold text-white">{initials(user?.full_name)}</span>
        </div>
        <div>
          <p className="text-[15px] font-bold text-text">{user?.full_name}</p>
          <p className="text-sm text-muted">{user?.email}</p>
        </div>
      </div>

      <form onSubmit={handleSave} className="flex flex-col gap-4 p-6">
        {error && <ErrorBanner message={error} />}

        <div>
          <label htmlFor="full_name" className="mb-1 block text-sm font-semibold text-text">
            Full name
          </label>
          <input
            id="full_name"
            type="text"
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value);
              setSaved(false);
            }}
            className="w-full rounded-xl border border-border px-3.5 py-2 text-sm text-text outline-none transition-colors focus:border-accent"
          />
        </div>

        <div>
          <label htmlFor="email" className="mb-1 block text-sm font-semibold text-text">
            Email address
          </label>
          <div className="flex items-center gap-2 rounded-xl border border-border bg-app-bg px-3.5 py-2 text-sm text-muted">
            <Mail size={14} />
            <span id="email">{user?.email}</span>
          </div>
        </div>

        {saved && (
          <div className="flex items-center gap-2 text-sm font-semibold text-green" role="status">
            <CheckCircle size={16} /> Profile saved successfully
          </div>
        )}

        <button type="submit" disabled={!canSave} className="btn-primary self-start px-4 py-2">
          {saving ? "Saving..." : "Save changes"}
        </button>
      </form>
    </div>
  );
}

// No authenticated change-password endpoint exists yet (only the
// email/token-based forgot-password flow) — this is an intentional
// informational state, not a stub awaiting wiring. Documented as a future
// backend enhancement (POST /auth/change-password) rather than built here.
function PasswordTab() {
  return (
    <div className="rounded-[var(--radius-card-lg)] border border-border bg-card p-6 shadow-card">
      <h3 className="mb-2 text-[15px] font-bold text-text">Change password</h3>
      <p className="mb-4 text-sm leading-relaxed text-muted">
        Changing your password while logged in isn't available yet. For now, you can reset your
        password by requesting a reset link by email.
      </p>
      <Link to="/forgot-password" className="btn-secondary inline-flex px-4 py-2">
        Go to Forgot Password
      </Link>
    </div>
  );
}

function NotificationsTab() {
  return (
    <div className="overflow-hidden rounded-[var(--radius-card-lg)] border border-border bg-card shadow-card">
      <div className="border-b border-border px-6 py-4">
        <p className="text-sm font-bold text-text">Email preferences</p>
      </div>
      <div className="flex flex-col items-center gap-2 px-6 py-14 text-center text-muted">
        <Bell size={32} strokeWidth={1} className="mb-1 text-border" />
        <p className="text-sm font-semibold text-text">Coming soon</p>
        <p className="max-w-xs text-[13px]">
          Notification preferences aren't available yet — this section will let you control email
          alerts once it ships.
        </p>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [tab, setTab] = useState("profile");

  return (
    <AppShell title="Settings" subtitle="Manage your account and preferences">
      <div className="max-w-2xl p-10">
        <div className="mb-7 flex w-fit gap-1 rounded-xl bg-app-bg p-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? "page" : undefined}
              className={`flex items-center gap-2 rounded-lg px-4 py-1.5 text-sm transition-colors ${
                tab === t.id ? "bg-card font-semibold text-text shadow-card" : "text-muted"
              }`}
            >
              <t.icon size={14} /> {t.label}
            </button>
          ))}
        </div>

        {tab === "profile" && <ProfileTab />}
        {tab === "password" && <PasswordTab />}
        {tab === "notifications" && <NotificationsTab />}
      </div>
    </AppShell>
  );
}
