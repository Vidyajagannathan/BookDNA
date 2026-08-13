import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { LogOut, UserPlus } from "lucide-react";
import { api } from "../lib/api";
const avatars = ["forest", "clay", "gold", "ocean", "plum"];
export function AccountPage() {
  const nav = useNavigate();
  const queryClient = useQueryClient();
  const profile = useQuery({
    queryKey: ["auth", "profile"],
    queryFn: api.profile,
    retry: false,
  });
  const [settings, setSettings] = useState<{
    display_name: string;
    timezone: string;
    date_format: string;
    language: string;
    avatar: string;
  }>();
  const current = settings || {
    display_name: profile.data?.display_name || "",
    timezone:
      profile.data?.timezone ||
      Intl.DateTimeFormat().resolvedOptions().timeZone ||
      "UTC",
    date_format: profile.data?.date_format || "DD/MM/YYYY",
    language: "en",
    avatar: profile.data?.avatar || "forest",
  };
  const update = useMutation({
    mutationFn: () => api.updateProfile(current),
    onSuccess: (data) => {
      queryClient.setQueryData(["auth", "profile"], data);
      setSettings(undefined);
    },
  });
  const [passwords, setPasswords] = useState({
    current: "",
    next: "",
    confirm: "",
  });
  const password = useMutation({
    mutationFn: () => api.changePassword(passwords.current, passwords.next),
    onSuccess: () => setPasswords({ current: "", next: "", confirm: "" }),
  });
  const [deletePassword, setDeletePassword] = useState("");
  const [confirm, setConfirm] = useState(false);
  const deletion = useMutation({
    mutationFn: () => api.deleteAccount(deletePassword),
    onSuccess: () => {
      queryClient.clear();
      nav("/");
    },
  });
  const logout = async () => {
    await api.logout();
    queryClient.clear();
    nav("/");
  };
  const logoutAll = useMutation({
    mutationFn: api.logoutAll,
    onSuccess: () => {
      queryClient.clear();
      nav("/login");
    },
  });
  if (profile.isPending)
    return (
      <section className="page">
        <div className="empty">Loading account…</div>
      </section>
    );
  if (profile.isError)
    return (
      <section className="page">
        <div className="empty">
          <h2>Sign in to manage your account</h2>
          <Link className="button primary" to="/login?next=/account">
            Sign in
          </Link>
        </div>
      </section>
    );
  return (
    <section className="page account-page">
      <span className="eyebrow">Your details and preferences</span>
      <h1>Account settings</h1>
      <div className="account-actions">
        <button className="button" onClick={logout}>
          <LogOut size={17} /> Sign out
        </button>
        <button
          className="button"
          disabled={logoutAll.isPending}
          onClick={() => {
            if (window.confirm("Sign out of BookDNA on every device?"))
              logoutAll.mutate();
          }}
        >
          <LogOut size={17} />
          {logoutAll.isPending ? "Signing out…" : "Sign out of all devices"}
        </button>
        <button
          className="button"
          onClick={async () => {
            if (window.confirm("Sign out and create another account?")) {
              await api.logout();
              queryClient.clear();
              nav("/register");
            }
          }}
        >
          <UserPlus size={17} /> Create another account
        </button>
      </div>
      <div className="settings-card">
        <h2>Profile</h2>
        <p>
          Your email is shown for account reference. Email changes and
          forgotten-password resets will arrive with email verification later.
        </p>
        <label>
          Email
          <input value={profile.data.email} disabled />
        </label>
        <label>
          Display name
          <input
            maxLength={60}
            value={current.display_name}
            onChange={(event) =>
              setSettings({ ...current, display_name: event.target.value })
            }
          />
        </label>
        <label>
          Avatar colour
          <div className="avatar-options">
            {avatars.map((value) => (
              <button
                key={value}
                className={`avatar ${value} ${current.avatar === value ? "selected" : ""}`}
                onClick={() => setSettings({ ...current, avatar: value })}
              >
                {(current.display_name ||
                  profile.data.username)[0].toUpperCase()}
              </button>
            ))}
          </div>
        </label>
        <div className="settings-grid">
          <label>
            Time zone
            <input
              value={current.timezone}
              onChange={(event) =>
                setSettings({ ...current, timezone: event.target.value })
              }
            />
          </label>
          <label>
            Date format
            <select
              value={current.date_format}
              onChange={(event) =>
                setSettings({ ...current, date_format: event.target.value })
              }
            >
              <option>DD/MM/YYYY</option>
              <option>MM/DD/YYYY</option>
              <option>YYYY-MM-DD</option>
            </select>
          </label>
          <label>
            Language
            <select value={current.language} disabled>
              <option value="en">English</option>
            </select>
            <small>
              More languages can be added when translations are ready.
            </small>
          </label>
        </div>
        {update.isSuccess && <p className="success">Profile saved.</p>}
        <button
          className="button primary"
          onClick={() => update.mutate()}
          disabled={update.isPending}
        >
          {update.isPending ? "Saving…" : "Save profile"}
        </button>
      </div>
      <div className="settings-card">
        <h2>Change password</h2>
        <form
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            if (passwords.next === passwords.confirm) password.mutate();
          }}
        >
          <label>
            Current password
            <input
              type="password"
              required
              value={passwords.current}
              onChange={(event) =>
                setPasswords({ ...passwords, current: event.target.value })
              }
            />
          </label>
          <label>
            New password
            <input
              type="password"
              required
              minLength={10}
              value={passwords.next}
              onChange={(event) =>
                setPasswords({ ...passwords, next: event.target.value })
              }
            />
          </label>
          <label>
            Confirm new password
            <input
              type="password"
              required
              minLength={10}
              value={passwords.confirm}
              onChange={(event) =>
                setPasswords({ ...passwords, confirm: event.target.value })
              }
            />
          </label>
          {passwords.confirm && passwords.next !== passwords.confirm && (
            <p className="error">Passwords do not match.</p>
          )}
          {password.error && <p className="error">{password.error.message}</p>}
          {password.isSuccess && (
            <p className="success">Password changed securely.</p>
          )}
          <button className="button primary">Change password</button>
        </form>
      </div>
      <div className="danger-zone">
        <h2>Delete account</h2>
        <p>
          This permanently removes your library, ratings, favourites, private
          DNF notes, and BookDNA.
        </p>
        <form
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            if (confirm) deletion.mutate();
          }}
        >
          <label>
            Confirm your password
            <input
              type="password"
              required
              value={deletePassword}
              onChange={(event) => setDeletePassword(event.target.value)}
            />
          </label>
          <label className="confirm-check">
            <input
              type="checkbox"
              checked={confirm}
              onChange={(event) => setConfirm(event.target.checked)}
            />{" "}
            I understand this cannot be undone.
          </label>
          {deletion.error && <p className="error">{deletion.error.message}</p>}
          <button
            className="button danger"
            disabled={!confirm || deletion.isPending}
          >
            Permanently delete my account
          </button>
        </form>
      </div>
    </section>
  );
}
