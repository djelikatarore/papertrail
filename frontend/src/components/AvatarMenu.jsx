import { ChevronDown, LogOut, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function initials(fullName) {
  if (!fullName) return "?";
  const parts = fullName.trim().split(/\s+/);
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export default function AvatarMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5"
      >
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-accent to-[#A78BFA]">
          <span className="text-[11px] font-bold text-white">{initials(user?.full_name)}</span>
        </div>
        <span className="text-sm font-semibold text-text">{user?.full_name ?? "Account"}</span>
        <ChevronDown size={14} className="text-muted" />
      </button>

      {open && (
        <div className="absolute right-0 top-[calc(100%+6px)] z-50 w-52 rounded-xl border border-border bg-card shadow-card-hover">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm font-semibold text-text">{user?.full_name}</p>
            <p className="mt-0.5 text-xs text-muted">{user?.email}</p>
          </div>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              navigate("/settings");
            }}
            className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm text-text hover:bg-app-bg"
          >
            <User size={14} className="text-muted" /> Your Profile
          </button>
          <div className="border-t border-border">
            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm text-red"
            >
              <LogOut size={14} /> Log out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
