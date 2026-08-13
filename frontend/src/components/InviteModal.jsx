import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";
import Modal from "./Modal";
import { getInviteLink, inviteByEmail } from "../services/workspaceService";

export default function InviteModal({ workspaceId, onClose }) {
  const [link, setLink] = useState(null);
  const [linkError, setLinkError] = useState(null);
  const [copied, setCopied] = useState(false);

  const [email, setEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [emailError, setEmailError] = useState(null);
  const [emailSuccess, setEmailSuccess] = useState(null);

  useEffect(() => {
    getInviteLink(workspaceId)
      .then((res) => setLink(res.invite_link))
      .catch(() => setLinkError("Could not load the invite link. Please try again."));
  }, [workspaceId]);

  function copyLink() {
    navigator.clipboard.writeText(link).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handleInvite(event) {
    event.preventDefault();
    if (!email.trim() || inviting) return;
    setInviting(true);
    setEmailError(null);
    setEmailSuccess(null);
    try {
      await inviteByEmail(workspaceId, email.trim());
      setEmailSuccess(`Invitation sent to ${email.trim()} — they'll join once they accept it.`);
      setEmail("");
    } catch (err) {
      const status = err.response?.status;
      if (status === 409) {
        setEmailError("This person is already a member of this workspace.");
      } else if (status === 502) {
        setEmailError("Could not send the invitation email. Please try again.");
      } else {
        setEmailError("Could not send this invite. Please try again.");
      }
    } finally {
      setInviting(false);
    }
  }

  return (
    <Modal onClose={onClose}>
      <h3 className="mb-6 pr-6 text-lg font-bold text-text">Invite to workspace</h3>

      <form onSubmit={handleInvite} className="mb-6">
        <label className="mb-1 block text-sm font-semibold text-text">Invite by email</label>
        <p className="mb-2 text-xs text-muted">
          Sends an invitation email either way — they'll join once they accept it, whether or not they
          already have a PaperTrail account.
        </p>
        <div className="flex gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setEmailError(null);
              setEmailSuccess(null);
            }}
            placeholder="colleague@example.com"
            className="flex-1 rounded-lg border border-border px-3.5 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={!email.trim() || inviting}
            className="btn-primary px-4 py-2"
          >
            {inviting ? "Inviting..." : "Invite"}
          </button>
        </div>
        {emailError && <p className="mt-2 text-xs text-red">{emailError}</p>}
        {emailSuccess && <p className="mt-2 text-xs text-green">{emailSuccess}</p>}
      </form>

      <div>
        <label className="mb-1 block text-sm font-semibold text-text">Or share an invite link</label>
        <p className="mb-2 text-xs text-muted">
          Anyone with a PaperTrail account can join by opening this link.
        </p>
        {linkError ? (
          <p className="text-xs text-red">{linkError}</p>
        ) : (
          <div className="flex gap-2">
            <input
              type="text"
              readOnly
              value={link ?? "Loading..."}
              className="flex-1 rounded-lg border border-border bg-app-bg px-3.5 py-2 text-xs text-muted"
            />
            <button
              type="button"
              onClick={copyLink}
              disabled={!link}
              className="btn-secondary px-3 py-2 text-xs"
            >
              {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? "Copied" : "Copy"}
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}
